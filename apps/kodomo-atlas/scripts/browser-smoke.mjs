/** Local-only browser smoke test. Never attach to the user's browser/profile. */
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const target = new URL("http://127.0.0.1:5173/");
assert.equal(target.origin, "http://127.0.0.1:5173");
assert.equal(target.pathname, "/");
const preflight = await fetch(target, { redirect: "error" });
assert.equal(preflight.status, 200);
assert((await preflight.text()).includes("こどもアトラス"));
const output = new URL("../qa/screenshots/", import.meta.url);
await mkdir(output, { recursive: true });
const report = {
  url: target.href,
  startedAt: new Date().toISOString(),
  viewport: {},
  checks: [],
  screenshots: [],
  blockedExternal: [],
  runtimeErrors: [],
  localHttpErrors: [],
  browser: "",
  status: "running",
};
const check = (label) => {
  report.checks.push(label);
  console.log(`PASS: ${label}`);
};
console.log(
  `Preflight: ${target.href} HTTP 200, expected title, redirects forbidden`,
);
const browser = await chromium.launch({
  channel: "chrome",
  headless: true,
  chromiumSandbox: true,
});
report.browser = browser.version();
let lastPage;

async function contextFor(viewport, mobile = false) {
  const context = await browser.newContext({
    viewport,
    locale: "ja-JP",
    deviceScaleFactor: 1,
    reducedMotion: "reduce",
    isMobile: mobile,
    hasTouch: mobile,
    serviceWorkers: "block",
  });
  // Fonts/background providers are intentionally blocked; only this application's origin is authorized.
  await context.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (url.origin === target.origin) return route.continue();
    report.blockedExternal.push(url.href);
    return route.abort("blockedbyclient");
  });
  await context.routeWebSocket(/.*/, (socket) => {
    const url = new URL(socket.url());
    if (
      url.protocol === "ws:" &&
      url.hostname === target.hostname &&
      url.port === target.port
    )
      socket.connectToServer();
    else {
      report.blockedExternal.push(url.href);
      socket.close();
    }
  });
  const page = await context.newPage();
  lastPage = page;
  page.setDefaultTimeout(8000);
  page.on("pageerror", (error) =>
    report.runtimeErrors.push({
      message: error.message,
      stack: error.stack,
      after: report.checks.at(-1) ?? "startup",
    }),
  );
  page.on("response", (response) => {
    if (
      new URL(response.url()).origin === target.origin &&
      response.status() >= 400
    )
      report.localHttpErrors.push(`${response.status()} ${response.url()}`);
  });
  page.on("framenavigated", (frame) => {
    if (frame === page.mainFrame() && frame.url() !== "about:blank")
      assert.equal(new URL(frame.url()).origin, target.origin);
  });
  await page.goto(target.href, { waitUntil: "networkidle" });
  await page
    .locator(".map-canvas .leaflet-overlay-pane svg path")
    .first()
    .waitFor();
  await settle(page);
  return { context, page };
}

async function settle(page) {
  await page.locator(".leaflet-zoom-anim").waitFor({ state: "detached" });
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve)),
      ),
  );
}

async function search(page, name, code) {
  await page
    .getByRole("combobox", { name: "都道府県・市区町村を検索" })
    .fill(name);
  await page.getByRole("option").filter({ hasText: code }).click();
  await page
    .locator(".map-selection-info .selected-region-name")
    .first()
    .filter({ hasText: name })
    .waitFor();
  await settle(page);
}

async function screenshot(page, name) {
  await page.mouse.move(0, 0);
  await settle(page);
  await page.screenshot({
    path: fileURLToPath(new URL(name, output)),
    fullPage: true,
    animations: "disabled",
  });
  report.screenshots.push(name);
}

async function assertAligned(page) {
  await page.waitForFunction(() => {
    const maps = [...document.querySelectorAll(".map-canvas")];
    if (maps.length !== 2 || document.querySelector(".leaflet-zoom-anim"))
      return false;
    const anchor = (map) => {
      const label = [...map.querySelectorAll(".city-label")].find(
        (element) => element.textContent === "大阪",
      );
      const a = label.getBoundingClientRect(),
        b = map.getBoundingClientRect();
      return { x: a.left - b.left, y: a.top - b.top };
    };
    const [a, b] = maps.map(anchor);
    return Math.abs(a.x - b.x) <= 2 && Math.abs(a.y - b.y) <= 2;
  });
}

try {
  const desktopSize = { width: 1600, height: 1100 };
  report.viewport.desktop = desktopSize;
  const desktop = await contextFor(desktopSize);
  const page = desktop.page;
  assert.equal(await page.locator(".map-canvas").count(), 1);
  assert.equal(await page.locator(".region-count").textContent(), "1,896地域");
  for (const city of ["札幌", "東京", "大阪", "那覇"]) {
    const inside = await page
      .locator(".map-canvas .city-label")
      .filter({ hasText: new RegExp(`^${city}$`) })
      .evaluate((element) => {
        const box = element.getBoundingClientRect(),
          map = element.closest(".map-canvas").getBoundingClientRect();
        return (
          box.left >= map.left &&
          box.left < map.right &&
          box.top >= map.top &&
          box.top < map.bottom
        );
      });
    assert(inside, `${city} must be inside the nationwide map`);
  }
  const shapes = page.locator(
    ".map-canvas .leaflet-overlay-pane svg path.leaflet-interactive",
  );
  assert.equal(
    await shapes.count(),
    1902,
    "Every geographic feature must have a rendered SVG path",
  );
  const painted = await shapes.evaluateAll(
    (paths) =>
      paths.filter((path) => (path.getAttribute("d") ?? "").length > 10).length,
  );
  assert(
    painted > 1800,
    "Nationwide administrative shapes must have drawn geometry",
  );
  await screenshot(page, "national.png");
  check(
    "Nationwide SVG paths drawn; Sapporo/Tokyo/Osaka/Naha in frame; 1,896 statistical regions",
  );

  for (const [label, title] of [
    ["年少人口比率", "年少人口比率"],
    ["0〜14歳人口", "0〜14歳人口"],
    ["子どもの人口密度", "子どもの人口密度"],
    ["年齢別の人口分布", "0〜4歳人口"],
  ]) {
    await page
      .locator(".mode-options")
      .getByRole("button", { name: label, exact: true })
      .click();
    assert.equal(
      await page.locator(".map-panel-heading h3").textContent(),
      title,
    );
  }
  for (const [age, title] of [
    ["5〜9歳", "5〜9歳人口"],
    ["10〜14歳", "10〜14歳人口"],
  ]) {
    await page.getByRole("button", { name: age, exact: true }).click();
    assert.equal(
      await page.locator(".map-panel-heading h3").textContent(),
      title,
    );
  }
  await page
    .locator(".mode-options")
    .getByRole("button", { name: "人口増減率", exact: true })
    .click();
  assert.equal(await page.locator(".map-year").textContent(), "2015→2020年");
  await page
    .locator(".mode-options")
    .getByRole("button", { name: "合計特殊出生率", exact: true })
    .click();
  assert.equal(await page.locator(".reference-box b").textContent(), "1.33");
  check(
    "All eight indicators switch; published national TFR 1.33 and indicator periods retained",
  );

  await page
    .getByRole("button", { name: "2つの指標を比較", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "比較する2つ目の指標" })
    .selectOption("childShare");
  const panels = await page.locator(".map-panel").all();
  const [leftBox, rightBox] = await Promise.all(
    panels.map((panel) => panel.boundingBox()),
  );
  assert(leftBox.x < rightBox.x && Math.abs(leftBox.y - rightBox.y) < 1);
  assert.equal(await page.locator(".compare-legend[open]").count(), 2);
  assert.deepEqual(await page.locator(".map-year").allTextContents(), [
    "2018–2022年",
    "2020年",
  ]);
  for (const [name, code, rate, share] of [
    ["大阪市", "27100", "1.16", "11.0"],
    ["豊中市", "27203", "1.50", "13.7"],
    ["明石市", "28203", "1.63", "13.8"],
  ]) {
    await search(page, name, code);
    const cards = await page.locator(".map-selection-info").allTextContents();
    assert(cards[0].includes(rate) && cards[0].includes("2018–2022年"));
    assert(cards[1].includes(share) && cards[1].includes("2020年"));
    const selectedPaths = page
      .locator(".map-panel")
      .first()
      .locator('svg path[stroke="#b85f25"]');
    assert.equal(await selectedPaths.count(), code === "27100" ? 24 : 1);
    await assertAligned(page);
  }
  check(
    "Osaka city (24 wards), Toyonaka, Akashi search; both values/periods; side-by-side maps and legends",
  );

  await search(page, "豊中市", "27203");
  await page.locator(".map-canvas").first().hover();
  const hover = page.locator(".data-tooltip:visible").first();
  await hover.waitFor();
  const hoverText = await hover.textContent();
  assert(
    hoverText.includes("豊中市") &&
      hoverText.includes("合計特殊出生率") &&
      hoverText.includes("2018–2022年"),
  );
  await page
    .locator(".map-zoom-controls")
    .first()
    .getByRole("button", { name: "地図を拡大", exact: true })
    .click();
  await settle(page);
  await assertAligned(page);
  const box = await page.locator(".map-canvas").first().boundingBox();
  await page.mouse.move(box.x + box.width * 0.65, box.y + box.height * 0.65);
  await page.mouse.down();
  await page.mouse.move(
    box.x + box.width * 0.65 + 45,
    box.y + box.height * 0.65 + 20,
    { steps: 5 },
  );
  await page.mouse.up();
  await assertAligned(page);
  check(
    "Hover shows region/indicator/period; zoom and drag synchronize both maps",
  );

  await search(page, "葛尾村", "07548");
  assert(
    (
      await page.locator(".map-selection-info strong").first().textContent()
    ).includes("—"),
  );
  assert(
    (await page.locator(".map-selection-info").first().textContent()).includes(
      "非公表",
    ),
  );
  check("Non-published fertility renders as missing, never zero");
  await search(page, "大阪市", "27100");
  await page
    .locator(".map-zoom-controls")
    .first()
    .getByRole("button", { name: "地図を縮小", exact: true })
    .click();
  await settle(page);
  await assertAligned(page);
  // Frame the Osaka–Toyonaka–Akashi corridor using the same wheel/drag controls as a visitor.
  const mapBox = await page.locator(".map-canvas").first().boundingBox();
  const scaleBefore = await page
    .locator(".leaflet-control-scale-line")
    .first()
    .evaluate((element) => element.getBoundingClientRect().width);
  await page.mouse.move(
    mapBox.x + mapBox.width / 2,
    mapBox.y + mapBox.height / 2,
  );
  await page.mouse.wheel(0, -75);
  await page.waitForFunction(
    (before) =>
      Math.abs(
        document
          .querySelector(".leaflet-control-scale-line")
          .getBoundingClientRect().width - before,
      ) > 2,
    scaleBefore,
  );
  await settle(page);
  await page.mouse.move(
    mapBox.x + mapBox.width * 0.4,
    mapBox.y + mapBox.height * 0.5,
  );
  await page.mouse.down();
  await page.mouse.move(
    mapBox.x + mapBox.width * 0.4 + 140,
    mapBox.y + mapBox.height * 0.5,
    { steps: 5 },
  );
  await page.mouse.up();
  await assertAligned(page);
  await screenshot(page, "osaka-comparison.png");

  await page.getByRole("button", { name: "ランキング", exact: true }).click();
  assert.equal(await page.locator("tbody tr").count(), 25);
  await page.getByRole("button", { name: "地図で見る", exact: true }).click();
  await page
    .getByRole("button", { name: "データについて", exact: true })
    .click();
  assert(await page.getByRole("dialog").isVisible());
  assert(
    (await page.getByRole("dialog").textContent()).includes("1,896地域の内訳"),
  );
  await page.getByRole("button", { name: "説明を閉じる", exact: true }).click();
  check("Existing ranking and data/methodology dialog still open");

  const mobileSize = { width: 390, height: 844 };
  report.viewport.mobile = mobileSize;
  const mobile = await contextFor(mobileSize, true);
  const phone = mobile.page;
  await phone.locator(".mobile-filter-button").click();
  await search(phone, "豊中市", "27203");
  await phone
    .getByRole("button", { name: "地域の選択を解除", exact: true })
    .click();
  await phone.locator(".map-canvas").scrollIntoViewIfNeeded();
  const phoneMap = await phone.locator(".map-canvas").boundingBox();
  await phone.touchscreen.tap(
    phoneMap.x + phoneMap.width / 2,
    phoneMap.y + phoneMap.height / 2,
  );
  await phone.locator(".map-selection-info").waitFor();
  const tapped = await phone.locator(".map-selection-info").textContent();
  assert(
    tapped.includes("豊中市") &&
      tapped.includes("合計特殊出生率") &&
      tapped.includes("2018–2022年"),
  );
  await phone
    .getByRole("button", { name: "2つの指標を比較", exact: true })
    .click();
  await phone
    .getByRole("combobox", { name: "比較する2つ目の指標" })
    .selectOption("childShare");
  const [mobileA, mobileB] = await Promise.all(
    (await phone.locator(".map-panel").all()).map((panel) =>
      panel.boundingBox(),
    ),
  );
  assert(mobileA.width >= 340 && mobileB.width >= 340 && mobileB.y > mobileA.y);
  assert.equal(await phone.locator(".compare-legend[open]").count(), 2);
  assert(
    !(await phone.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    )),
    "No horizontal page overflow",
  );
  await assertAligned(phone);
  await screenshot(phone, "mobile.png");
  check(
    "390px touch viewport: settings/search/tap feedback, full-width comparison maps, two legends, no horizontal overflow",
  );

  assert.deepEqual(report.runtimeErrors, []);
  assert.deepEqual(report.localHttpErrors, []);
  report.status = "passed";
  check(
    "No runtime exceptions or local HTTP errors; all external page requests blocked",
  );
} catch (error) {
  report.status = "failed";
  report.failure = error.stack;
  if (lastPage)
    await lastPage
      .screenshot({
        path: fileURLToPath(new URL("failure.png", output)),
        fullPage: true,
      })
      .catch(() => {});
  throw error;
} finally {
  report.finishedAt = new Date().toISOString();
  report.blockedExternal = [...new Set(report.blockedExternal)];
  await writeFile(
    new URL("../qa/browser-results.json", import.meta.url),
    JSON.stringify(report, null, 2),
  );
  await browser.close();
}
