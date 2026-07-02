// Orchestrator: boot sequence, session, tabs, clock, memify/solve, forget
// menu, Ask-HAL recall, debug overlay.
const Main = (() => {
  let state = null;
  let world = { locations: [] };
  let characters = {};
  let clockTimer = null;

  const $ = (id) => document.getElementById(id);

  // ---------- boot ----------
  const BOOT_LINES = [
    "HAL-9001 BIOS v6.66 … OK",
    "mounting /memory/graph … FAILED",
    "fsck: memory integrity 3% — 97% of last night unrecoverable",
    "owner: DEV — status: UNRESPONSIVE (snoring)",
    "incoming event: PRIYA arrives 12:00",
    "objective: reconstruct last night. find the ring.",
    "rebooting in detective mode…",
  ];

  async function boot() {
    const log = $("boot-log");
    for (const line of BOOT_LINES) {
      log.textContent += "> " + line + "\n";
      await new Promise(r => setTimeout(r, 520));
    }
    await new Promise(r => setTimeout(r, 900));
    $("boot-screen").style.display = "none";
    $("topbar").classList.remove("hidden");
    $("game").classList.remove("hidden");
    startClock();
  }

  // ---------- clock (soft drama timer) ----------
  function startClock() {
    let minutes = 6 * 60;
    clockTimer = setInterval(() => {
      minutes += GAME_MINUTES_PER_REAL_SECOND;
      const capped = Math.min(minutes, 12 * 60);
      const h = Math.floor(capped / 60), m = Math.floor(capped % 60);
      const el = $("clock");
      el.textContent = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")} ${h < 12 ? "AM" : "PM"}`;
      if (capped >= 11 * 60) el.classList.add("late");
    }, 1000);
  }

  // ---------- toasts ----------
  function toast(text, kind = "") {
    const el = document.createElement("div");
    el.className = `toast ${kind}`;
    el.textContent = text;
    $("toast-stack").appendChild(el);
    setTimeout(() => el.remove(), 3500);
  }

  function updateHud(hud) {
    if (!hud) return;
    $("hud-memories").textContent = hud.memories;
    $("hud-inferences").textContent = hud.inferences;
    $("hud-forgotten").textContent = hud.forgotten;
    $("hud-memify").textContent = hud.memify_runs;
  }

  // ---------- locations ----------
  function renderTabs() {
    const nav = $("location-tabs");
    nav.innerHTML = "";
    for (const loc of world.locations) {
      const b = document.createElement("button");
      b.className = "loc-tab" + (state.current_location === loc.id ? " active" : "");
      b.innerHTML = loc.name.toUpperCase() + (loc.character ? ' <span class="chardot">●</span>' : "");
      b.onclick = () => enterLocation(loc.id);
      nav.appendChild(b);
    }
  }

  async function enterLocation(locationId) {
    const resp = await api.enterLocation(state.session_id, locationId);
    state.current_location = locationId;
    renderTabs();
    const character = resp.location.character ? characters[resp.location.character] : null;
    Scene.render(resp.location, character);
  }

  async function inspectHotspot(locationId, hotspotId, el) {
    el.classList.add("inspected");
    try {
      const resp = await api.inspect(state.session_id, locationId, hotspotId);
      Scene.showEvidenceModal(resp.hotspot, resp.facts);
      if (resp.facts.length) {
        Graph.registerFacts(resp.facts);
        const delta = Graph.applyDelta(resp.graph_delta);
        toast(`+${resp.facts.length} memories · graph +${delta.nodes} nodes`);
      }
      updateHud(resp.hud);
    } catch (err) { toast(err.message, "error"); }
  }

  // ---------- memify / solve ----------
  $("btn-memify").onclick = async () => {
    const btn = $("btn-memify");
    btn.disabled = true; btn.textContent = "🧠 CONSOLIDATING…";
    try {
      const resp = await api.memify(state.session_id);
      const delta = Graph.applyDelta(resp.graph_delta, { inference: true });
      updateHud(resp.hud);
      if (resp.inferences?.length) {
        Graph.registerFacts(resp.inferences);
        resp.inferences.forEach((inf, i) =>
          setTimeout(() => toast(`💡 INFERRED: ${inf.text}`, "purple"), i * 900));
      } else {
        toast(delta.nodes || delta.edges
          ? `💡 memify: +${delta.nodes} inferred nodes, +${delta.edges} edges`
          : "memify ran — no new inferences yet. Discover more first.", "purple");
      }
    } catch (err) { toast(err.message, "error"); }
    btn.disabled = false; btn.textContent = "🧠 CONSOLIDATE";
  };

  $("btn-solve").onclick = async () => {
    const btn = $("btn-solve");
    btn.disabled = true; btn.textContent = "🎯 EVALUATING…";
    try {
      const resp = await api.solve(state.session_id);
      showEnding(resp);
    } catch (err) { toast(err.message, "error"); }
    btn.disabled = false; btn.textContent = "🎯 SOLVE THE NIGHT";
  };

  function showEnding(resp) {
    const r = resp.result;
    const title = $("ending-verdict-title");
    title.textContent = r.won ? "NIGHT RECONSTRUCTED" : "MEMORY INCOMPLETE";
    title.className = r.won ? "win" : "lose";
    $("ending-verdict").textContent = r.verdict;
    const ol = $("ending-timeline");
    ol.innerHTML = "";
    for (const entry of r.timeline) {
      const li = document.createElement("li");
      li.innerHTML = `<span class="t">${entry.time}</span> — ${entry.text}`;
      li.onclick = () => { $("ending-screen").classList.add("hidden"); citeFactEntities(entry.text); };
      ol.appendChild(li);
    }
    const hal = Array.isArray(resp.hal_answer)
      ? (resp.hal_answer[0]?.text || JSON.stringify(resp.hal_answer[0]))
      : JSON.stringify(resp.hal_answer);
    $("ending-hal").textContent = hal;
    $("ending-stats").textContent =
      `coverage ${(r.coverage * 100).toFixed(0)}% · key facts ${r.key_facts_found.length}/${r.key_facts_found.length + r.key_facts_missing.length}` +
      ` · active red herrings ${r.active_red_herrings.length}`;
    $("ending-screen").classList.remove("hidden");
  }

  function citeFactEntities(text) {
    const words = text.toLowerCase().split(/\W+/).filter(w => w.length > 4);
    const ids = Graph.allNodes()
      .filter(n => words.some(w => n.label.toLowerCase().includes(w)))
      .map(n => n.id);
    Graph.citeNodes(ids);
  }

  $("ending-close").onclick = () => $("ending-screen").classList.add("hidden");

  // ---------- recall (Ask HAL) ----------
  $("recall-form").onsubmit = async (e) => {
    e.preventDefault();
    const input = $("recall-input");
    const query = input.value.trim();
    if (!query) return;
    input.value = "";
    const box = $("recall-answer");
    box.classList.remove("hidden");
    box.textContent = "HAL is remembering…";
    try {
      const resp = await api.recall(state.session_id, query);
      const first = Array.isArray(resp.answer) ? resp.answer[0] : resp.answer;
      const raw = (first && (first.text || first.search_result)) || JSON.stringify(first);
      const [answer, evidence] = String(raw).split(/\n+Evidence:/);
      box.innerHTML = "";
      box.append(Object.assign(document.createElement("div"), { textContent: answer.trim() }));
      if (evidence) {
        const det = document.createElement("details");
        det.innerHTML = `<summary style="cursor:pointer;color:var(--dim)">evidence (${(evidence.match(/data_id/g) || []).length} sources)</summary>`;
        det.append(Object.assign(document.createElement("pre"),
          { textContent: evidence.trim(), style: "white-space:pre-wrap;color:var(--dim);font-size:10px;margin-top:6px" }));
        box.append(det);
      }
      Graph.citeNodes(resp.cited_node_ids || []);
      updateHud(resp.hud);
    } catch (err) { box.textContent = `recall failed: ${err.message}`; }
  };

  // ---------- debug overlay ----------
  document.addEventListener("keydown", async (e) => {
    if (e.key !== "`") return;
    const overlay = $("debug-overlay");
    if (!overlay.classList.contains("hidden")) return overlay.classList.add("hidden");
    overlay.classList.remove("hidden");
    const tbody = document.querySelector("#debug-table tbody");
    tbody.innerHTML = "<tr><td colspan=5>loading…</td></tr>";
    try {
      const log = await api.debugLog();
      tbody.innerHTML = "";
      for (const call of log.calls.slice().reverse()) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${call.op}</td><td>${call.dataset || ""}</td><td>${Math.round(call.ms)}</td>` +
          `<td class="${call.ok ? "ok" : "err"}">${call.ok ? "OK" : "ERR"}</td><td>${call.detail || ""}</td>`;
        tbody.appendChild(tr);
      }
    } catch (err) { tbody.innerHTML = `<tr><td colspan=5>${err.message}</td></tr>`; }
  });

  // ---------- init ----------
  async function startWithAccessGate() {
    try {
      return await api.startSession();
    } catch (err) {
      const msg = String(err.message);
      const limited = msg.includes("access code") || msg.includes("budget") || msg.includes("detective");
      if (!limited) throw err;
      const code = prompt(msg + "\n\nHave an access code? Enter it (or Cancel):");
      if (!code) throw err;
      localStorage.setItem("vegas_access_code", code.trim());
      return api.startSession(); // one retry; a wrong code throws to the boot log
    }
  }

  async function init() {
    await Graph.init();
    await Scene.loadManifest();
    const bootPromise = boot();
    const started = await startWithAccessGate();
    state = started.state;
    world.locations = state.locations;
    // character metadata comes with each location payload; cache names for docks
    characters = {
      rosa: { name: "Rosa" }, lucky_lou: { name: "Lucky Lou" },
      rev_sonny: { name: "Rev. Sonny" }, chad: { name: "Chad" },
    };
    updateHud(state.hud);
    await bootPromise;
    renderTabs();
    await enterLocation(state.current_location);
  }

  init().catch(err => {
    document.getElementById("boot-log").textContent += `\n> FATAL: backend unreachable — ${err.message}\n> is the API running?`;
  });

  return { inspectHotspot, toast, updateHud, sessionId: () => state?.session_id };
})();

// Right-click → forget menu (registered on graph nodes by graph.js).
const Forget = (() => {
  let pendingFactId = null;

  function openMenu(nodeLabel, x, y) {
    const factId = Graph.factForLabel(nodeLabel);
    if (!factId) return;
    pendingFactId = factId;
    const menu = document.getElementById("forget-menu");
    menu.style.left = x + "px";
    menu.style.top = y + "px";
    menu.classList.remove("hidden");
  }

  document.addEventListener("click", () => document.getElementById("forget-menu").classList.add("hidden"));

  document.getElementById("forget-btn").onclick = async (e) => {
    e.stopPropagation();
    document.getElementById("forget-menu").classList.add("hidden");
    if (!pendingFactId) return;
    try {
      const resp = await api.forget(Main.sessionId(), pendingFactId);
      Graph.markForgotten(pendingFactId);
      Graph.applyDelta(resp.graph_delta);
      Main.updateHud(resp.hud);
      Main.toast(`🗑 forgot ${pendingFactId} — ${resp.graph_delta.removed_node_ids.length} nodes pruned`, "error");
    } catch (err) { Main.toast(err.message, "error"); }
    pendingFactId = null;
  };

  return { openMenu };
})();
