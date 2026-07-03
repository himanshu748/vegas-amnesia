// Renders a 1280x720 YouTube thumbnail over a gameplay backdrop.
import { chromium } from "playwright";
import fs from "fs";

const bg = "data:image/png;base64," + fs.readFileSync("docs/media/hero.png").toString("base64");
const HTML = `<!DOCTYPE html><html><head>
<link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@600;700&family=Monoton&display=swap" rel="stylesheet">
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{width:1280px;height:720px;overflow:hidden;font-family:"Chakra Petch",sans-serif;position:relative}
  .bg{position:absolute;inset:0;background:url('${bg}') center/cover;filter:saturate(1.2) brightness(.55)}
  .scan{position:absolute;inset:0;background:repeating-linear-gradient(0deg,rgba(0,0,0,.25) 0 2px,transparent 2px 5px)}
  .vig{position:absolute;inset:0;background:radial-gradient(ellipse at center,transparent 30%,rgba(10,8,18,.85) 100%)}
  .wrap{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:20px}
  .kicker{font-size:26px;font-weight:700;letter-spacing:6px;color:#22e6ff;text-shadow:0 0 14px rgba(34,230,255,.9)}
  .title{font-family:"Monoton",cursive;font-size:118px;line-height:.95;color:#ff2e88;text-shadow:0 0 26px #ff2e88,0 0 90px rgba(255,46,136,.6)}
  .sub{font-size:30px;font-weight:600;color:#e4e0f2;text-shadow:0 2px 6px #000;max-width:900px}
  .sub b{color:#b26bff}
  .chips{display:flex;gap:14px;margin-top:6px}
  .chip{font-size:22px;font-weight:700;padding:8px 18px;border-radius:6px;border:2px solid;background:rgba(10,8,18,.6)}
  .c1{color:#22e6ff;border-color:#22e6ff}.c2{color:#ffb545;border-color:#ffb545}
  .c3{color:#b26bff;border-color:#b26bff}.c4{color:#ff2e88;border-color:#ff2e88}
</style></head><body>
  <div class="bg"></div><div class="scan"></div><div class="vig"></div>
  <div class="wrap">
    <div class="kicker">AN AI DETECTIVE GAME</div>
    <div class="title">VEGAS AMNESIA</div>
    <div class="sub">the <b>Cognee memory lifecycle</b> IS the gameplay — a live 3D memory graph you build, question, and prune</div>
    <div class="chips">
      <span class="chip c1">remember</span><span class="chip c2">recall</span>
      <span class="chip c3">memify</span><span class="chip c4">forget</span>
    </div>
  </div>
</body></html>`;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
await page.setContent(HTML, { waitUntil: "networkidle" });
await page.waitForTimeout(600);
await page.screenshot({ path: "docs/social/thumbnail.png" });
await browser.close();
console.log("thumbnail written");
