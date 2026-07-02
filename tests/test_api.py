"""M3 endpoint tests — Cognee is mocked so these run offline and fast.

The mock mimics the verified live behavior: remember returns data_ids resolved
by fact-id name, the graph grows a couple of nodes per remembered fact, and
forget removes that fact's nodes.
"""
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.services import cognee_client


class FakeCognee:
    """Stands in for Cognee Cloud: one entity node + one dataset edge per fact."""

    def __init__(self):
        self.datasets: dict[str, dict] = {}

    def _ds(self, dataset):
        return self.datasets.setdefault(dataset, {"facts": {}, "extra_nodes": []})

    async def remember(self, facts, dataset):
        ds = self._ds(dataset)
        remembered = []
        for fact in facts:
            ds["facts"][fact["id"]] = fact["text"]
            remembered.append(
                {"fact_id": fact["id"], "text": fact["text"],
                 "data_id": f"data-{fact['id']}", "dataset_id": "ds-1"}
            )
        return {"remembered": remembered, "failed": [], "queued": 0}

    async def recall(self, query, dataset, top_k=15, search_type=None):
        ds = self._ds(dataset)
        return [{"kind": "graph_completion", "text": " ".join(ds["facts"].values()) or "no memories"}]

    async def memify(self, dataset):
        ds = self._ds(dataset)
        ds["extra_nodes"].append(f"inference-{len(ds['extra_nodes']) + 1}")
        return {"status": "ok"}

    async def forget(self, dataset, data_id=None, fact_id=None):
        ds = self._ds(dataset)
        target = fact_id or (data_id or "").replace("data-", "")
        if target not in ds["facts"]:
            raise cognee_client.CogneeError(f"no data item '{target}'")
        del ds["facts"][target]
        return {"status": "success"}

    async def get_graph(self, dataset):
        ds = self._ds(dataset)
        nodes, edges = [], []
        for fid in ds["facts"]:
            nodes.append({"id": f"node-{fid}", "label": f"entity:{fid}"})
            nodes.append({"id": f"node-{fid}-b", "label": f"detail:{fid}"})
            edges.append({"source": f"node-{fid}", "target": f"node-{fid}-b", "label": "relates_to"})
        for extra in ds["extra_nodes"]:
            nodes.append({"id": extra, "label": extra})
        return {"nodes": nodes, "edges": edges}

    async def delete_dataset(self, dataset):
        self.datasets.pop(dataset, None)
        return True


@pytest.fixture()
def client(monkeypatch):
    fake = FakeCognee()
    for target in ("backend.services.game", "backend.routers.game",
                   "backend.routers.memory", "backend.routers.session"):
        monkeypatch.setattr(f"{target}.cognee_client", fake, raising=True)
    with TestClient(app) as test_client:
        test_client.fake = fake
        yield test_client


def start(client):
    state = client.post("/api/session/start").json()["state"]
    return state["session_id"]


def test_session_start_gives_isolated_dataset(client):
    a = client.post("/api/session/start").json()["state"]
    b = client.post("/api/session/start").json()["state"]
    assert a["session_id"] != b["session_id"]
    assert a["dataset"] != b["dataset"]
    assert a["current_location"] == "hotel_suite"
    assert len(a["locations"]) == 6


def test_inspect_evidence_remembers_and_returns_delta(client):
    sid = start(client)
    r = client.post("/api/evidence/inspect", json={
        "session_id": sid, "location_id": "hotel_suite", "hotspot_id": "safe_note"})
    assert r.status_code == 200
    body = r.json()
    assert {f["fact_id"] for f in body["facts"]} == {"f13", "f14"}
    assert len(body["graph_delta"]["added_nodes"]) == 4  # 2 nodes per fact
    assert body["hud"]["memories"] == 2

    # re-inspecting is free — no new facts, no delta
    r2 = client.post("/api/evidence/inspect", json={
        "session_id": sid, "location_id": "hotel_suite", "hotspot_id": "safe_note"})
    assert r2.json()["facts"] == []
    assert r2.json()["graph_delta"] is None


def test_talk_reveals_facts_and_lou_lies_until_confronted(client):
    sid = start(client)
    # Lou lies (f08) while the receipt (f07) is unknown
    r = client.post("/api/character/talk", json={
        "session_id": sid, "character_id": "lucky_lou", "message": "Was Dev here?"})
    assert r.json()["facts"][0]["fact_id"] == "f08"

    # find the receipt, then Lou confesses f07 on the next exchange
    client.post("/api/evidence/inspect", json={
        "session_id": sid, "location_id": "pawn_shop", "hotspot_id": "pawn_receipt"})
    r2 = client.post("/api/character/talk", json={
        "session_id": sid, "character_id": "lucky_lou", "message": "Explain this receipt."})
    assert r2.json()["facts"] == []  # f07 already discovered via the receipt
    r3 = client.get("/api/game/state", params={"session_id": sid})
    assert r3.status_code == 200


def test_forget_removes_nodes_and_solve_tracks_it(client):
    sid = start(client)
    client.post("/api/evidence/inspect", json={
        "session_id": sid, "location_id": "hotel_suite", "hotspot_id": "lipstick_napkin"})
    r = client.post("/api/memory/forget", json={"session_id": sid, "fact_id": "rh1"})
    assert r.status_code == 200
    assert r.json()["graph_delta"]["removed_node_ids"]
    assert r.json()["hud"]["forgotten"] == 1

    # forgetting twice is a 409
    r2 = client.post("/api/memory/forget", json={"session_id": sid, "fact_id": "rh1"})
    assert r2.status_code == 409


def test_memify_tags_new_nodes_as_inferences(client):
    sid = start(client)
    client.post("/api/evidence/inspect", json={
        "session_id": sid, "location_id": "casino_floor", "hotspot_id": "casino_chip_receipt"})
    client.get("/api/graph", params={"session_id": sid})  # sync snapshot
    r = client.post("/api/memory/memify", json={"session_id": sid})
    added = r.json()["graph_delta"]["added_nodes"]
    assert added and all(n["data"]["type"] == "inference" for n in added)
    assert r.json()["hud"]["inferences"] == len(added)


def test_recall_returns_answer_and_citations(client):
    sid = start(client)
    client.post("/api/evidence/inspect", json={
        "session_id": sid, "location_id": "casino_floor", "hotspot_id": "casino_chip_receipt"})
    r = client.post("/api/memory/recall", json={"session_id": sid, "query": "what happened?"})
    assert r.status_code == 200
    assert "answer" in r.json()


def test_solve_flow_win_and_contamination(client):
    sid = start(client)
    key_hotspots = [
        ("hotel_suite", "safe_note"), ("hotel_suite", "ice_bucket_cash"),
        ("hotel_suite", "dead_phone"), ("casino_floor", "casino_chip_receipt"),
        ("pawn_shop", "pawn_receipt"), ("chapel", "chapel_polaroid"),
    ]
    for loc, hotspot in key_hotspots:
        client.post("/api/evidence/inspect", json={
            "session_id": sid, "location_id": loc, "hotspot_id": hotspot})
    for char, n in [("rosa", 5), ("rev_sonny", 3), ("chad", 3), ("lucky_lou", 2)]:
        for _ in range(n):
            client.post("/api/character/talk", json={
                "session_id": sid, "character_id": char, "message": "tell me more"})

    r = client.post("/api/game/solve", json={"session_id": sid})
    result = r.json()["result"]
    # dead_phone brought in rh3 — one active herring is forgiven
    assert result["active_red_herrings"] == ["rh3"]
    assert result["won"] is True
    assert r.json()["hal_answer"]

    # forgetting the herring keeps the win and cleans the graph
    client.post("/api/memory/forget", json={"session_id": sid, "fact_id": "rh3"})
    r2 = client.post("/api/game/solve", json={"session_id": sid})
    assert r2.json()["result"]["won"] is True
    assert r2.json()["result"]["active_red_herrings"] == []


def test_reset_creates_fresh_session_and_drops_dataset(client):
    sid = start(client)
    client.post("/api/evidence/inspect", json={
        "session_id": sid, "location_id": "hotel_suite", "hotspot_id": "safe_note"})
    r = client.post("/api/session/reset", json={"session_id": sid})
    new_state = r.json()["state"]
    assert new_state["session_id"] != sid
    assert new_state["discovered_facts"] == []
    # old session is gone
    r2 = client.get("/api/game/state", params={"session_id": sid})
    assert r2.status_code == 404


def test_world_story_integrity():
    """Every hotspot fact exists in ground truth; every character fact too;
    all evidence-sourced facts are reachable from some hotspot."""
    from backend.models.facts import load_ground_truth
    from backend.models.world import load_world

    truth, world = load_ground_truth(), load_world()
    all_ids = {f.id for f in truth.facts} | {f.id for f in truth.red_herrings}

    hotspot_facts: set[str] = set()
    for loc in world.locations:
        assert 3 <= len(loc.hotspots) <= 5
        for h in loc.hotspots:
            assert set(h.facts) <= all_ids, f"{h.id} references unknown facts"
            hotspot_facts |= set(h.facts)

    char_facts: set[str] = set()
    for c in world.characters:
        assert world.location(c.location) is not None
        assert set(c.knows_facts + c.confesses_facts) <= all_ids
        char_facts |= set(c.knows_facts + c.confesses_facts)

    # every ground-truth fact must be discoverable somewhere
    missing = all_ids - hotspot_facts - char_facts
    assert not missing, f"undiscoverable facts: {missing}"
    # every red herring is plantable AND debunkable — by a character, or by
    # contradicting evidence (rh4 falls to the pawn receipt's timeline)
    for rh in truth.red_herrings:
        assert rh.id in hotspot_facts
        char_debunk = any(rh.id in c.debunks for c in world.characters)
        assert char_debunk or rh.debunked_by, f"{rh.id} is un-debunkable"
