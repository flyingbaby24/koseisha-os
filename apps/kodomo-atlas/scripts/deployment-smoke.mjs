/** Verify only deployment-specific routing; never attach to a personal browser. */
import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const production = process.argv.includes("--production");
const origin = production ? "https://www.jinn-project.com" : "http://127.0.0.1:4173";
const appUrl = `${origin}/kodomo-atlas/`;
const prefix = production ? "production" : "static-preview";
const out = new URL("../qa/", import.meta.url);
await mkdir(out, { recursive: true });
const report = { origin, appUrl, startedAt: new Date().toISOString(), checks: [], errors: [], httpErrors: [], screenshots: [], statistics: {}, status: "running" };
const hash = bytes => createHash("sha256").update(bytes).digest("hex");
const expected = Object.fromEntries(await Promise.all(["statistics.json", "municipalities.geojson"].map(async file => [file, hash(await readFile(new URL(`../public/data/${file}`, import.meta.url)))])));
for (const pathname of ["/", "/index-ja.html", "/kodomo-atlas/"]) {
  const response = await fetch(`${origin}${pathname}`, { redirect: "error" });
  assert.equal(response.status, 200, pathname);
  const html = await response.text();
  assert(html.includes(pathname.includes("kodomo-atlas") ? "こどもアトラス" : "Jinn Project"));
}
const browser = await chromium.launch({ channel: "chrome", headless: true, chromiumSandbox: true });
let lastPage;
const bodyChecks = [];
function pass(message) { report.checks.push(message); console.log(`PASS: ${message}`); }
async function open(viewport, touch = false) {
  const context = await browser.newContext({ viewport, isMobile: touch, hasTouch: touch, locale: "ja-JP", reducedMotion: "reduce", serviceWorkers: "block" });
  await context.route("**/*", route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort("blockedbyclient"));
  const page = await context.newPage(); lastPage = page; page.setDefaultTimeout(30000);
  page.on("pageerror", error => report.errors.push(error.message));
  page.on("request", request => {
    if (new URL(request.url()).origin === origin) assert(!/127\.0\.0\.1|localhost/.test(request.url()) || !production);
  });
  page.on("response", response => {
    const url = new URL(response.url());
    if (url.origin !== origin) return;
    if (response.status() >= 400) report.httpErrors.push(`${response.status()} ${url.pathname}`);
    const file = url.pathname.split("/").at(-1);
    if (expected[file]) bodyChecks.push(response.body().then(bytes => {
      assert.equal(hash(bytes), expected[file], `Published data unchanged: ${file}`);
      report.statistics[file] = { status: response.status(), sha256: hash(bytes), bytes: bytes.length };
    }));
  });
  return page;
}
async function loaded(page) { await page.locator(".map-canvas svg path.leaflet-interactive").first().waitFor(); }
async function search(page, name, code) {
  await page.getByRole("combobox", { name: "都道府県・市区町村を検索" }).fill(name);
  await page.getByRole("option").filter({ hasText: code }).click();
  await page.locator(".map-selection-info .selected-region-name").first().filter({ hasText: name }).waitFor();
}
async function shot(page, name, locator) {
  const path = fileURLToPath(new URL(`${prefix}-${name}.png`, out));
  if (locator) {
    await locator.scrollIntoViewIfNeeded();
    await locator.locator("img").evaluateAll(images => Promise.all(images.map(image => image.decode())));
    await page.screenshot({ path, animations: "disabled" });
  }
  else await page.screenshot({ path, fullPage: true, animations: "disabled" });
  report.screenshots.push(path);
}
try {
  const page = await open({ width: 1600, height: 1100 });
  for (const language of ["/index-ja.html", "/"]) {
    await page.goto(`${origin}${language}`, { waitUntil: "networkidle" });
    const card = page.locator("#p-kodomo-atlas");
    assert.equal(await card.getAttribute("href"), "/kodomo-atlas/");
    assert((await card.textContent()).includes("Kodomo Atlas"));
    assert.equal(await page.locator(".work-item").count(), 8);
    if (language.includes("ja")) {
      assert((await card.textContent()).includes("全国の出生率と子どもの人口分布"));
      await shot(page, "home", card);
    }
  }
  await page.locator("#p-kodomo-atlas").click();
  await loaded(page); assert.equal(page.url(), appUrl);
  assert.equal(await page.locator(".map-canvas svg path.leaflet-interactive").count(), 1902);
  assert.equal(await page.locator(".reference-box b").textContent(), "1.33");
  pass("English/Japanese project cards, eight existing/new entries, top-to-app navigation and nationwide map");
  await shot(page, "atlas");
  await page.getByRole("button", { name: "2つの指標を比較", exact: true }).click();
  await page.getByRole("combobox", { name: "比較する2つ目の指標" }).selectOption("childShare");
  assert.equal(await page.getByRole("combobox", { name: "比較する2つ目の指標" }).locator("option").count(), 8);
  for (const [name, code, tfr, share] of [["大阪市", "27100", "1.16", "11.0"], ["豊中市", "27203", "1.50", "13.7"], ["明石市", "28203", "1.63", "13.8"]]) {
    await search(page, name, code);
    const text = await page.locator(".map-selection-info").allTextContents();
    assert(text[0].includes(tfr) && text[1].includes(share));
  }
  const [a,b] = await Promise.all((await page.locator(".map-panel").all()).map(panel => panel.boundingBox()));
  assert(a.x < b.x && Math.abs(a.y - b.y) < 1);
  assert.equal(await page.locator(".compare-legend[open]").count(), 2);
  assert.deepEqual(await page.locator(".map-year").allTextContents(), ["2018–2022年", "2020年"]);
  await search(page, "大阪市", "27100");
  await page.locator(".map-zoom-controls").first().getByRole("button", { name: "地図を縮小", exact: true }).click();
  await page.locator(".leaflet-zoom-anim").waitFor({ state: "detached" });
  await shot(page, "comparison");
  pass("Production paths preserve Osaka/Toyonaka/Akashi searches, PC side-by-side comparison and both legends");
  await page.reload({ waitUntil: "networkidle" }); await loaded(page);
  assert.equal(await page.locator(".map-canvas svg path.leaflet-interactive").count(), 1902);
  await page.getByRole("button", { name: "ランキング", exact: true }).click();
  assert.equal(await page.locator("tbody tr").count(), 25);
  pass("Direct app URL, page reload and ranking work without SPA fallback or local API");

  const phone = await open({ width: 390, height: 844 }, true);
  await phone.goto(appUrl, { waitUntil: "networkidle" }); await loaded(phone);
  await phone.locator(".mobile-filter-button").click(); await search(phone, "豊中市", "27203");
  await phone.getByRole("button", { name: "2つの指標を比較", exact: true }).click();
  await phone.getByRole("combobox", { name: "比較する2つ目の指標" }).selectOption("childShare");
  const [mobileA,mobileB] = await Promise.all((await phone.locator(".map-panel").all()).map(panel => panel.boundingBox()));
  assert(mobileA.width > 340 && mobileB.y > mobileA.y);
  assert.equal(await phone.locator(".compare-legend[open]").count(), 2);
  assert(!(await phone.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
  await shot(phone, "mobile");
  pass("390px direct access, search, stacked comparison and legends without horizontal overflow");
  await Promise.all(bodyChecks);
  assert.deepEqual(report.errors, []); assert.deepEqual(report.httpErrors, []);
  assert.equal(Object.keys(report.statistics).length, 2);
  pass("CSS/JS/images/statistics/GeoJSON load without HTTP errors; published data hashes match originals");
  report.status = "passed";
} catch (error) {
  report.status = "failed"; report.failure = error.stack;
  if (lastPage) await shot(lastPage, "failure").catch(() => {});
  throw error;
} finally {
  report.finishedAt = new Date().toISOString();
  await writeFile(new URL(`${prefix}-results.json`, out), JSON.stringify(report, null, 2));
  await browser.close();
}
