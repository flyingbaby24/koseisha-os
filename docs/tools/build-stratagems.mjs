// Builds docs/research/stratagems/index.html from the Atlas data.
//
//   node docs/tools/build-stratagems.mjs
//
// Sources: stratagems.js (36 records + cognitive tree), stratagems-en.js
// (English records) and i18n.js (UI strings, chapter labels). The page is
// pre-rendered in both languages: every UI string is written as a JA/EN pair
// of spans and CSS shows the pair matching <html lang>, which an inline head
// script sets before first paint. The board, the cognitive categories and a
// compact version of all 36 entries are therefore readable without
// JavaScript; atlas.js then replaces the compact entries with the full reader.
// The output is deterministic, so CI can check it is committed in sync.
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const docs = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dir = path.join(docs, "research/stratagems");
const read = (f) => fs.readFileSync(path.join(dir, f), "utf8");

export function loadAtlasData() {
  const context = vm.createContext({
    window: { location: { href: "https://www.jinn-project.com/research/stratagems/" }, localStorage: null, history: {} },
    navigator: { language: "ja" },
    URL,
  });
  const source = [read("stratagems.js"), read("stratagems-en.js"), read("i18n.js")].join("\n;\n");
  return vm.runInContext(source + "\n;({ stratagems, cognitiveTree, stratagemTranslations, cognitiveTreeTranslations, uiTranslations, chapterLabels, chapterNumerals })", context);
}

const esc = (value) => String(value ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const pad = (n) => String(n).padStart(2, "0");

export function buildPage(data) {
  const { stratagems, cognitiveTree, stratagemTranslations, cognitiveTreeTranslations, uiTranslations, chapterLabels, chapterNumerals } = data;
  const en = stratagemTranslations.en;
  const ui = (lang, key) => uiTranslations[lang][key] ?? uiTranslations.ja[key];
  const pair = (ja, enText, tag = "span", attrs = "") => `<${tag} data-l="ja" lang="ja"${attrs}>${ja}</${tag}><${tag} data-l="en" lang="en"${attrs}>${enText}</${tag}>`;
  const L = (key, tag) => pair(esc(ui("ja", key)), esc(ui("en", key)), tag);
  const LH = (key) => pair(ui("ja", key), ui("en", key));
  // aria-label cannot hold a language pair: write the Japanese default and let atlas.js swap it.
  const A = (key) => `aria-label="${esc(ui("ja", key))}" data-aria="${key}"`;
  const field = (s, name, lang) => (lang === "en" ? en[s.id]?.[name] : undefined) ?? s[name];
  const treeField = (node, name, lang) => (lang === "en" ? cognitiveTreeTranslations.en?.[node.id]?.[name] : undefined) ?? node[name] ?? "";
  const chapterName = (i, lang, form = "name") => chapterLabels[lang][i][form];
  const categoryCount = new Set(stratagems.map((s) => s.category)).size;
  const byId = new Map(stratagems.map((s) => [s.id, s]));

  const cell = (s) => `<li><a class="cell" href="#stratagem-${s.id}" data-id="${s.id}"><span class="cell-no">${pad(s.id)}</span><span class="cell-han" lang="ja">${esc(s.name)}</span>`
    + `<span class="cell-sub">${pair(`${esc(s.reading)} · ${esc(s.english)}`, esc(field(s, "name", "en")))}</span>`
    + `<span class="cell-cat">${s.category === field(s, "category", "en") ? `<span lang="en">${esc(s.category)}</span>` : pair(esc(s.category), esc(field(s, "category", "en")))}</span></a></li>`;

  const chapters = chapterLabels.ja.map((_, i) => {
    const members = stratagems.filter((s) => Math.floor((s.id - 1) / 6) === i);
    return `<div class="chapter" role="group" aria-labelledby="chapter-${i + 1}">`
      + `<h3 class="chapter-head" id="chapter-${i + 1}"><span class="chapter-num" aria-hidden="true">${chapterNumerals[i]}</span>`
      + `<span class="chapter-short" aria-hidden="true">${pair(chapterName(i, "ja"), chapterName(i, "en", "short"))}</span>`
      + `<span class="chapter-name">${pair(`${chapterName(i, "ja", "num")} ${chapterName(i, "ja")}`, `${chapterName(i, "en", "num")} · ${chapterName(i, "en")}`)}</span></h3>`
      + `<ol class="cells">${members.map(cell).join("")}</ol></div>`;
  }).join("\n          ");

  // atlas.js relabels the options from the data when the language changes.
  const option = (value, ja) => `<option value="${esc(value)}">${esc(ja)}</option>`;
  const chapterOptions = [option("all", ui("ja", "allChapters"))]
    .concat(chapterLabels.ja.map((_, i) => option(String(i + 1), `${chapterName(i, "ja", "num")} ${chapterName(i, "ja")}`))).join("");
  const groupOptions = [option("all", ui("ja", "allGroups"))]
    .concat(cognitiveTree.map((g) => option(g.id, treeField(g, "title", "ja")))).join("");
  const categoryOptions = [option("all", ui("ja", "allCategories"))]
    .concat([...new Set(stratagems.map((s) => s.category))].sort().map((c) => option(c, c))).join("");

  const memberLink = (id) => {
    const s = byId.get(id);
    return `<li><a href="#stratagem-${id}"><span class="m-no">${pad(id)}</span><span class="m-han" lang="ja">${esc(s.name)}</span><span class="m-name" data-l="en" lang="en">${esc(field(s, "name", "en"))}</span></a></li>`;
  };
  const groups = cognitiveTree.map((g, i) => `<li class="group" id="group-${g.id}">
          <div class="group-head"><span class="group-no" aria-hidden="true">${pad(i + 1)}</span><h3>${pair(esc(treeField(g, "title", "ja")), esc(treeField(g, "title", "en")))}</h3>
          <p>${pair(esc(treeField(g, "description", "ja")), esc(treeField(g, "description", "en")))}</p>
          <button type="button" class="link-button js-only" data-show-group="${g.id}">${L("showOnAtlas")}</button></div>
          <ul class="subgroups">${g.children.map((c) => `<li><h4>${pair(esc(treeField(c, "title", "ja")), esc(treeField(c, "title", "en")))}</h4><ul class="members">${c.stratagemIds.map(memberLink).join("")}</ul></li>`).join("")}</ul>
        </li>`).join("\n        ");

  // Without scripts the inline head script never runs, so <html lang> stays "ja" and only
  // Japanese is shown: the compact entries are written in Japanese alone.
  const staticEntry = (s) => {
    const i = Math.floor((s.id - 1) / 6);
    return `<article class="entry-static" id="stratagem-${s.id}" aria-labelledby="static-title-${s.id}">
          <p class="es-meta">${chapterName(i, "ja", "num")} ${chapterName(i, "ja")} · ${s.id} / 36</p>
          <h3 id="static-title-${s.id}"><span class="es-no">${pad(s.id)}</span> <span class="es-han">${esc(s.name)}</span> <span class="es-name">${esc(s.reading)} · <span lang="en">${esc(s.english)}</span></span></h3>
          <p>${esc(s.summary)}</p>
          <p><a href="${esc(s.noteUrl)}" target="_blank" rel="noopener noreferrer">${esc(ui("ja", "readOnNote"))} ↗<span class="sr-only">${esc(ui("ja", "opensNewTab"))}</span></a></p>
        </article>`;
  };

  // The 150 KB of data and app code is requested once the first paint is on screen (or at
  // the load event where paint timing is unavailable), so it does not compete with the
  // stylesheet and fonts for the first render. Execution order is kept (async=false).
  const scriptLoader = "(function(){var done=false;function go(){if(done)return;done=true;['stratagems.js','stratagems-en.js','i18n.js','atlas.js'].forEach(function(src){var s=document.createElement('script');s.src=src;s.async=false;document.body.appendChild(s)})}try{new PerformanceObserver(function(list,o){if(list.getEntries().some(function(e){return e.name==='first-contentful-paint'})){o.disconnect();setTimeout(go,0)}}).observe({type:'paint',buffered:true})}catch(e){}addEventListener('load',function(){setTimeout(go,0)})})()";
  // Sets <html lang> before first paint, then preloads only the display faces the first screen
  // uses in that language and width (avoids a font swap shifting the page).
  const headScript = "(function(d){var l='ja';try{var p=new URLSearchParams(location.search).get('lang'),s=null;try{s=localStorage.getItem('stratagems-language')}catch(e){}var n=String(navigator.language||'').toLowerCase();l=p==='ja'||p==='en'?p:s==='ja'||s==='en'?s:n?(n.indexOf('ja')===0?'ja':'en'):'ja'}catch(e){}d.lang=l;d.className='js';var w=matchMedia('(min-width: 700px)').matches,f=l==='ja'?['fonts/atlas-han-600.woff2']:['../../assets/fonts/instrument-serif-latin.woff2'].concat(w?['fonts/atlas-han-600.woff2']:[]);f.forEach(function(h){var k=document.createElement('link');k.rel='preload';k.as='font';k.type='font/woff2';k.crossOrigin='anonymous';k.href=h;document.head.appendChild(k)})})(document.documentElement)";

  return `<!doctype html>
<html lang="ja" class="no-js">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>36 Stratagems Cognitive Bias Atlas | Jinn Project</title>
  <meta name="description" content="A cognitive bias reinterpretation of the Thirty-Six Stratagems through behavioral economics and modern decision theory.">
  <meta name="theme-color" content="#f3eee4">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Jinn Project">
  <meta property="og:title" content="36 Stratagems Cognitive Bias Atlas">
  <meta property="og:description" content="A cognitive bias reinterpretation of the Thirty-Six Stratagems through behavioral economics and modern decision theory.">
  <meta property="og:url" content="https://www.jinn-project.com/research/stratagems/">
  <link rel="icon" href="../../favicon.ico" sizes="any">
  <link rel="icon" href="../../assets/img/icon-32.png" type="image/png">
  <link rel="apple-touch-icon" href="../../assets/img/apple-touch-icon.png">
  <script>${headScript}</script>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <a class="skip-link" href="#atlas">${L("skipToAtlas")}</a>
  <header class="masthead">
    <a class="brand" href="../../" data-home-en="../../" data-home-ja="../../index-ja.html"><img src="../../assets/img/jinn-mark-96.webp" width="32" height="32" alt=""><span>Jinn Project</span><span class="sr-only"> — ${L("siteHome")}</span></a>
    <span class="masthead-title" aria-hidden="true">${L("pageName")}</span>
    <nav class="masthead-nav" ${A("pageName")}>
      <a href="#atlas">${L("navAtlas")}</a><a href="#categories">${L("navCategories")}</a><a href="#concept">${L("navConcept")}</a><a href="#notes">${L("navNotes")}</a>
    </nav>
    <div class="language-switcher" role="group" aria-label="Language / 言語">
      <button id="languageJa" class="language-button" type="button" data-language="ja" lang="ja" aria-pressed="false">日本語</button>
      <button id="languageEn" class="language-button" type="button" data-language="en" lang="en" aria-pressed="false">EN</button>
    </div>
  </header>
  <main id="main">
    <section class="hero" aria-labelledby="hero-title">
      <div class="hero-text">
        <p class="kicker">${L("heroEyebrow")}</p>
        <h1 id="hero-title">${LH("heroTitle")}</h1>
        <p class="lead">${L("heroLead")}</p>
        <p class="hero-actions"><a class="button button-ink" href="#atlas">${L("openAtlas")}</a><a class="button" href="#categories">${L("viewCategories")}</a></p>
      </div>
      <div class="hero-slip" aria-hidden="true"><span class="hero-han">三十六計</span><span class="hero-seal">計</span></div>
      <ul class="hero-facts">
        <li><strong>${stratagems.length}</strong>${L("stratagems")}</li>
        <li><strong>${categoryCount}</strong>${L("categories")}</li>
        <li><strong>1</strong>${L("humanFirmware")}</li>
      </ul>
    </section>

    <section id="atlas" class="atlas" aria-labelledby="atlas-title" tabindex="-1">
      <div class="section-head">
        <p class="kicker">${L("atlasEyebrow")}</p>
        <h2 id="atlas-title">${L("atlasTitle")}</h2>
      </div>
      <div class="atlas-layout">
        <div class="atlas-panel">
          <form class="tools js-only" role="search" ${A("filters")} id="tools">
            <div class="field field-search"><label for="search">${L("searchLabel")}</label><input id="search" type="search" autocomplete="off" spellcheck="false" enterkeyhint="search"></div>
            <details class="filters" id="filters" open>
              <summary>${L("filters")}<span class="filter-badge" id="filterBadge" hidden></span></summary>
              <div class="filter-fields">
                <div class="field"><label for="chapter">${L("chapterFilter")}</label><select id="chapter">${chapterOptions}</select></div>
                <div class="field"><label for="group">${L("groupFilter")}</label><select id="group">${groupOptions}</select></div>
                <div class="field"><label for="category">${L("categories")}</label><select id="category">${categoryOptions}</select></div>
                <button type="button" class="link-button" id="clearFilters" hidden>${L("clearFilters")}</button>
              </div>
            </details>
          </form>
          <div class="board-bar js-only">
            <p class="result-count" id="resultCount" role="status"></p>
            <div class="view-switch" role="group" ${A("viewLabel")}>
              <button type="button" data-view="board" aria-pressed="true">${L("viewBoard")}</button><button type="button" data-view="list" aria-pressed="false">${L("viewList")}</button>
            </div>
          </div>
          <div class="board" id="board" data-view="board" role="group" aria-labelledby="board-label" aria-describedby="board-hint">
            <p class="sr-only" id="board-label">${L("boardLabel")}</p>
            <p class="sr-only js-only" id="board-hint">${L("boardHint")}</p>
            <svg class="board-lines" id="boardLines" aria-hidden="true" focusable="false"></svg>
          ${chapters}
          </div>
          <p class="board-caption js-only" id="boardCaption" aria-hidden="true"></p>
          <p class="board-legend js-only"><span class="legend-line" aria-hidden="true"></span><span class="legend-line legend-dotted" aria-hidden="true"></span>${L("boardLegend")}</p>
        </div>
        <div class="reader" id="reader">
          <noscript><div class="entries-static">
            <p class="static-note">${esc(ui("ja", "staticNote"))}</p>
        ${stratagems.map(staticEntry).join("\n        ")}
          </div></noscript>
        </div>
      </div>
    </section>

    <section id="categories" class="section categories" aria-labelledby="categories-title">
      <div class="section-head">
        <p class="kicker">${L("categories")}</p>
        <h2 id="categories-title">${L("categoriesTitle")}</h2>
      </div>
      <ol class="groups">
        ${groups}
      </ol>
    </section>

    <section id="concept" class="section essay" aria-labelledby="concept-title">
      <p class="kicker">${L("conceptEyebrow")}</p>
      <h2 id="concept-title">${L("conceptTitle")}</h2>
      <p>${L("conceptBody")}</p>
    </section>

    <section id="notes" class="section essay essay-note" aria-labelledby="notes-title">
      <p class="kicker">${L("notesEyebrow")}</p>
      <h2 id="notes-title">${L("notesTitle")}</h2>
      <p>${L("notesBody")}</p>
    </section>
  </main>
  <nav class="pager-bar js-only" id="pagerBar" ${A("positionLabel")} hidden>
    <button type="button" class="pager-step" data-step="-1"><span aria-hidden="true">‹</span><span class="sr-only">${L("previous")}</span></button>
    <button type="button" class="pager-index" id="pagerIndex"><span class="pager-pos" id="pagerPos"></span><span class="pager-name" id="pagerName" lang="ja"></span><span class="sr-only">${L("backToAtlas")}</span></button>
    <button type="button" class="pager-step" data-step="1"><span aria-hidden="true">›</span><span class="sr-only">${L("next")}</span></button>
  </nav>
  <footer class="footer">
    <span>© Jinn Project</span>
    <span>Visualizing hidden structures in thought and behavior.</span>
    <a href="../../" data-home-en="../../" data-home-ja="../../index-ja.html">${L("siteHome")}</a>
  </footer>
  <p class="sr-only" id="announcer" role="status" aria-live="polite"></p>
  <script>${scriptLoader}</script>

  <!-- Cloudflare Web Analytics -->
<script defer
src="https://static.cloudflareinsights.com/beacon.min.js"
data-cf-beacon='{"token":"7da53f8ef3544cf0967279ebd140ff89"}'>
</script>
<!-- End Cloudflare Web Analytics -->
</body>
</html>
`;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const out = path.join(dir, "index.html");
  fs.writeFileSync(out, buildPage(loadAtlasData()));
  console.log("Generated " + path.relative(path.dirname(docs), out));
}
