// Records a full winning playthrough of the CURRENT UI with beat timestamps.
// The graph panel is opened only to showcase changes, then closed so scene
// interactions (hotspots, character dock) aren't blocked by its canvas.
// Output: docs/demo-raw/<id>.webm + beats.json
import { chromium } from "playwright";
import fs from "fs";

const OUT = "docs/demo-raw";
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });

const beats = [];
let t0;
const mark = (name) => {
  const t = (Date.now() - t0) / 1000;
  beats.push({ name, t });
  console.log(`BEAT ${t.toFixed(1)}s  ${name}`);
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1600, height: 900 },
  recordVideo: { dir: OUT, size: { width: 1600, height: 900 } },
});
const page = await ctx.newPage();

const filed = () => page.evaluate(() => parseInt(document.getElementById("hud-memories").textContent) || 0);
const graphOpen = () => page.evaluate(() => document.getElementById("memory-panel").classList.contains("open"));
async function openGraph() { if (!(await graphOpen())) { await page.click("#btn-graph"); await sleep(700); } }
async function closeGraph() { if (await graphOpen()) { await page.click("#mempanel-close"); await sleep(500); } }

async function fileHotspot(nth) {
  await closeGraph();
  const before = await filed();
  await page.click(`#hotspots .hotspot:nth-child(${nth})`);
  await page.waitForSelector("#modal-backdrop:not(.hidden)", { timeout: 60000 });
  await sleep(1500);
  const fileBtn = await page.$("#evidence-file:not(.hidden)");
  if (fileBtn) { await fileBtn.click(); await page.waitForFunction((b) => (parseInt(document.getElementById("hud-memories").textContent)||0) > b, before, { timeout: 120000 }).catch(()=>{}); }
  else { await page.click("#evidence-close"); }
  await sleep(500);
}
async function goLoc(name) {
  await closeGraph();
  const tabs = await page.$$("#location-tabs .loc-tab");
  for (const t of tabs) { if (((await t.textContent()) || "").toUpperCase().includes(name)) { await t.click(); await sleep(800); return; } }
}
async function talk(msg, n = 1) {
  await closeGraph();
  await page.click("#character-dock");
  for (let i = 0; i < n; i++) {
    await page.fill("#chat-input", msg);
    await page.click("#chat-form button");
    await page.waitForSelector("#chat-log .msg.character", { timeout: 90000 });
    await sleep(1800);
  }
  await page.click("#chat-close").catch(()=>{});
}

await page.goto("http://localhost:8000/");
t0 = Date.now();
mark("boot_start");
await page.waitForSelector("#game:not(.hidden)", { timeout: 30000 });
await page.waitForSelector("#howto:not(.hidden)", { timeout: 8000 }).catch(() => {});
mark("howto");
await sleep(3500);
await page.click("#howto-close").catch(() => {});
mark("suite");
await sleep(2500);

// --- REMEMBER: file the safe note, then open the graph to watch nodes appear ---
mark("remember_click");
await page.click('#hotspots .hotspot:nth-child(2)');
await page.waitForSelector("#modal-backdrop:not(.hidden)", { timeout: 60000 });
mark("remember_modal");
await sleep(3000);
await page.click("#evidence-file");
mark("remember_filed");
await page.waitForFunction(() => (parseInt(document.getElementById("hud-memories").textContent)||0) >= 1, null, { timeout: 120000 });
await openGraph();
mark("graph_open");
await sleep(4500);

await fileHotspot(3);       // ice bucket
await openGraph();
mark("graph_grow");
await sleep(4000);

// --- TESTIMONY ---
mark("chat_open");
await closeGraph();
await page.click("#character-dock");
await page.fill("#chat-input", "Chad — what happened after the pawn shop?");
await page.click('#chat-form button');
await page.waitForSelector("#chat-log .msg.character", { timeout: 90000 });
mark("chat_reply");
await sleep(4500);
await page.click("#chat-close");

// --- RECALL (input lives in the graph panel) ---
await openGraph();
mark("recall_ask");
await page.fill("#recall-input", "Where is Priya's engagement ring?");
await page.click('#recall-form button');
await page.waitForFunction(() => { const b=document.getElementById("recall-answer"); return b && !b.classList.contains("hidden") && !b.textContent.includes("remembering"); }, null, { timeout: 90000 });
mark("recall_answer");
await sleep(4500);

// --- MEMIFY (topbar button; then show purple nodes in the open graph) ---
mark("memify_click");
await page.click("#btn-memify");
await page.waitForFunction(() => !document.getElementById("btn-memify").disabled, null, { timeout: 180000 });
await openGraph();
mark("memify_done");
await sleep(4500);

// --- FORGET via the Memory Log ---
await fileHotspot(5);       // lipstick napkin (rh1)
mark("herring_filed");
await sleep(1000);
await page.click("#hud-open-log").catch(async () => { await openGraph(); await page.click("#hud-open-log"); });
await page.waitForSelector("#memlog-backdrop:not(.hidden)", { timeout: 8000 });
mark("memlog_open");
await sleep(3000);
const forgetBtns = await page.$$(".mem-forget");
if (forgetBtns.length) { await forgetBtns[forgetBtns.length - 1].click(); }
mark("forget_click");
await page.waitForFunction(() => (parseInt(document.getElementById("hud-forgotten").textContent)||0) >= 1, null, { timeout: 90000 }).catch(()=>{});
await sleep(3500);
await page.click("#memlog-close").catch(()=>{});

// --- collect the rest of the key facts for a real WIN ---
await goLoc("CASINO"); await fileHotspot(1);
await goLoc("PAWN"); await fileHotspot(1);
await goLoc("CHAPEL"); await fileHotspot(1);
await goLoc("ROSA"); await talk("Rosa, what did you see?", 4);
await goLoc("CHAPEL"); await talk("Reverend, was it a real wedding?", 3);
await goLoc("HOTEL"); await talk("Chad, what else do you remember?", 3);
await goLoc("PAWN"); await talk("Lou, explain this receipt.", 2);
mark("collected");
await sleep(1200);

// --- SOLVE → win animation ---
await closeGraph();
mark("solve_click");
await page.click("#btn-solve");
await page.waitForSelector("#ending-screen:not(.hidden)", { timeout: 120000 });
mark("ending");
await sleep(6000);
await page.click("#ending-close");

// --- the receipts: debug overlay ---
mark("debug_open");
await page.keyboard.press("`");
await sleep(1500);
mark("debug_table");
await sleep(4500);
mark("end");

await ctx.close();
await browser.close();
fs.writeFileSync(`${OUT}/beats.json`, JSON.stringify(beats, null, 2));
const f = fs.readdirSync(OUT).find((x) => x.endsWith(".webm"));
console.log("VIDEO:", f);
