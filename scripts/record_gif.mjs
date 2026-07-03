// Records a short highlight clip of the CURRENT UI for the README GIF.
import { chromium } from "playwright";
import fs from "fs";
const OUT = "docs/gif-raw";
fs.rmSync(OUT, { recursive: true, force: true }); fs.mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1280, height: 720 },
  recordVideo: { dir: OUT, size: { width: 1280, height: 720 } },
});
const page = await ctx.newPage();
await page.goto("http://localhost:8000/");
await page.waitForSelector("#game:not(.hidden)", { timeout: 30000 });
await page.waitForSelector("#howto:not(.hidden)", { timeout: 8000 }).catch(() => {});
await sleep(1500);
await page.click("#howto-close").catch(() => {});
await sleep(2500); // full-width scene beauty shot

// file two clues
for (const h of [1, 2]) {
  await page.click(`#hotspots .hotspot:nth-child(${h})`);
  await page.waitForSelector("#modal-backdrop:not(.hidden)", { timeout: 60000 });
  await sleep(1800);
  await page.click("#evidence-file");
  await sleep(1500);
}
// wait for memories to land
await page.waitForFunction(() => parseInt(document.getElementById("hud-memories").textContent) >= 2, null, { timeout: 120000 });
await sleep(1200);
// open the 3D memory graph
await page.click("#btn-graph");
await sleep(5000); // the graph orbits
// ask HAL
await page.fill("#recall-input", "Where is the engagement ring?");
await page.click("#recall-form button");
await page.waitForFunction(() => {
  const b = document.getElementById("recall-answer");
  return b && !b.classList.contains("hidden") && !b.textContent.includes("remembering");
}, null, { timeout: 90000 });
await sleep(4500);

await ctx.close();
await browser.close();
const f = fs.readdirSync(OUT).find((x) => x.endsWith(".webm"));
console.log("GIF RAW:", f);
