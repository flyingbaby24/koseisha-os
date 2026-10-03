// Stratagems Atlas — progressive enhancement for the pre-rendered page.
//
// Globals from the deferred scripts loaded before this one:
//   stratagems.js     stratagems, cognitiveTree
//   stratagems-en.js  stratagemTranslations, cognitiveTreeTranslations
//   i18n.js           uiTranslations, chapterLabels, chapterNumerals, chapterIndexOf,
//                     currentLanguage, t, getLocalizedField, getLocalizedTreeField,
//                     safeStorageSet, updateLanguageUrl
//
// The board, filters and categories are already in the HTML (docs/tools/build-stratagems.mjs).
// This script adds selection, the reader (all 36 entries, one visible), deep links
// (#stratagem-N), filtering, language switching and motion.
(() => {
  "use strict";

  const root = document.documentElement;
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const wide = matchMedia("(min-width: 1100px)");
  const narrow = matchMedia("(max-width: 699px)");

  const board = $("#board");
  const reader = $("#reader");
  const lines = $("#boardLines");
  const caption = $("#boardCaption");
  const search = $("#search");
  const chapterSelect = $("#chapter");
  const groupSelect = $("#group");
  const categorySelect = $("#category");
  const filtersBox = $("#filters");
  const filterBadge = $("#filterBadge");
  const clearButton = $("#clearFilters");
  const resultCount = $("#resultCount");
  const pagerBar = $("#pagerBar");
  const pagerPos = $("#pagerPos");
  const pagerName = $("#pagerName");
  const announcer = $("#announcer");
  const languageButtons = $$("[data-language]");
  const viewButtons = $$("[data-view]", $(".view-switch"));
  if (!board || !reader || typeof stratagems === "undefined") return;

  const ids = stratagems.map((s) => s.id);
  const byId = new Map(stratagems.map((s) => [s.id, s]));
  const cells = $$(".cell", board);
  const cellById = new Map(cells.map((cell) => [Number(cell.dataset.id), cell]));
  const categories = [...new Set(stratagems.map((s) => s.category))].sort();

  // Relations derived from the data: outgoing (listed by this stratagem), incoming
  // (stratagems that list this one) and placements in the cognitive tree.
  const outgoing = new Map(stratagems.map((s) => [s.id, (s.relatedStratagems || []).filter((id) => byId.has(id) && id !== s.id)]));
  const incoming = new Map(ids.map((id) => [id, []]));
  outgoing.forEach((targets, from) => targets.forEach((to) => incoming.get(to).push(from)));
  const placements = new Map(ids.map((id) => [id, []]));
  cognitiveTree.forEach((group) => group.children.forEach((child) => child.stratagemIds.forEach((id) => placements.get(id)?.push({ group, child }))));
  const groupMembers = new Map(cognitiveTree.map((group) => [group.id, new Set(group.children.flatMap((child) => child.stratagemIds))]));

  const state = { selected: ids[0], view: "board", matches: new Set(ids), filtering: false, readerInView: false };

  const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const pad = (n) => String(n).padStart(2, "0");
  const field = (s, name) => getLocalizedField(s, name);
  const isJa = () => currentLanguage === "ja";
  const secondary = (s) => (isJa() ? s.reading : field(s, "name"));
  const chapterOf = (id) => chapterLabels[currentLanguage][chapterIndexOf(id)];
  const chapterText = (id) => (isJa() ? `${chapterOf(id).num} ${chapterOf(id).name}` : `${chapterOf(id).num} · ${chapterOf(id).name}`);
  const format = (key, n) => t(key).replace("{n}", n);
  const paragraphs = (text) => String(text ?? "").trim().split(/\n\s*\n/).filter(Boolean)
    .map((p) => `<p>${esc(p.trim()).replace(/\n/g, "<br>")}</p>`).join("");
  const list = (items, className) => (items.length ? `<ul class="${className}">${items.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : "");
  const motionOk = () => !reduceMotion.matches;
  const idle = window.requestIdleCallback || ((fn) => setTimeout(() => fn({ timeRemaining: () => 8 }), 32));

  function validateLongFormContent() {
    const problems = [];
    stratagems.forEach((s) => {
      ["interpretation", "principle", "noteTitle"].forEach((name) => {
        if (!String(s[name] ?? "").trim()) problems.push(`ja #${s.id} ${name}`);
        if (!String(stratagemTranslations.en?.[s.id]?.[name] ?? "").trim()) problems.push(`en #${s.id} ${name}`);
      });
    });
    if (stratagems.length !== 36) problems.push(`expected 36 records, found ${stratagems.length}`);
    if (problems.length) console.error("Stratagem long-form content validation failed:", problems);
  }

  // ---------- Entries ----------
  function rail(id) {
    const chapter = chapterIndexOf(id);
    return `<ol class="rail" aria-hidden="true">${chapterLabels.ja.map((_, g) => `<li${g === chapter ? ' class="is-chapter"' : ""}>${[1, 2, 3, 4, 5, 6].map((k) => `<i${g * 6 + k === id ? ' class="is-current"' : ""}></i>`).join("")}</li>`).join("")}</ol>`;
  }

  function relatedCard(id) {
    const s = byId.get(id);
    return `<li><a href="#stratagem-${id}" data-goto="${id}"><span class="rel-no">${pad(id)}</span><span class="rel-han" lang="ja">${esc(s.name)}</span><span class="rel-name">${esc(isJa() ? s.summary : field(s, "name"))}</span></a></li>`;
  }

  function renderEntry(s) {
    const id = s.id;
    const summary = field(s, "summary");
    const interpretation = field(s, "interpretation");
    const out = outgoing.get(id);
    const inc = incoming.get(id);
    const parts = [
      `<header class="entry-head">`,
      rail(id),
      `<p class="entry-meta"><span class="entry-chapter">${esc(chapterText(id))}</span><span class="entry-pos">${pad(id)} / 36</span><button type="button" class="link-button copy-link" data-copy="${id}">${esc(t("copyLink"))}</button></p>`,
      `<h3 class="entry-title" id="entry-title-${id}" tabindex="-1"><span class="entry-no" aria-hidden="true">${pad(id)}</span><span class="entry-han" lang="ja">${esc(s.name)}</span><span class="entry-name" lang="en">${esc(isJa() ? s.english : field(s, "name"))}</span></h3>`,
      isJa() ? `<p class="entry-reading" lang="ja">${esc(s.reading)}</p>` : "",
      `<p><span class="tag" lang="en">${esc(field(s, "category"))}</span></p>`,
      `</header>`,
      `<p class="entry-summary">${esc(summary)}</p>`,
      `<section class="entry-sec"><h4>${esc(t("principle"))}</h4><blockquote class="principle">${paragraphs(field(s, "principle"))}</blockquote></section>`,
      // The English records reuse the summary as the interpretation; show that text once.
      String(interpretation).trim() && String(interpretation).trim() !== String(summary).trim()
        ? `<section class="entry-sec"><h4>${esc(t("interpretation"))}</h4><div class="prose">${paragraphs(interpretation)}</div></section>` : "",
      `<section class="entry-sec"><h4>${esc(t("cognitiveReading"))}</h4>`,
      `<ol class="chain"><li><span class="chain-label">${esc(chapterOf(id).num)} · ${pad(id)}</span><span class="chain-han" lang="ja">${esc(s.name)}</span></li>`,
      `<li><span class="chain-label">${esc(t("bias"))}</span><span class="chain-value">${esc(field(s, "bias"))}</span></li>`,
      `<li><span class="chain-label">${esc(t("behavioral"))}</span><span class="chain-value">${esc(field(s, "behavioral"))}</span></li></ol>`,
      (field(s, "relatedBiases") || []).length ? `<div class="subhead"><h5>${esc(t("relatedBiases"))}</h5>${list(field(s, "relatedBiases"), "chips chips-ai")}</div>` : "",
      (field(s, "breakdown") || []).length ? `<div class="subhead"><h5>${esc(t("breakdown"))}</h5><ol class="steps">${field(s, "breakdown").map((x) => `<li>${esc(x)}</li>`).join("")}</ol></div>` : "",
      (field(s, "relatedConcepts") || []).length ? `<div class="subhead"><h5>${esc(t("relatedConcepts"))}</h5>${list(field(s, "relatedConcepts"), "chips")}</div>` : "",
      placements.get(id).length ? `<div class="subhead"><h5>${esc(t("cognitiveCategories"))}</h5><ul class="placements">${placements.get(id).map(({ group, child }) => `<li><a href="#group-${group.id}">${esc(getLocalizedTreeField(group, "title"))}</a> › ${esc(getLocalizedTreeField(child, "title"))}</li>`).join("")}</ul></div>` : "",
      `</section>`,
      `<section class="entry-sec"><h4>${esc(t("example"))}</h4><p class="example">${esc(field(s, "example"))}</p></section>`,
      s.noteUrl || (field(s, "references") || []).length ? `<section class="entry-sec"><h4>${esc(t("note"))}</h4>` : "",
      s.noteUrl ? `<a class="note-card" href="${esc(s.noteUrl)}" target="_blank" rel="noopener noreferrer"><span class="note-title">${esc(field(s, "noteTitle"))}</span><span class="note-cta">${esc(t("readOnNote"))} ↗</span><span class="sr-only">${esc(t("opensNewTab"))}</span></a>` : "",
      (field(s, "references") || []).length ? `<div class="subhead"><h5>${esc(t("references"))}</h5><ol class="refs">${field(s, "references").map((x) => `<li>${esc(x)}</li>`).join("")}</ol></div>` : "",
      s.noteUrl || (field(s, "references") || []).length ? `</section>` : "",
      out.length || inc.length ? `<section class="entry-sec"><h4>${esc(t("relatedStratagems"))}</h4>` : "",
      out.length ? `<ul class="rel-grid">${out.map(relatedCard).join("")}</ul>` : "",
      inc.length ? `<div class="subhead"><h5>${esc(t("referencedBy"))}</h5><ul class="rel-grid rel-in">${inc.map(relatedCard).join("")}</ul></div>` : "",
      out.length || inc.length ? `</section>` : "",
      `<div class="pager-slot"></div>`,
    ];
    return parts.join("");
  }

  const entries = document.createElement("div");
  entries.className = "entries";
  entries.id = "entries";
  entries.innerHTML = ids.map((id) => `<article class="entry" id="stratagem-${id}" data-id="${id}" aria-labelledby="entry-title-${id}" hidden="until-found"></article>`).join("");
  reader.append(entries);
  const articleById = new Map($$(".entry", entries).map((el) => [Number(el.dataset.id), el]));

  function ensureRendered(id) {
    const article = articleById.get(id);
    if (article.dataset.lang === currentLanguage) return article;
    article.innerHTML = renderEntry(byId.get(id));
    article.dataset.lang = currentLanguage;
    if (id === state.selected) renderPager(article);
    return article;
  }

  // The other 35 entries are rendered once the reader starts interacting (Ctrl/Cmd+F is a
  // keydown too), so find-in-page can reach them without weighing down the first load.
  let restToken = 0;
  let restWanted = false;
  function renderRestSoon() {
    if (restWanted) return;
    restWanted = true;
    renderRestWhenIdle();
  }
  function renderRestWhenIdle() {
    const token = ++restToken;
    const queue = ids.filter((id) => id !== state.selected);
    const step = (deadline) => {
      if (token !== restToken) return;
      while (queue.length && deadline.timeRemaining() > 4) ensureRendered(queue.shift());
      if (queue.length) idle(step);
    };
    idle(step);
  }

  // ---------- Sequence & pager ----------
  function sequence() {
    if (state.filtering && state.matches.size && state.matches.has(state.selected)) return ids.filter((id) => state.matches.has(id));
    return ids;
  }
  function neighbours(id) {
    const seq = sequence();
    const i = seq.indexOf(id);
    return { prev: seq[(i - 1 + seq.length) % seq.length], next: seq[(i + 1) % seq.length], index: i + 1, total: seq.length };
  }
  function renderPager(article) {
    const id = Number(article.dataset.id);
    const { prev, next } = neighbours(id);
    const link = (target, rel, label) => {
      const s = byId.get(target);
      return `<a href="#stratagem-${target}" rel="${rel}" data-goto="${target}"><span class="pg-label">${rel === "prev" ? "← " : ""}${esc(t(label))}${rel === "next" ? " →" : ""}</span><span class="pg-han" lang="ja">${esc(s.name)}</span><span class="pg-name">${pad(target)} · ${esc(secondary(s))}</span></a>`;
    };
    const slot = $(".pager-slot", article);
    if (slot) slot.innerHTML = `<nav class="entry-pager" aria-label="${esc(`${t("previous")} / ${t("next")}`)}">${link(prev, "prev", "previous")}${link(next, "next", "next")}</nav>`;
  }

  // ---------- Board ----------
  function setRoving(id) {
    cells.forEach((cell) => { cell.tabIndex = Number(cell.dataset.id) === id ? 0 : -1; });
  }

  function setCaption(id) {
    const s = byId.get(id);
    caption.innerHTML = `${pad(id)} <span lang="ja">${esc(s.name)}</span> — ${esc(isJa() ? `${s.reading} · ${s.english}` : field(s, "name"))}`;
  }

  function anchor(id, box) {
    const r = cellById.get(id).getBoundingClientRect();
    const inset = narrow.matches ? [7, 9] : [12.5, 12.5];
    return [r.right - box.left - inset[0], r.top - box.top + inset[1]];
  }

  function drawLines(animate) {
    if (state.view !== "board" || !board.offsetWidth) { lines.replaceChildren(); return; }
    const box = board.getBoundingClientRect();
    lines.setAttribute("viewBox", `0 0 ${box.width} ${box.height}`);
    const [x1, y1] = anchor(state.selected, box);
    const curve = (id) => {
      const [x2, y2] = anchor(id, box);
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2, dx = x2 - x1, dy = y2 - y1;
      const bow = 0.16;
      return `M${x1.toFixed(1)} ${y1.toFixed(1)} Q${(mx - dy * bow).toFixed(1)} ${(my + dx * bow).toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}`;
    };
    const out = outgoing.get(state.selected);
    const inc = incoming.get(state.selected).filter((id) => !out.includes(id));
    lines.innerHTML = out.map((id, i) => `<path class="out" pathLength="1" style="--d:${i * 70}ms" d="${curve(id)}"/>`).join("")
      + inc.map((id, i) => `<path class="in" style="--d:${(out.length + i) * 70}ms" d="${curve(id)}"/>`).join("")
      + `<circle cx="${x1.toFixed(1)}" cy="${y1.toFixed(1)}" r="4"/>`;
    lines.classList.remove("is-drawing");
    if (animate && motionOk()) { void lines.getBoundingClientRect(); lines.classList.add("is-drawing"); }
  }

  function markBoard() {
    const out = new Set(outgoing.get(state.selected));
    const inc = new Set(incoming.get(state.selected));
    cells.forEach((cell) => {
      const id = Number(cell.dataset.id);
      if (id === state.selected) cell.setAttribute("aria-current", "true"); else cell.removeAttribute("aria-current");
      cell.classList.toggle("is-related", out.has(id));
      cell.classList.toggle("is-referrer", inc.has(id));
    });
  }

  // ---------- Selection ----------
  function urlFor(id) {
    const url = new URL(window.location.href);
    url.hash = `stratagem-${id}`;
    return url;
  }

  function scrollToEntry(article, smooth) {
    const top = article.getBoundingClientRect().top;
    const header = narrow.matches ? 12 : $(".masthead").offsetHeight + 16;
    if (wide.matches && top >= header - 2 && top < window.innerHeight * 0.6) return;
    window.scrollTo({ top: window.scrollY + top - header, behavior: smooth && motionOk() ? "smooth" : "auto" });
  }

  function select(id, { scroll = false, focus = false, animate = true, updateHash = true, lines: withLines = true } = {}) {
    id = Number(id);
    if (!byId.has(id)) return;
    const changed = id !== state.selected;
    state.selected = id;
    const article = ensureRendered(id);
    articleById.forEach((el, key) => { if (key === id) el.removeAttribute("hidden"); else if (!el.hasAttribute("hidden")) el.setAttribute("hidden", "until-found"); });
    renderPager(article);
    if (animate && changed && motionOk()) {
      article.classList.remove("is-entering");
      void article.offsetWidth;
      article.classList.add("is-entering");
      clearTimeout(article.enteringTimer);
      article.enteringTimer = setTimeout(() => article.classList.remove("is-entering"), 1100);
    }
    markBoard();
    setRoving(id);
    setCaption(id);
    if (withLines) drawLines(animate && changed);
    updatePagerBar();
    if (updateHash) history.replaceState(history.state, "", urlFor(id));
    document.title = `${pad(id)} ${byId.get(id).name} — ${t("pageName")} | Jinn Project`;
    if (scroll) scrollToEntry(article, true);
    if (focus) $(".entry-title", article)?.focus({ preventScroll: true });
  }

  // ---------- Filters ----------
  function toSearchText(value) {
    if (Array.isArray(value)) return value.map(toSearchText).join(" ");
    if (value && typeof value === "object") return Object.values(value).map(toSearchText).join(" ");
    return String(value ?? "");
  }
  // Same fields and rules as the previous Atlas search.
  function matchesQuery(s, query) {
    if (!query) return true;
    const fields = ["name", "category", "summary", "bias", "behavioral", "example", "relatedConcepts", "relatedBiases"];
    if (currentLanguage === "ja") fields.push("reading", "english");
    const localized = fields.map((name) => getLocalizedField(s, name));
    const supplementalJapanese = currentLanguage === "en" ? fields.map((name) => s[name]) : [];
    return toSearchText([...localized, ...supplementalJapanese]).toLowerCase().includes(query);
  }

  let autoSelectTimer = 0;
  function applyFilters({ autoSelect = true } = {}) {
    const query = search.value.toLowerCase().trim();
    const chapter = chapterSelect.value, group = groupSelect.value, category = categorySelect.value;
    state.matches = new Set(stratagems.filter((s) => (chapter === "all" || chapterIndexOf(s.id) === Number(chapter) - 1)
      && (group === "all" || groupMembers.get(group)?.has(s.id))
      && (category === "all" || s.category === category)
      && matchesQuery(s, query)).map((s) => s.id));
    const facets = [chapter, group, category].filter((v) => v !== "all").length;
    state.filtering = Boolean(query) || facets > 0;
    board.toggleAttribute("data-filtering", state.filtering);
    cells.forEach((cell) => cell.classList.toggle("is-match", state.matches.has(Number(cell.dataset.id))));
    filterBadge.hidden = facets === 0;
    filterBadge.textContent = String(facets);
    clearButton.hidden = !state.filtering;
    resultCount.textContent = state.filtering && state.matches.size === 0
      ? `${t("noResultsTitle")} — ${t("noResultsDescription")}`
      : format("resultCount", state.filtering ? state.matches.size : 36);
    clearTimeout(autoSelectTimer);
    if (autoSelect && state.filtering && state.matches.size && !state.matches.has(state.selected)) {
      // Like the previous Atlas, open the first match; wait for typing to settle.
      autoSelectTimer = setTimeout(() => select(ids.find((id) => state.matches.has(id))), 160);
    } else {
      renderPager(articleById.get(state.selected));
      updatePagerBar();
    }
  }

  function clearFilters() {
    search.value = "";
    chapterSelect.value = groupSelect.value = categorySelect.value = "all";
    applyFilters({ autoSelect: false });
  }

  // ---------- Language ----------
  function relabel() {
    const options = (el, labels) => [...el.options].forEach((option) => { option.textContent = labels(option.value); });
    options(chapterSelect, (v) => (v === "all" ? t("allChapters") : chapterText((Number(v) - 1) * 6 + 1)));
    options(groupSelect, (v) => (v === "all" ? t("allGroups") : getLocalizedTreeField(cognitiveTree.find((g) => g.id === v), "title")));
    options(categorySelect, (v) => (v === "all" ? t("allCategories") : field(stratagems.find((s) => s.category === v), "category")));
    $$("[data-aria]").forEach((el) => el.setAttribute("aria-label", t(el.dataset.aria)));
    $$("[data-home-ja]").forEach((a) => { a.href = isJa() ? a.dataset.homeJa : a.dataset.homeEn; });
    languageButtons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.language === currentLanguage)));
  }

  function setLanguage(language) {
    if (!["ja", "en"].includes(language) || language === currentLanguage) return;
    currentLanguage = language;
    root.lang = language;
    safeStorageSet("stratagems-language", language);
    updateLanguageUrl(language);
    relabel();
    select(state.selected, { animate: false, updateHash: false });
    applyFilters({ autoSelect: false });
    if (restWanted) renderRestWhenIdle();
  }

  // ---------- Touch stepper ----------
  function updatePagerBar() {
    const show = !wide.matches && state.readerInView;
    pagerBar.hidden = !show;
    const { index, total } = neighbours(state.selected);
    pagerPos.textContent = total === 36 ? `${pad(state.selected)} / 36` : `${index} / ${total}`;
    pagerName.textContent = byId.get(state.selected).name;
  }

  function announce(message) {
    announcer.textContent = "";
    setTimeout(() => { announcer.textContent = message; }, 40);
  }

  // ---------- View ----------
  function setView(view) {
    if (view === state.view) return;
    const before = motionOk() ? new Map(cells.map((cell) => [cell, cell.getBoundingClientRect()])) : null;
    state.view = view;
    board.dataset.view = view;
    viewButtons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.view === view)));
    if (before) {
      cells.forEach((cell) => {
        const a = before.get(cell), b = cell.getBoundingClientRect();
        if (!b.width || !a.width) return;
        const dx = a.left - b.left, dy = a.top - b.top;
        if (Math.abs(dx) + Math.abs(dy) > 1) cell.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }], { duration: 420, easing: "cubic-bezier(0.2, 0.65, 0.2, 1)" });
      });
    }
    drawLines(false);
  }

  // ---------- Events ----------
  board.addEventListener("click", (event) => {
    const cell = event.target.closest(".cell");
    if (!cell || event.metaKey || event.ctrlKey || event.shiftKey || event.button) return;
    event.preventDefault();
    select(cell.dataset.id, { scroll: true, focus: true });
  });

  board.addEventListener("keydown", (event) => {
    const cell = event.target.closest(".cell");
    if (!cell) return;
    const id = Number(cell.dataset.id);
    const listView = state.view === "list";
    const visible = listView && state.filtering ? ids.filter((x) => state.matches.has(x)) : ids;
    const i = visible.indexOf(id);
    const moves = {
      ArrowDown: listView ? visible[i + 1] : id % 6 ? id + 1 : null,
      ArrowUp: listView ? visible[i - 1] : (id - 1) % 6 ? id - 1 : null,
      ArrowRight: listView ? null : id + 6 <= 36 ? id + 6 : null,
      ArrowLeft: listView ? null : id - 6 >= 1 ? id - 6 : null,
      Home: visible[0],
      End: visible[visible.length - 1],
    };
    if (!(event.key in moves)) return;
    event.preventDefault();
    const next = moves[event.key];
    if (next) {
      setRoving(next);
      cellById.get(next).focus();
    }
  });

  board.addEventListener("pointerover", (event) => { const cell = event.target.closest(".cell"); if (cell) setCaption(Number(cell.dataset.id)); });
  board.addEventListener("pointerleave", () => setCaption(state.selected));
  board.addEventListener("focusin", (event) => { const cell = event.target.closest(".cell"); if (cell) setCaption(Number(cell.dataset.id)); });
  board.addEventListener("focusout", (event) => { if (!board.contains(event.relatedTarget)) setRoving(state.selected); });

  // Every in-page link to an entry — related cards, pager, category members — selects it.
  document.addEventListener("click", (event) => {
    const link = event.target.closest('a[href^="#stratagem-"]');
    if (!link || board.contains(link) || event.metaKey || event.ctrlKey || event.shiftKey || event.button) return;
    event.preventDefault();
    select(link.getAttribute("href").slice(11), { scroll: true, focus: true });
  });

  reader.addEventListener("click", async (event) => {
    const button = event.target.closest(".copy-link");
    if (!button) return;
    const url = urlFor(Number(button.dataset.copy)).href;
    try {
      await navigator.clipboard.writeText(url);
      button.textContent = t("linkCopied");
      announce(t("linkCopied"));
      setTimeout(() => { button.textContent = t("copyLink"); }, 2000);
    } catch (_) {
      announce(url);
    }
  });

  entries.addEventListener("beforematch", (event) => {
    const article = event.target.closest(".entry");
    if (article) select(article.dataset.id, { animate: false });
  });

  window.addEventListener("hashchange", () => {
    const id = parseHash();
    if (id && id !== state.selected) select(id, { scroll: true, updateHash: false });
  });

  search.addEventListener("input", () => applyFilters());
  [chapterSelect, groupSelect, categorySelect].forEach((el) => el.addEventListener("change", () => applyFilters()));
  $("#tools").addEventListener("submit", (event) => event.preventDefault());
  clearButton.addEventListener("click", () => { clearFilters(); search.focus(); });
  viewButtons.forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
  languageButtons.forEach((button) => button.addEventListener("click", () => setLanguage(button.dataset.language)));

  $$("[data-show-group]").forEach((button) => button.addEventListener("click", () => {
    groupSelect.value = button.dataset.showGroup;
    chapterSelect.value = categorySelect.value = "all";
    search.value = "";
    filtersBox.open = true;
    applyFilters();
    $("#atlas").scrollIntoView({ behavior: motionOk() ? "smooth" : "auto" });
    cellById.get(ids.find((id) => state.matches.has(id)) ?? state.selected).focus({ preventScroll: true });
  }));

  pagerBar.addEventListener("click", (event) => {
    const step = event.target.closest("[data-step]");
    if (step) {
      const { prev, next } = neighbours(state.selected);
      const target = Number(step.dataset.step) < 0 ? prev : next;
      select(target, { scroll: true });
      announce(`${pad(target)} ${byId.get(target).name} — ${secondary(byId.get(target))}`);
      return;
    }
    if (event.target.closest("#pagerIndex")) {
      $(".atlas-panel").scrollIntoView({ behavior: motionOk() ? "smooth" : "auto", block: "start" });
      cellById.get(state.selected).focus({ preventScroll: true });
    }
  });

  new IntersectionObserver(([entry]) => {
    state.readerInView = entry.isIntersecting;
    updatePagerBar();
  }, { rootMargin: "0px 0px -35% 0px" }).observe(reader);
  [wide, narrow].forEach((query) => query.addEventListener("change", () => { updatePagerBar(); drawLines(false); }));
  new ResizeObserver(() => drawLines(false)).observe(board);

  function parseHash() {
    const match = /^#stratagem-(\d{1,2})$/.exec(window.location.hash);
    const id = match ? Number(match[1]) : null;
    return byId.has(id) ? id : null;
  }

  // ---------- Boot ----------
  if (window.CSS && "registerProperty" in CSS) root.classList.add("can-wipe");
  validateLongFormContent();
  const linked = parseHash();
  filtersBox.open = !narrow.matches;
  relabel();
  applyFilters({ autoSelect: false });
  select(linked ?? ids[0], { animate: false, updateHash: false, lines: false });
  requestAnimationFrame(() => drawLines(false));
  ["pointerdown", "keydown", "touchstart", "wheel"].forEach((type) => window.addEventListener(type, renderRestSoon, { once: true, passive: true }));
  window.addEventListener("beforeprint", () => ids.forEach(ensureRendered));
  if (linked) requestAnimationFrame(() => scrollToEntry(articleById.get(linked), false));
  document.fonts?.ready.then(() => drawLines(false));
})();
