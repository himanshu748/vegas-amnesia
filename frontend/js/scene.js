// Scene rendering: backdrop, hotspots, character dock, evidence modal.
const Scene = (() => {
  let manifest = { characters: {}, locations: {}, evidence: {} };

  // Hand-placed hotspot positions (percent of scene, per location).
  const POSITIONS = {
    hotel_suite: { dead_phone: [22, 72], safe_note: [80, 38], ice_bucket_cash: [58, 60], room_service_receipt: [38, 82], lipstick_napkin: [68, 84] },
    casino_floor: { casino_chip_receipt: [30, 62], stray_pawn_ticket: [55, 78], security_report: [78, 55], blackjack_table: [45, 45] },
    rosas_bar: { bar_polaroid: [30, 40], bar_tab: [55, 65], neon_matchbook: [75, 78] },
    chapel: { chapel_polaroid: [25, 45], gift_shop_rack: [72, 60], guestbook: [50, 78] },
    pawn_shop: { pawn_receipt: [60, 65], watch_case: [30, 55], lous_ledger: [80, 80] },
    parking_garage: { parking_stub: [40, 70], stray_keycard: [60, 62], rooftop_view: [80, 30] },
  };

  const EVIDENCE_ICONS = {
    dead_phone: "📱", safe_note: "🗒️", ice_bucket_cash: "🪣", room_service_receipt: "🥞",
    lipstick_napkin: "💋", casino_chip_receipt: "🎰", stray_pawn_ticket: "🎫",
    security_report: "📋", blackjack_table: "🃏", bar_polaroid: "📸", bar_tab: "🧾",
    neon_matchbook: "🔥", chapel_polaroid: "💒", gift_shop_rack: "💍", guestbook: "📖",
    pawn_receipt: "🧾", watch_case: "⌚", lous_ledger: "📒", parking_stub: "🅿️",
    stray_keycard: "🔑", rooftop_view: "🌆",
  };

  async function loadManifest() {
    try { manifest = await (await fetch("assets/manifest.json")).json(); }
    catch { /* placeholders take over */ }
  }

  function render(location, characterMeta) {
    const backdrop = document.getElementById("scene-backdrop");
    const img = manifest.locations[location.id];
    backdrop.style.backgroundImage = img ? `url(${img})` : "none";
    backdrop.style.backgroundColor = img ? "" : "#141021";
    document.getElementById("scene-title").textContent = location.name.toUpperCase();
    document.getElementById("scene-desc").textContent = location.description;

    const wrap = document.getElementById("hotspots");
    wrap.innerHTML = "";
    for (const h of location.hotspots) {
      const [x, y] = (POSITIONS[location.id] || {})[h.id] || [50, 50];
      const el = document.createElement("button");
      el.className = "hotspot" + (h.inspected ? " inspected" : "");
      el.style.left = x + "%"; el.style.top = y + "%";
      el.innerHTML = `<span class="ring"></span><span class="tag">${h.name}</span>`;
      el.onclick = () => Main.inspectHotspot(location.id, h.id, el);
      wrap.appendChild(el);
    }

    const dock = document.getElementById("character-dock");
    if (location.character && characterMeta) {
      dock.classList.remove("hidden");
      const portrait = document.getElementById("character-portrait");
      portrait.src = manifest.characters[location.character] || "";
      portrait.alt = characterMeta.name;
      document.getElementById("character-name").textContent = `TALK TO ${characterMeta.name.toUpperCase()}`;
      dock.onclick = () => Chat.open(location.character, characterMeta.name);
    } else {
      dock.classList.add("hidden");
      Chat.close();
    }
  }

  function showEvidenceModal(hotspot, facts, onFile) {
    const img = (manifest.evidence || {})[hotspot.id];
    const icon = document.getElementById("evidence-icon");
    icon.innerHTML = img
      ? `<img src="${img}" alt="" style="width:190px;height:190px;object-fit:cover;border-radius:6px;border:1px solid var(--cyan)">`
      : (EVIDENCE_ICONS[hotspot.id] || "🔎");
    document.getElementById("evidence-name").textContent = hotspot.name;
    document.getElementById("evidence-desc").textContent = hotspot.description;
    const factsEl = document.getElementById("evidence-facts");
    factsEl.innerHTML = "";
    const unfiled = facts.filter(f => !f.already_filed);
    facts.forEach((f, i) => {
      const chip = document.createElement("div");
      chip.className = "fact-chip" + (f.already_filed ? " filed" : "");
      chip.style.animationDelay = `${i * 0.25}s`;
      chip.textContent = f.text;
      factsEl.appendChild(chip);
    });

    const fileBtn = document.getElementById("evidence-file");
    const closeBtn = document.getElementById("evidence-close");
    if (unfiled.length) {
      fileBtn.classList.remove("hidden");
      closeBtn.textContent = "LEAVE IT";
      fileBtn.onclick = () => {
        document.getElementById("modal-backdrop").classList.add("hidden");
        onFile && onFile();
      };
    } else {
      fileBtn.classList.add("hidden");
      closeBtn.textContent = facts.length ? "ALREADY ON FILE" : "NOTED";
      fileBtn.onclick = null;
    }
    document.getElementById("modal-backdrop").classList.remove("hidden");
  }

  document.getElementById("evidence-close").onclick =
    () => document.getElementById("modal-backdrop").classList.add("hidden");
  document.getElementById("modal-backdrop").onclick = (e) => {
    if (e.target.id === "modal-backdrop") e.target.classList.add("hidden");
  };

  function showBubble(text) {
    const bubble = document.getElementById("speech-bubble");
    bubble.textContent = text.length > 220 ? text.slice(0, 217) + "…" : text;
    bubble.classList.remove("hidden");
    clearTimeout(showBubble._t);
    showBubble._t = setTimeout(() => bubble.classList.add("hidden"), 9000);
  }

  return { loadManifest, render, showEvidenceModal, showBubble };
})();
