// Character chat drawer.
const Chat = (() => {
  let currentCharacter = null;

  function open(characterId, name) {
    currentCharacter = characterId;
    document.getElementById("chat-title").textContent = `INTERROGATING: ${name.toUpperCase()}`;
    document.getElementById("chat-drawer").classList.remove("hidden");
    document.getElementById("chat-input").focus();
  }

  function close() {
    currentCharacter = null;
    document.getElementById("chat-drawer").classList.add("hidden");
    document.getElementById("chat-log").innerHTML = "";
  }

  function push(role, text) {
    const log = document.getElementById("chat-log");
    const el = document.createElement("div");
    el.className = `msg ${role}`;
    el.textContent = text;
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }

  document.getElementById("chat-close").onclick = close;
  document.getElementById("chat-form").onsubmit = async (e) => {
    e.preventDefault();
    const input = document.getElementById("chat-input");
    const message = input.value.trim();
    if (!message || !currentCharacter) return;
    input.value = "";
    push("player", message);
    const thinking = push("thinking", "…");
    try {
      const resp = await api.talk(Main.sessionId(), currentCharacter, message);
      thinking.remove();
      push("character", resp.line);
      if (resp.facts.length) {
        Graph.registerFacts(resp.facts);
        Main.toast(`+${resp.facts.length} memory from testimony`, "");
      }
      const delta = Graph.applyDelta(resp.graph_delta);
      Main.updateHud(resp.hud);
      if (delta.nodes) Main.toast(`memory graph +${delta.nodes} nodes`, "");
    } catch (err) {
      thinking.remove();
      push("thinking", `[connection lost: ${err.message}]`);
    }
  };

  return { open, close, push };
})();
