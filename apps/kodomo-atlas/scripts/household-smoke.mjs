/** Focused browser check for the household / marital-status layer (local dev server only). */
import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const target = new URL("http://127.0.0.1:5173/");
const output = new URL("../qa/screenshots/", import.meta.url);
await mkdir(output, { recursive: true });
const data = JSON.parse(await readFile(new URL("../public/data/households.json", import.meta.url), "utf8"));
const stats = JSON.parse(await readFile(new URL("../public/data/statistics.json", import.meta.url), "utf8"));
const row = (code) => Object.fromEntries(data.fields.map((f, i) => [f, data.regions[code][i]]));
const nf = new Intl.NumberFormat("ja-JP", { maximumFractionDigits: 0 });
const share = (v) => (v === null ? "—" : v.toFixed(1));
const national = row("00000");
const toyonaka = row("27203");
const report = { startedAt: new Date().toISOString(), checks: [], runtimeErrors: [], blockedExternal: [], status: "running" };
const pass = (label) => { report.checks.push(label); console.log(`PASS: ${label}`); };

const browser = await chromium.launch({ channel: "chrome", headless: true, chromiumSandbox: true });
async function open(viewport, mobile = false) {
  const context = await browser.newContext({ viewport, locale: "ja-JP", reducedMotion: "reduce", isMobile: mobile, hasTouch: mobile, serviceWorkers: "block" });
  await context.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (url.origin === target.origin) return route.continue();
    report.blockedExternal.push(url.href);
    return route.abort("blockedbyclient");
  });
  await context.routeWebSocket(/.*/, (socket) => (new URL(socket.url()).host === target.host ? socket.connectToServer() : socket.close()));
  const page = await context.newPage();
  page.setDefaultTimeout(8000);
  page.on("pageerror", (error) => report.runtimeErrors.push(error.message));
  await page.goto(target.href, { waitUntil: "networkidle" });
  await page.locator(".map-canvas .leaflet-overlay-pane svg path").first().waitFor();
  return page;
}
const title = (page) => page.locator(".map-panel-heading h3").first().textContent();
const big = (page) => page.locator(".detail-big-number").textContent();
async function search(page, name, code) {
  await page.getByRole("combobox", { name: "都道府県・市区町村を検索" }).fill(name);
  await page.getByRole("option").filter({ hasText: code }).click();
  await page.locator(".map-selection-info .selected-region-name").first().filter({ hasText: name }).waitFor();
  await page.locator(".leaflet-zoom-anim").waitFor({ state: "detached" });
}
async function aligned(page) {
  await page.waitForFunction(() => {
    const maps = [...document.querySelectorAll(".map-canvas")];
    if (maps.length !== 2) return false;
    const at = (map) => {
      const label = [...map.querySelectorAll(".city-label")].find((e) => e.textContent === "大阪");
      const a = label.getBoundingClientRect(), b = map.getBoundingClientRect();
      return [a.left - b.left, a.top - b.top];
    };
    const [a, b] = maps.map(at);
    return Math.abs(a[0] - b[0]) <= 2 && Math.abs(a[1] - b[1]) <= 2;
  });
}

try {
  const page = await open({ width: 1440, height: 900 });
  assert.deepEqual(await page.getByRole("tab").allTextContents(), ["出生・子ども", "世帯構造", "未婚・高齢化"]);
  await page.getByRole("tab", { name: "世帯構造" }).click();
  await page.getByRole("button", { name: "単独世帯", exact: true }).click();
  assert.equal(await title(page), "単独世帯の割合");
  assert.equal(await page.locator(".map-year").textContent(), "2020年");
  assert.equal(await big(page), `${share(national.singleShare)}%`);
  assert.equal(await page.locator(".map-key .ramp-national").textContent(), `全国 ${share(national.singleShare)}`);
  assert.equal(share(national.singleShare), "38.1");
  await page.getByRole("button", { name: "数", exact: true }).click();
  assert.equal(await title(page), "単独世帯数");
  assert.equal(await big(page), `${nf.format(national.single)}世帯`);
  await page.getByRole("button", { name: "夫婦と子どもの世帯", exact: true }).click();
  assert.equal(await title(page), "夫婦と子どもから成る世帯数", "share/count choice carries over");
  await page.getByRole("button", { name: "割合（%）", exact: true }).click();
  assert.equal(await title(page), "夫婦と子どもから成る世帯の割合");
  await page.getByRole("button", { name: "18歳未満のいる世帯", exact: true }).click();
  assert.equal(await title(page), "18歳未満の世帯員がいる世帯の割合");
  pass("世帯構造 tab: 単独世帯・夫婦と子ども・18歳未満のいる世帯; share/count toggle; national 38.1% and 21,151,042 households");

  await page.getByRole("tab", { name: "未婚・高齢化" }).click();
  await page.getByRole("button", { name: "25〜39歳の未婚", exact: true }).click();
  assert.equal(await title(page), "25〜39歳の未婚率");
  for (const [sex, key, label] of [["男性", "unmarriedRateMale", "（男性）"], ["女性", "unmarriedRateFemale", "（女性）"]]) {
    await page.getByRole("button", { name: sex, exact: true }).click();
    assert.equal(await title(page), `25〜39歳の未婚率${label}`);
    assert.equal(await big(page), `${share(national[key])}%`);
  }
  await page.getByRole("button", { name: "数", exact: true }).click();
  assert.equal(await title(page), "25〜39歳の未婚者数（女性）");
  assert.equal(await big(page), `${nf.format(national.unmarriedFemale)}人`);
  await page.getByRole("button", { name: "高齢者のみの世帯", exact: true }).click();
  await page.getByRole("button", { name: "割合（%）", exact: true }).click();
  assert.equal(await title(page), "65歳以上の世帯員のみの世帯の割合");
  assert.equal(await big(page), `${share(national.elderlyOnlyShare)}%`);
  await page.getByRole("button", { name: "65歳以上の単独世帯", exact: true }).click();
  assert.equal(await title(page), "65歳以上の単独世帯の割合");
  pass("未婚・高齢化 tab: 25〜39歳未婚率 total/male/female and count; 高齢者のみの世帯; 65歳以上の単独世帯");

  await search(page, "豊中市", "27203");
  assert.equal(await page.locator(".map-selection-info strong").textContent(), `${share(toyonaka.elderlySingleShare)}%`);
  const grid = await page.locator(".household-stats button").allTextContents();
  for (const [i, key] of ["singleShare", "coupleChildrenShare", "under18Share", "unmarriedRate", "elderlyOnlyShare", "elderlySingleShare"].entries())
    assert(grid[i].includes(`${share(toyonaka[key])}%`), `${key} in region panel`);
  assert(grid[3].includes(`男性 ${share(toyonaka.unmarriedRateMale)}%`) && grid[3].includes(`女性 ${share(toyonaka.unmarriedRateFemale)}%`));
  const reference = await page.locator(".reference-line").textContent();
  assert(reference.includes(`${(toyonaka.withElderly / toyonaka.general * 100).toFixed(1)}%`) && reference.includes("「高齢者のみの世帯」とは別"));
  pass("豊中市: map card and region panel show the published values; 65歳以上の「いる」世帯 is a separate reference");

  await page.getByRole("button", { name: "ランキング", exact: true }).click();
  const units = stats.municipalities.map((r) => ({ ...r, h: row(r.code) })).filter((r) => r.h.elderlySingleShare !== null);
  units.sort((a, b) => b.h.elderlySingleShare - a.h.elderlySingleShare || a.code.localeCompare(b.code));
  assert.equal(await page.locator("#ranking-title").textContent(), "65歳以上の単独世帯の割合");
  assert((await page.locator("tbody tr").first().textContent()).includes(units[0].name));
  assert((await page.locator(".ranking-table-heading p").textContent()).includes(`${nf.format(units.length)}地域`));
  await page.getByRole("button", { name: "地図で見る", exact: true }).click();
  await search(page, "豊中市", "27203");
  pass(`Ranking uses the 1,896 units only (${nf.format(units.length)} with values; top: ${units[0].prefecture}${units[0].name})`);

  const labels = { tfr: "合計特殊出生率", childShare: "年少人口比率", under18Share: "18歳未満の世帯員がいる世帯の割合" };
  const tfr = stats.municipalities.find((r) => r.code === "27203");
  for (const [name, left, right] of [
    ["出生率 × 25〜39歳未婚率", "tfr", "unmarriedRate"],
    ["年少人口比率 × 高齢者のみの世帯率", "childShare", "elderlyOnlyShare"],
    ["出生率 × 単独世帯率", "tfr", "singleShare"],
    ["18歳未満のいる世帯率 × 単独世帯率", "under18Share", "singleShare"],
  ]) {
    await page.getByRole("button", { name: new RegExp(`^${name.replace(/[×]/g, "\\$&")}`) }).click();
    assert.equal(await page.locator(".map-panel").count(), 2);
    assert.equal(await title(page), labels[left]);
    assert.equal(await page.getByRole("combobox", { name: "比較する2つ目の指標" }).inputValue(), right);
    assert.deepEqual(await page.locator(".map-year").allTextContents(), [left === "tfr" ? "2018–2022年" : "2020年", "2020年"]);
    const cards = await page.locator(".map-selection-info strong").allTextContents();
    const leftValue = left === "tfr" ? tfr.tfr.toFixed(2) : `${share(left === "childShare" ? tfr.childShare : toyonaka[left])}%`;
    assert.equal(cards[0], leftValue, `${name}: map A value`);
    assert.equal(cards[1], `${share(toyonaka[right])}%`, `${name}: map B value`);
    await aligned(page);
  }
  assert.equal(await page.locator(".map-panel .map-key").count(), 2);
  await page.screenshot({ path: fileURLToPath(new URL("households-compare.png", output)) });
  pass("Four one-tap comparisons: A/B indicators and periods, 豊中市 values on both maps, synchronized maps");

  await page.getByRole("button", { name: "比較を終了", exact: true }).click();
  await page.getByRole("tab", { name: "世帯構造" }).click();
  await page.getByRole("button", { name: "単独世帯", exact: true }).click();
  await search(page, "双葉町", "07546");
  assert.equal(await page.locator(".map-selection-info strong").textContent(), "—データなし・非公表");
  assert.equal(await big(page), "—");
  pass("双葉町 (2020 population 0): household shares are undefined (—), never 0");

  await page.getByRole("button", { name: "データについて", exact: true }).click();
  const dialog = await page.getByRole("dialog").textContent();
  for (const text of ["第9-1表", "第27-4表", "第4-3表", "第4-4表", "「単独世帯」と「未婚者」は別の指標です", "「65歳以上の世帯員がいる世帯」と「65歳以上の世帯員のみの世帯」も別です", "因果関係を示すものではありません", "家族類型「不詳」"])
    assert(dialog.includes(text), text);
  await page.getByRole("button", { name: "説明を閉じる", exact: true }).click();
  pass("Data dialog: four official sources, denominators, 単独世帯≠未婚者, 「いる」≠「のみ」, no causal claim");

  const phone = await open({ width: 390, height: 844 }, true);
  await phone.getByRole("tab", { name: "世帯構造" }).click();
  await phone.getByRole("button", { name: /^18歳未満のいる世帯率 × 単独世帯率/ }).click();
  const [a, b] = await Promise.all((await phone.locator(".map-panel").all()).map((p) => p.boundingBox()));
  assert(a.width >= 340 && b.width >= 340 && b.y > a.y);
  const key = await phone.locator(".map-panel").nth(1).locator(".map-key").boundingBox();
  const select = await phone.getByRole("combobox", { name: "比較する2つ目の指標" }).boundingBox();
  assert(select.x + select.width <= key.x + key.width + 1, "Map B indicator select stays inside its legend");
  assert(!(await phone.evaluate(() => document.documentElement.scrollWidth > innerWidth)), "No horizontal overflow");
  await phone.screenshot({ path: fileURLToPath(new URL("households-mobile.png", output)) });
  pass("390px: category tabs, preset comparison stacked full width, select inside legend, no horizontal overflow");

  assert.deepEqual(report.runtimeErrors, []);
  report.status = "passed";
  pass("No runtime exceptions; external requests blocked");
} catch (error) {
  report.status = "failed";
  report.failure = error.stack;
  throw error;
} finally {
  report.finishedAt = new Date().toISOString();
  report.blockedExternal = [...new Set(report.blockedExternal)];
  await writeFile(new URL("../qa/household-results.json", import.meta.url), JSON.stringify(report, null, 2));
  await browser.close();
}
