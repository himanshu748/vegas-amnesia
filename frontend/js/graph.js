// The memory graph panel — the star of the show. Cytoscape with lifecycle
// animations: pop-in on remember, purple glow on memify inferences, fade-out
// on forget, pulse on recall citations.
const Graph = (() => {
  let cy = null;
  // fact_id -> {label} for nodes we know map to remembered facts (for forget)
  const factNodes = new Map();

  const STYLE = [
    { selector: "node", style: {
      "background-color": "#22e6ff", "label": "data(label)", "color": "#d8d4e8",
      "font-family": "JetBrains Mono, monospace", "font-size": 8, "width": 14, "height": 14,
      "text-wrap": "ellipsis", "text-max-width": 90, "text-valign": "bottom", "text-margin-y": 4,
      "border-width": 0, "transition-property": "background-color, border-color, width, height, opacity",
      "transition-duration": "0.3s",
    }},
    { selector: 'node[type="inference"]', style: {
      "background-color": "#b26bff", "width": 18, "height": 18,
      "border-width": 3, "border-color": "rgba(178,107,255,.4)",
    }},
    { selector: "node.fresh", style: { "width": 24, "height": 24 } },
    { selector: "node.cited", style: {
      "border-width": 5, "border-color": "#ffb545", "width": 22, "height": 22,
    }},
    { selector: "node.suspect", style: { "border-width": 3, "border-color": "#ff4757" } },
    { selector: "node.dying", style: { "opacity": 0.05, "background-color": "#ff4757" } },
    // Cognee plumbing (chunks/summaries) stays visible for the judges but dimmed
    { selector: "node.plumbing", style: {
      "background-color": "#3a3157", "width": 8, "height": 8, "font-size": 5, "color": "#6f6a85",
    }},
    // fact-tag nodes (node_set ids like f13/rh1) glow amber — they anchor citations
    { selector: "node.facttag", style: {
      "background-color": "#ffb545", "shape": "diamond", "width": 16, "height": 16,
    }},
    { selector: "edge", style: {
      "width": 1, "line-color": "#3a3157", "curve-style": "bezier",
      "target-arrow-shape": "triangle", "target-arrow-color": "#3a3157", "arrow-scale": 0.6,
      "label": "data(label)", "font-size": 6, "color": "#6f6a85",
      "font-family": "JetBrains Mono, monospace", "text-rotation": "autorotate",
      "transition-property": "line-color, opacity", "transition-duration": "0.3s",
    }},
    { selector: 'edge.inference', style: {
      "line-color": "#b26bff", "target-arrow-color": "#b26bff", "width": 2, "line-style": "dashed",
    }},
    { selector: "edge.fresh", style: { "line-color": "#22e6ff", "target-arrow-color": "#22e6ff", "width": 2.5 } },
  ];

  function init() {
    cy = cytoscape({
      container: document.getElementById("graph"),
      elements: [], style: STYLE,
      layout: { name: "cose" },
    });
    cy.on("cxttap", "node", (evt) => Forget.openMenu(evt));
    // the graph container resizes when the recall answer box appears/disappears
    new ResizeObserver(() => { cy.resize(); cy.fit(undefined, 30); })
      .observe(document.getElementById("graph"));
    return cy;
  }

  function classify(node) {
    const label = node.data("label") || "";
    if (/^(DocumentChunk|TextSummary|TextDocument|EntityType)/.test(label)) node.addClass("plumbing");
    if (/^(f|rh)\d+$/.test(label)) node.addClass("facttag");
  }

  function relayout() {
    const layout = cy.layout({ name: "cose", animate: true, animationDuration: 600, padding: 20 });
    layout.one("layoutstop", () => cy.animate({ fit: { padding: 30 }, duration: 250 }));
    layout.run();
  }

  // Apply an incremental graph_delta from any backend response.
  function applyDelta(delta, { inference = false } = {}) {
    if (!delta) return { nodes: 0, edges: 0 };
    const addedN = [], addedE = [];
    for (const node of delta.added_nodes || []) {
      if (cy.getElementById(node.data.id).length) continue;
      const added = cy.add({ group: "nodes", ...node, classes: "fresh" });
      classify(added);
      addedN.push(added);
    }
    for (const edge of delta.added_edges || []) {
      if (cy.getElementById(edge.data.id).length) continue;
      if (!cy.getElementById(edge.data.source).length || !cy.getElementById(edge.data.target).length) continue;
      addedE.push(cy.add({ group: "edges", ...edge, classes: "fresh" }));
    }
    for (const id of delta.removed_node_ids || []) {
      const node = cy.getElementById(id);
      if (node.length) { node.addClass("dying"); setTimeout(() => node.remove(), 500); }
    }
    for (const id of delta.removed_edge_ids || []) cy.getElementById(id).remove();

    if (inference) {
      addedN.forEach(n => { n.data("type", "inference"); n.addClass("inference"); });
      addedE.forEach(e => e.addClass("inference"));
    }
    setTimeout(() => cy.elements().removeClass("fresh"), 1400);
    if (addedN.length || addedE.length) relayout();
    return { nodes: addedN.length, edges: addedE.length };
  }

  function fullSync(graph) {
    cy.elements().remove();
    cy.add(graph.nodes.map(n => ({ group: "nodes", ...n })));
    const ids = new Set(graph.nodes.map(n => n.data.id));
    cy.add(graph.edges.filter(e => ids.has(e.data.source) && ids.has(e.data.target))
      .map(e => ({ group: "edges", ...e, classes: e.data.id.includes("inference") ? "inference" : "" })));
    graph.nodes.forEach(n => { if (n.data.type === "inference") cy.getElementById(n.data.id).addClass("inference"); });
    cy.nodes().forEach(classify);
    relayout();
  }

  // Pulse-highlight recall citations.
  function citeNodes(ids) {
    cy.nodes().removeClass("cited");
    ids.forEach(id => cy.getElementById(id).addClass("cited"));
    if (ids.length) {
      const cited = cy.nodes(".cited");
      cy.animate({ fit: { eles: cited, padding: 80 }, duration: 500 });
      setTimeout(() => {
        cy.nodes().removeClass("cited");
        cy.animate({ fit: { padding: 30 }, duration: 400 });
      }, 4000);
    }
  }

  // Track which graph labels belong to a remembered fact so right-click →
  // forget can offer the right fact. We match on the fact's entity words.
  function registerFacts(facts) {
    for (const f of facts) factNodes.set(f.fact_id, f);
  }

  function factForNode(node) {
    const label = (node.data("label") || "").toLowerCase();
    let best = null, bestScore = 0;
    for (const [fid, fact] of factNodes) {
      if (fact.forgotten) continue;
      const words = fact.text.toLowerCase().split(/\W+/).filter(w => w.length > 3);
      const score = words.filter(w => label.includes(w)).length;
      if (score > bestScore) { best = fid; bestScore = score; }
    }
    return best;
  }

  function markForgotten(fid) {
    const fact = factNodes.get(fid);
    if (fact) fact.forgotten = true;
  }

  return { init, applyDelta, fullSync, citeNodes, registerFacts, factForNode, markForgotten, cyRef: () => cy };
})();
