// Thin fetch wrapper over the FastAPI backend. All game mutations return
// graph_delta payloads that graph.js animates incrementally.
const api = {
  async _call(method, path, body, params) {
    const url = new URL(API_BASE + path, location.origin);
    if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
    const headers = {};
    if (body) headers["Content-Type"] = "application/json";
    const code = localStorage.getItem("vegas_access_code");
    if (code) headers["X-Access-Code"] = code;
    const resp = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!resp.ok) {
      const detail = await resp.json().catch(() => ({}));
      throw new Error(detail.detail || `${method} ${path} -> ${resp.status}`);
    }
    return resp.json();
  },
  startSession: () => api._call("POST", "/api/session/start"),
  resetSession: (sid) => api._call("POST", "/api/session/reset", { session_id: sid }),
  gameState: (sid) => api._call("GET", "/api/game/state", null, { session_id: sid }),
  enterLocation: (sid, loc) => api._call("POST", "/api/location/enter", { session_id: sid, location_id: loc }),
  inspect: (sid, loc, hotspot) => api._call("POST", "/api/evidence/inspect", { session_id: sid, location_id: loc, hotspot_id: hotspot }),
  fileEvidence: (sid, loc, hotspot) => api._call("POST", "/api/evidence/file", { session_id: sid, location_id: loc, hotspot_id: hotspot }),
  talk: (sid, character, message) => api._call("POST", "/api/character/talk", { session_id: sid, character_id: character, message }),
  memify: (sid) => api._call("POST", "/api/memory/memify", { session_id: sid }),
  forget: (sid, factId) => api._call("POST", "/api/memory/forget", { session_id: sid, fact_id: factId }),
  recall: (sid, query) => api._call("POST", "/api/memory/recall", { session_id: sid, query }),
  solve: (sid, timedOut = false) => api._call("POST", "/api/game/solve", { session_id: sid, timed_out: timedOut }),
  graph: (sid) => api._call("GET", "/api/graph", null, { session_id: sid }),
  debugLog: () => api._call("GET", "/api/debug/cognee-log"),
};
