// Renders designed title cards + caption chips (game fonts/colors) to PNGs
// for the demo composite. Run: node scripts/make_cards.mjs
import { chromium } from "playwright";
import fs from "fs";

const OUT = "docs/cards";
fs.mkdirSync(OUT, { recursive: true });

const PAGE = `<!DOCTYPE html><html><head>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Monoton&display=swap" rel="stylesheet">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { width:1600px; height:900px; background:transparent; font-family:"JetBrains Mono",monospace; overflow:hidden; }
  .card { width:1600px; height:900px; background:#0a0812; display:flex; flex-direction:column;
          align-items:center; justify-content:center; gap:26px; position:relative; }
  .card::after { content:""; position:absolute; inset:0;
          background: repeating-linear-gradient(0deg, rgba(0,0,0,.18) 0 2px, transparent 2px 5px); }
  .title { font-family:"Monoton",cursive; font-size:110px; color:#ff2e88;
           text-shadow:0 0 24px #ff2e88, 0 0 80px rgba(255,46,136,.5); }
  .title.cyan { color:#22e6ff; text-shadow:0 0 24px #22e6ff, 0 0 80px rgba(34,230,255,.5); }
  .sub { font-size:26px; color:#d8d4e8; letter-spacing:1px; }
  .tiny { font-size:19px; color:#6f6a85; letter-spacing:2px; }
  .url { font-size:38px; font-weight:700; color:#22e6ff; text-shadow:0 0 18px rgba(34,230,255,.8);
         border:2px solid #22e6ff; border-radius:6px; padding:14px 30px; }
  .lifecycle { display:flex; gap:18px; margin-top:8px; }
  .lifecycle span { font-size:20px; font-weight:700; padding:8px 16px; border-radius:4px; border:1.5px solid; }
  .chipwrap { width:1600px; height:900px; display:flex; align-items:flex-end; justify-content:center;
              padding-bottom:26px; background:transparent; }
  .chip { max-width:1250px; font-size:31px; font-weight:700; letter-spacing:.5px; text-align:center;
          padding:16px 34px; border-radius:8px; background:rgba(10,8,18,.88);
          border:2px solid; line-height:1.35; }
  .chip small { display:block; font-size:17px; font-weight:400; color:#6f6a85; margin-top:5px; letter-spacing:1px; }
  .cyan2 { color:#22e6ff; border-color:#22e6ff; box-shadow:0 0 26px rgba(34,230,255,.45); }
  .amber2 { color:#ffb545; border-color:#ffb545; box-shadow:0 0 26px rgba(255,181,69,.45); }
  .purple2 { color:#b26bff; border-color:#b26bff; box-shadow:0 0 26px rgba(178,107,255,.45); }
  .pink2 { color:#ff2e88; border-color:#ff2e88; box-shadow:0 0 26px rgba(255,46,136,.45); }
</style></head><body></body></html>`;

const CARDS = {
  intro: `<div class="card">
    <div class="title">VEGAS AMNESIA</div>
    <div class="sub">an AI detective game built on the <b style="color:#b26bff">Cognee Cloud memory lifecycle</b></div>
    <div class="lifecycle">
      <span style="color:#22e6ff;border-color:#22e6ff">remember</span>
      <span style="color:#ffb545;border-color:#ffb545">recall</span>
      <span style="color:#b26bff;border-color:#b26bff">memify</span>
      <span style="color:#ff2e88;border-color:#ff2e88">forget</span>
    </div>
    <div class="tiny">WEMAKEDEVS × COGNEE — THE HANGOVER PART AI</div>
  </div>`,
  outro: `<div class="card">
    <div class="title cyan" style="font-size:76px">PLAY IT NOW</div>
    <div class="url">vegas-amnesia.vercel.app</div>
    <div class="sub">per-session Cognee datasets · live 3D memory graph · citations on every answer</div>
    <div class="tiny">BUILT WITH CLAUDE CODE · COGNEE CLOUD TRACK</div>
  </div>`,
};

const CHIPS = [
  ["cap1", "cyan2", "you are HAL-9001 — your memory graph was wiped", "reconstruct last night before noon"],
  ["cap2", "cyan2", "① REMEMBER — file the evidence you trust", "POST /api/v1/remember · not everything you find is true"],
  ["cap3", "cyan2", "every memory becomes nodes in a living 3D graph", "one Cognee dataset per investigation"],
  ["cap4", "amber2", "interrogate — characters react to what your graph knows", "LLM dialogue, graph-aware"],
  ["cap5", "amber2", "② RECALL — Ask HAL anything, sources cited", "POST /api/v1/recall · cited nodes pulse in the graph"],
  ["cap6", "purple2", "③ MEMIFY — connect the dots, derive new insights", "purple inference nodes · cognify + derivation"],
  ["cap7", "pink2", "④ FORGET — false memories get deleted for real", "POST /api/v1/forget · the red herring dies on screen"],
  ["cap8", "amber2", "SOLVE — the night reconstructed, every line cited", "coverage-scored against ground truth"],
  ["cap9", "purple2", "every Cognee call on the record — press backtick", "timed lifecycle log, in-game"],
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
await page.setContent(PAGE, { waitUntil: "networkidle" });

for (const [name, html] of Object.entries(CARDS)) {
  await page.evaluate((h) => (document.body.innerHTML = h), html);
  await page.waitForTimeout(350);
  await page.screenshot({ path: `${OUT}/${name}.png` });
  console.log("card", name);
}
for (const [name, cls, text, small] of CHIPS) {
  await page.evaluate(({ cls, text, small }) => {
    document.body.innerHTML =
      `<div class="chipwrap"><div class="chip ${cls}">${text}<small>${small}</small></div></div>`;
  }, { cls, text, small });
  await page.waitForTimeout(120);
  await page.screenshot({ path: `${OUT}/${name}.png`, omitBackground: true });
  console.log("chip", name);
}
await browser.close();
console.log("cards done");
