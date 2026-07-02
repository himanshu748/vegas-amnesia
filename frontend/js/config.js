// API base: same-origin by default (HF Spaces serves both), overridable for
// local dev (?api=http://localhost:8000) or a hardcoded prod backend.
const HF_BACKEND = "https://himanshukumarjha-vegas-amnesia.hf.space";

const API_BASE = (() => {
  const param = new URLSearchParams(location.search).get("api");
  if (param) return param.replace(/\/$/, "");
  if (["3000", "3001"].includes(location.port)) return "http://localhost:8000"; // local dev
  if (location.hostname.endsWith(".hf.space") || location.hostname === "localhost") return ""; // same origin
  return HF_BACKEND; // Vercel (or any other static host) -> HF Space API
})();

const GAME_MINUTES_PER_REAL_SECOND = 0.6; // 6:00AM -> noon in ~10 real minutes
