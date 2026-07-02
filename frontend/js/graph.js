// The memory graph panel — now a live 3D force graph (three.js via
// 3d-force-graph). Auto-rotating camera; lifecycle animations: pop-in on
// remember, purple glow + particle edges on memify inferences, amber pulse on
// recall citations, fade-out on forget (right-click a node).
const Graph = (() => {
  const COLORS = {
    memory: "#22e6ff",
    inference: "#b26bff",
    facttag: "#ffb545",
    plumbing: "#4a4168",
    cited: "#ffb545",
    dying: "#ff4757",
  };

  let graph = null;
  let orbitTimer = null;
  let focusHold = false; // citation camera focus temporarily owns the view
  const nodes = [];            // persistent objects: {id,label,kind,fresh,cited,dying}
  const links = [];            // {id,source,target,label,inference}
  const nodeById = new Map();
  const factNodes = new Map(); // fact_id -> fact record (for forget mapping)

  const kindOf = (label, type) => {
    if (type === "inference") return "inference";
    if (/^(DocumentChunk|TextSummary|TextDocument|EntityType)/.test(label)) return "plumbing";
    if (/^(f|rh)\d+$/.test(label)) return "facttag";
    return "memory";
  };

  const nodeColor = (n) =>
    n.dying ? COLORS.dying : n.cited ? COLORS.cited : COLORS[n.kind] || COLORS.memory;
  const nodeSize = (n) =>
    (n.kind === "plumbing" ? 2.5 : n.kind === "inference" ? 9 : 5.5) * (n.fresh ? 2 : 1) * (n.cited ? 2 : 1);

  function makeNodeObject(n) {
    const group = new THREE.Group();
    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(1, 16, 16),
      new THREE.MeshLambertMaterial({
        color: nodeColor(n),
        transparent: true,
        opacity: n.dying ? 0.15 : n.kind === "plumbing" ? 0.45 : 0.95,
        emissive: nodeColor(n),
        emissiveIntensity: n.cited || n.fresh ? 0.9 : 0.45,
      })
    );
    const s = nodeSize(n);
    sphere.scale.set(s, s, s);
    group.add(sphere);
    if (n.kind !== "plumbing") {
      const sprite = new SpriteText(n.label.length > 22 ? n.label.slice(0, 21) + "…" : n.label);
      sprite.color = nodeColor(n);
      sprite.textHeight = n.kind === "facttag" ? 3.8 : 4.6;
      sprite.fontFace = "JetBrains Mono, monospace";
      sprite.position.y = -(s + 4);
      sprite.material.depthWrite = false;
      group.add(sprite);
    }
    return group;
  }

  const refresh = () => graph && graph.nodeThreeObject(graph.nodeThreeObject());

  async function init() {
    // the 3D libs load as ES modules — wait for them
    await new Promise((resolve) => {
      const timer = setInterval(() => {
        if (window.__graphLibsReady) { clearInterval(timer); resolve(); }
      }, 40);
    });
    const el = document.getElementById("graph");
    graph = ForceGraph3D({ controlType: "orbit" })(el)
      .backgroundColor("#0f0c1a")
      .showNavInfo(false)
      .nodeId("id")
      .nodeLabel((n) => n.label)
      .nodeThreeObject(makeNodeObject)
      .linkColor((l) => (l.inference ? COLORS.inference : "#3a3157"))
      .linkOpacity(0.5)
      .linkWidth((l) => (l.inference ? 1.2 : 0.5))
      .linkDirectionalParticles((l) => (l.inference ? 3 : 0))
      .linkDirectionalParticleSpeed(0.008)
      .linkDirectionalParticleWidth(1.6)
      .onNodeRightClick((node, event) => Forget.openMenu(node.label, event.clientX, event.clientY))
      .graphData({ nodes, links });

    graph.d3Force("charge").strength(-240);

    // Manual auto-orbit: OrbitControls' autoRotate fights cameraPosition
    // tweens, so we drive the camera ourselves — distance follows the graph's
    // live bounding box, so the constellation always stays framed.
    let angle = 0;
    let orbitPaused = false;
    orbitTimer = setInterval(() => {
      if (orbitPaused || focusHold || !nodes.length) return;
      const bb = graph.getGraphBbox();
      if (!bb) return;
      const span = Math.max(
        bb.x[1] - bb.x[0], bb.y[1] - bb.y[0], bb.z[1] - bb.z[0], 100);
      const dist = span * 0.95 + 40;
      const center = {
        x: (bb.x[0] + bb.x[1]) / 2,
        y: (bb.y[0] + bb.y[1]) / 2,
        z: (bb.z[0] + bb.z[1]) / 2,
      };
      angle += 0.0035;
      graph.cameraPosition({
        x: center.x + dist * Math.sin(angle),
        y: center.y + span * 0.2,
        z: center.z + dist * Math.cos(angle),
      }, center);
    }, 40);
    // hand the camera to the player while they're interacting
    el.addEventListener("pointerdown", () => (orbitPaused = true));
    el.addEventListener("pointerup", () => setTimeout(() => (orbitPaused = false), 5000));

    new ResizeObserver(() => {
      graph.width(el.clientWidth).height(el.clientHeight);
    }).observe(el);
    return graph;
  }

  function addNode(data, { inference = false } = {}) {
    if (nodeById.has(data.id)) return null;
    const node = {
      id: data.id,
      label: data.label || String(data.id).slice(0, 8),
      kind: kindOf(data.label || "", inference ? "inference" : data.type),
      fresh: true,
    };
    nodes.push(node);
    nodeById.set(node.id, node);
    return node;
  }

  // Apply an incremental graph_delta from any backend response.
  function applyDelta(delta, { inference = false } = {}) {
    if (!delta) return { nodes: 0, edges: 0 };
    let addedN = 0, addedE = 0;

    for (const n of delta.added_nodes || []) {
      if (addNode(n.data, { inference })) addedN++;
    }
    for (const e of delta.added_edges || []) {
      if (links.some((l) => l.id === e.data.id)) continue;
      if (!nodeById.has(e.data.source) || !nodeById.has(e.data.target)) continue;
      links.push({ id: e.data.id, source: e.data.source, target: e.data.target,
                   label: e.data.label, inference });
      addedE++;
    }

    const removedNodes = new Set(delta.removed_node_ids || []);
    const removedEdges = new Set(delta.removed_edge_ids || []);
    if (removedNodes.size || removedEdges.size) {
      nodes.forEach((n) => { if (removedNodes.has(n.id)) n.dying = true; });
      refresh();
      setTimeout(() => {
        for (let i = nodes.length - 1; i >= 0; i--) {
          if (removedNodes.has(nodes[i].id)) { nodeById.delete(nodes[i].id); nodes.splice(i, 1); }
        }
        for (let i = links.length - 1; i >= 0; i--) {
          const l = links[i];
          const sid = l.source.id ?? l.source, tid = l.target.id ?? l.target;
          if (removedEdges.has(l.id) || removedNodes.has(sid) || removedNodes.has(tid)) links.splice(i, 1);
        }
        graph.graphData({ nodes, links });
      }, 700);
    }

    if (addedN || addedE) graph.graphData({ nodes, links });
    setTimeout(() => { nodes.forEach((n) => (n.fresh = false)); refresh(); }, 1600);
    return { nodes: addedN, edges: addedE };
  }

  function fullSync(g) {
    nodes.length = 0; links.length = 0; nodeById.clear();
    for (const n of g.nodes) addNode({ ...n.data });
    for (const e of g.edges) {
      if (nodeById.has(e.data.source) && nodeById.has(e.data.target))
        links.push({ id: e.data.id, source: e.data.source, target: e.data.target, label: e.data.label });
    }
    nodes.forEach((n) => (n.fresh = false));
    graph.graphData({ nodes, links });
  }

  // Pulse-highlight recall citations and swing the camera to them.
  function citeNodes(ids) {
    const idSet = new Set(ids);
    let focus = null;
    nodes.forEach((n) => { n.cited = idSet.has(n.id); if (n.cited && !focus) focus = n; });
    refresh();
    if (focus && focus.x !== undefined) {
      focusHold = true;
      const dist = 160;
      const r = Math.hypot(focus.x, focus.y, focus.z) || 1;
      graph.cameraPosition(
        { x: focus.x * (1 + dist / r), y: focus.y * (1 + dist / r), z: focus.z * (1 + dist / r) },
        focus, 1200);
    }
    setTimeout(() => {
      nodes.forEach((n) => (n.cited = false));
      refresh();
      focusHold = false;
    }, 4500);
  }

  function registerFacts(facts) {
    for (const f of facts) factNodes.set(f.fact_id, f);
  }

  function factForLabel(label) {
    const lower = (label || "").toLowerCase();
    let best = null, bestScore = 0;
    for (const [fid, fact] of factNodes) {
      if (fact.forgotten) continue;
      if (lower === fid) return fid; // amber fact-tag nodes match directly
      const words = fact.text.toLowerCase().split(/\W+/).filter((w) => w.length > 3);
      const score = words.filter((w) => lower.includes(w)).length;
      if (score > bestScore) { best = fid; bestScore = score; }
    }
    return best;
  }

  function markForgotten(fid) {
    const fact = factNodes.get(fid);
    if (fact) fact.forgotten = true;
  }

  const allNodes = () => nodes.map((n) => ({ id: n.id, label: n.label }));

  return { init, applyDelta, fullSync, citeNodes, registerFacts, factForLabel,
           markForgotten, allNodes, instance: () => graph };
})();
