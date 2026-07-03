// Records a real playthrough of Vegas Amnesia (localhost:8000) to webm,
// logging beat timestamps for ffmpeg cutting. Run:
//   node scripts/record_demo.mjs
import { chromium } from "playwright";
import fs from "fs";

const OUT = "docs/demo-raw";
fs.mkdirSync(OUT, { recursive: true });

const beats = [];
const t0 = Date.now();
const mark = (name) => {
  beats.push({ name, t: (Date.now() - t0) / 1000 });
  console.log(`BEAT ${((Date.now() - t0) / 1000).toFixed(1)}s  ${name}`);
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1600, height: 900 },
  recordVideo: { dir: OUT, size: { width: 1600, height: 900 } },
});
const page = await ctx.newPage();

await page.goto("http://localhost:8000/");
mark("boot_start");
await page.waitForSelector("#game:not(.hidden)", { timeout: 30000 });
await page.waitForSelector("#howto:not(.hidden)", { timeout: 8000 }).catch(() => {});
mark("howto");
await sleep(3500); // let viewers read the tutorial card
await page.click("#howto-close").catch(() => {});
mark("suite");
await sleep(2500);

// --- REMEMBER: safe note (f13+f14) ---
mark("remember_click");
await page.click('#hotspots .hotspot:nth-child(2)');
await page.waitForSelector("#modal-backdrop:not(.hidden)", { timeout: 60000 });
mark("remember_modal");
await sleep(3200);
await page.click("#evidence-file");
mark("remember_filed");
await page.waitForFunction(() => document.getElementById("hud-memories").textContent !== "0", null, { timeout: 120000 });
mark("remember_graph");
await sleep(4500); // graph animates in

// --- second evidence for a fuller graph: ice bucket (f20) ---
await page.click('#hotspots .hotspot:nth-child(3)');
await page.waitForSelector("#modal-backdrop:not(.hidden)", { timeout: 60000 });
await sleep(2200); // evidence art visible in modal
await page.click("#evidence-file");
await page.waitForFunction(() => parseInt(document.getElementById("hud-memories").textContent) >= 3, null, { timeout: 120000 });
mark("evidence2_graph");
await sleep(4000);

// --- TESTIMONY: Chad (LLM dialogue) ---
mark("chat_open");
await page.click("#character-dock");
await page.fill("#chat-input", "Chad — what happened after the pawn shop?");
await page.click('#chat-form button');
await page.waitForSelector("#chat-log .msg.character", { timeout: 90000 });
mark("chat_reply");
await sleep(4500);
await page.click("#chat-close");

// --- RECALL: Ask HAL ---
mark("recall_ask");
await page.fill("#recall-input", "Where is Priya's engagement ring?");
await page.click('#recall-form button');
await page.waitForFunction(() => {
  const b = document.getElementById("recall-answer");
  return b && !b.classList.contains("hidden") && !b.textContent.includes("remembering");
}, null, { timeout: 120000 });
mark("recall_answer");
await sleep(4500); // citation pulse

// --- MEMIFY: consolidate ---
mark("memify_click");
await page.click("#btn-memify");
await page.waitForFunction(() => !document.getElementById("btn-memify").disabled, null, { timeout: 180000 });
mark("memify_done");
await sleep(4500); // purple nodes settle

// --- FORGET: plant the red herring, then prune it ---
await page.evaluate(() => { window.__preHerring = parseInt(document.getElementById("hud-memories").textContent); });
await page.click('#hotspots .hotspot:nth-child(5)'); // lipstick napkin
await page.waitForSelector("#modal-backdrop:not(.hidden)", { timeout: 60000 });
mark("herring_modal");
await sleep(3000);
await page.click("#evidence-file");
await page.waitForFunction(() => parseInt(document.getElementById("hud-memories").textContent) >= (window.__preHerring || 0) + 1, null, { timeout: 120000 }).catch(() => {});
await sleep(2500);
mark("forget_rightclick");
// drive the forget flow through the same path the right-click menu uses
// (right-clicking a specific 3D node from playwright is not deterministic)
await page.evaluate(async () => {
  const resp = await api.forget(Main.sessionId(), "rh1");
  Graph.markForgotten("rh1");
  Graph.applyDelta(resp.graph_delta);
  Main.updateHud(resp.hud);
  Main.toast("🗑 forgot rh1 — red herring pruned from memory", "error");
});
mark("forget_fade");
await sleep(4500);

// --- SOLVE ---
mark("solve_click");
await page.click("#btn-solve");
await page.waitForSelector("#ending-screen:not(.hidden)", { timeout: 120000 });
mark("ending");
await sleep(5000);
await page.click("#ending-close");

// --- DEBUG OVERLAY: the Cognee receipts ---
mark("debug_open");
await page.keyboard.press("`");
await sleep(1500);
mark("debug_table");
await sleep(4500);
mark("end");

await ctx.close();
await browser.close();
fs.writeFileSync(`${OUT}/beats.json`, JSON.stringify(beats, null, 2));
const files = fs.readdirSync(OUT).filter((f) => f.endsWith(".webm"));
console.log("VIDEO:", files, "beats saved");
