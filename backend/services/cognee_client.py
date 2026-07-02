"""The single wrapper around the Cognee Cloud REST API.

Every memory-lifecycle call in the game goes through this module:

    remember(facts, dataset)  -> POST /api/v1/remember   (ingest + auto-cognify)
    recall(query, dataset)    -> POST /api/v1/recall     (auto-routed retrieval)
    memify(dataset)           -> POST /api/v1/memify     (consolidation / enrichment)
    forget(data_id, dataset)  -> unified deletion API    (prune a memory)
    get_graph(dataset)        -> GET  /api/v1/datasets/{id}/graph (nodes + edges)

Auth is an `X-Api-Key` header (Cognee Cloud). Every call is timed and appended
to CALL_LOG so the frontend debug overlay can show judges the raw lifecycle
traffic. `remember` failures are queued and retried so the game loop never
hard-crashes on a transient Cognee error.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

import httpx

from backend import config

logger = logging.getLogger("cognee")

# Rolling log of every lifecycle call — surfaced by the debug overlay (backtick).
CALL_LOG: list[dict[str, Any]] = []
_CALL_LOG_MAX = 500

# remember() payloads that failed on a transient error, retried by retry_pending().
_PENDING_REMEMBERS: list[tuple[str, str]] = []  # (fact_text, dataset)


class CogneeError(RuntimeError):
    """Raised when Cognee Cloud returns a non-retryable error."""


def _log_call(op: str, dataset: str, ms: float, ok: bool, detail: str = "") -> None:
    CALL_LOG.append(
        {
            "op": op,
            "dataset": dataset,
            "ms": round(ms, 1),
            "ok": ok,
            "detail": detail[:300],
            "t": time.time(),
        }
    )
    del CALL_LOG[:-_CALL_LOG_MAX]
    logger.info("cognee.%s dataset=%s ok=%s %.0fms %s", op, dataset, ok, ms, detail[:120])


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=config.COGNEE_BASE_URL,
        headers={"X-Api-Key": config.COGNEE_API_KEY},
        timeout=httpx.Timeout(120.0, connect=15.0),
    )


async def _request(
    op: str,
    method: str,
    path: str,
    dataset: str = "",
    *,
    json: Optional[dict] = None,
    data: Optional[dict] = None,
    files: Optional[dict] = None,
    retries: int = 2,
) -> Any:
    """Do one HTTP call with timing, logging, and retry on 5xx/network errors."""
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        start = time.perf_counter()
        try:
            async with _client() as client:
                resp = await client.request(method, path, json=json, data=data, files=files)
            ms = (time.perf_counter() - start) * 1000
            if resp.status_code < 300:
                _log_call(op, dataset, ms, True)
                if not resp.content:
                    return {}
                try:
                    return resp.json()
                except ValueError:
                    return {"raw": resp.text}
            # 4xx is a real bug or bad payload — don't retry, surface it.
            if resp.status_code < 500:
                _log_call(op, dataset, ms, False, f"{resp.status_code}: {resp.text[:200]}")
                raise CogneeError(f"{op} failed ({resp.status_code}): {resp.text[:500]}")
            _log_call(op, dataset, ms, False, f"{resp.status_code}, attempt {attempt + 1}")
            last_exc = CogneeError(f"{op} failed ({resp.status_code}): {resp.text[:500]}")
        except httpx.HTTPError as exc:
            ms = (time.perf_counter() - start) * 1000
            _log_call(op, dataset, ms, False, f"{type(exc).__name__}, attempt {attempt + 1}")
            last_exc = exc
        if attempt < retries:
            await asyncio.sleep(1.5 * (attempt + 1))
    raise CogneeError(f"{op} failed after {retries + 1} attempts: {last_exc}")


# ---------------------------------------------------------------------------
# Datasets — each game session gets its own dataset so demo runs stay isolated.
# ---------------------------------------------------------------------------

async def list_datasets() -> list[dict]:
    result = await _request("datasets.list", "GET", "/api/v1/datasets")
    return result if isinstance(result, list) else result.get("datasets", [])


async def dataset_id_for_name(dataset: str) -> Optional[str]:
    for ds in await list_datasets():
        if ds.get("name") == dataset:
            return str(ds.get("id"))
    return None


async def delete_dataset(dataset: str) -> bool:
    """Drop an entire session dataset (used by /api/session/reset)."""
    ds_id = await dataset_id_for_name(dataset)
    if ds_id is None:
        return False
    await _request("datasets.delete", "DELETE", f"/api/v1/datasets/{ds_id}", dataset)
    return True


async def list_data_items(dataset: str) -> list[dict]:
    """Raw data items in a dataset — used to map fact text -> Cognee data_id."""
    ds_id = await dataset_id_for_name(dataset)
    if ds_id is None:
        return []
    result = await _request("datasets.data", "GET", f"/api/v1/datasets/{ds_id}/data", dataset)
    return result if isinstance(result, list) else result.get("data", [])


# ---------------------------------------------------------------------------
# Lifecycle: remember -> recall -> memify -> forget
# ---------------------------------------------------------------------------

async def remember(facts: list[str], dataset: str) -> dict:
    """Ingest facts into the session dataset. One remember call per fact, so
    every fact becomes its own data item and can be individually forgotten.

    /api/v1/remember is multipart and auto-cognifies — no separate cognify call.
    """
    results, failed = [], []
    for fact in facts:
        try:
            result = await _request(
                "remember",
                "POST",
                "/api/v1/remember",
                dataset,
                data={"datasetName": dataset},
                files={"data": ("fact.txt", fact.encode("utf-8"), "text/plain")},
            )
            results.append({"fact": fact, "result": result})
        except (CogneeError, httpx.HTTPError) as exc:
            _PENDING_REMEMBERS.append((fact, dataset))
            failed.append({"fact": fact, "error": str(exc)})
    return {"remembered": results, "failed": failed, "queued": len(_PENDING_REMEMBERS)}


async def retry_pending() -> int:
    """Retry remember() calls that previously failed. Returns how many flushed."""
    pending, _PENDING_REMEMBERS[:] = _PENDING_REMEMBERS[:], []
    flushed = 0
    for fact, dataset in pending:
        result = await remember([fact], dataset)
        flushed += len(result["remembered"])
    return flushed


async def recall(
    query: str,
    dataset: str,
    *,
    search_type: Optional[str] = None,
    top_k: int = 10,
) -> dict:
    """Query the memory graph. Uses /recall (auto-routed) by default; passes
    through to /search when an explicit search_type is requested.
    """
    if search_type:
        return await _request(
            "search",
            "POST",
            "/api/v1/search",
            dataset,
            json={
                "query": query,
                "searchType": search_type,
                "datasets": [dataset],
                "topK": top_k,
            },
        )
    return await _request(
        "recall",
        "POST",
        "/api/v1/recall",
        dataset,
        json={"query": query, "datasets": [dataset], "topK": top_k},
    )


async def memify(dataset: str) -> dict:
    """Run Cognee's consolidation/enrichment pass — derives new inferred
    nodes/edges from what's already remembered. The game diffs the graph
    before/after to animate the inferences.
    """
    return await _request(
        "memify",
        "POST",
        "/api/v1/memify",
        dataset,
        json={"datasetName": dataset, "runInBackground": False},
    )


async def forget(dataset: str, *, data_id: Optional[str] = None, fact_text: Optional[str] = None) -> dict:
    """Prune a memory. Targets a specific data item when data_id (or a fact_text
    to resolve into one) is given; otherwise wipes the dataset's graph+vector
    memory. Maps to Cognee v1.0's unified deletion API.
    """
    ds_id = await dataset_id_for_name(dataset)
    if ds_id is None:
        raise CogneeError(f"forget: dataset '{dataset}' not found")

    if data_id is None and fact_text is not None:
        for item in await list_data_items(dataset):
            name = str(item.get("name", "")) + str(item.get("raw_data_location", ""))
            if fact_text[:60].lower() in (str(item.get("text", "")) + name).lower():
                data_id = str(item.get("id"))
                break
        if data_id is None:
            raise CogneeError(f"forget: no data item matching '{fact_text[:60]}'")

    if data_id is not None:
        return await _request(
            "forget", "DELETE", f"/api/v1/datasets/{ds_id}/data/{data_id}", dataset
        )
    return await _request("forget", "DELETE", f"/api/v1/datasets/{ds_id}", dataset)


# ---------------------------------------------------------------------------
# Graph snapshot for the frontend panel
# ---------------------------------------------------------------------------

async def get_graph(dataset: str) -> dict:
    """Full graph for a dataset as {nodes: [...], edges: [...]} — the frontend
    converts this to Cytoscape elements and computes deltas for animation.
    """
    ds_id = await dataset_id_for_name(dataset)
    if ds_id is None:
        return {"nodes": [], "edges": []}
    result = await _request("graph", "GET", f"/api/v1/datasets/{ds_id}/graph", dataset)
    return {
        "nodes": result.get("nodes", []),
        "edges": result.get("edges", []),
    }
