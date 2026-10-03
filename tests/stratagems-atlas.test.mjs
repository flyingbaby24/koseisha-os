import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadAtlasData, buildPage } from '../docs/tools/build-stratagems.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dir = path.join(root, 'docs/research/stratagems');
const read = p => fs.readFileSync(path.join(dir, p), 'utf8');
const html = read('index.html');
const data = loadAtlasData();
const { stratagems, cognitiveTree, stratagemTranslations, uiTranslations, chapterLabels } = data;

test('the Atlas page is generated from the data (run node docs/tools/build-stratagems.mjs)', () => {
  assert.equal(buildPage(loadAtlasData()), html);
});

test('the 36 records are complete in both languages and their relations resolve', () => {
  assert.deepEqual(Array.from(stratagems, s => s.id), Array.from({ length: 36 }, (_, i) => i + 1));
  const ids = new Set(stratagems.map(s => s.id));
  for (const s of stratagems) {
    for (const field of ['name', 'reading', 'english', 'category', 'bias', 'behavioral', 'summary', 'example', 'interpretation', 'principle', 'noteTitle', 'noteUrl']) {
      assert.ok(String(s[field] ?? '').trim(), `ja #${s.id} ${field}`);
    }
    const en = stratagemTranslations.en[s.id];
    for (const field of ['name', 'category', 'bias', 'behavioral', 'summary', 'example', 'interpretation', 'principle', 'noteTitle']) {
      assert.ok(String(en?.[field] ?? '').trim(), `en #${s.id} ${field}`);
    }
    assert.ok(s.breakdown.length && en.breakdown.length, `#${s.id} breakdown`);
    for (const r of s.relatedStratagems) assert.ok(ids.has(r), `#${s.id} relates to missing #${r}`);
  }
  const placed = new Set(cognitiveTree.flatMap(g => g.children.flatMap(c => c.stratagemIds)));
  assert.equal(placed.size, 36, 'every stratagem sits in the cognitive tree');
});

test('the board holds the 36 stratagems in six chapters of six, in classical order', () => {
  const chapters = [...html.matchAll(/<div class="chapter" role="group" aria-labelledby="chapter-(\d)">([\s\S]*?)<\/ol><\/div>/g)];
  assert.equal(chapters.length, 6);
  chapters.forEach(([, n, body], i) => {
    assert.equal(Number(n), i + 1);
    const cells = [...body.matchAll(/<a class="cell" href="#stratagem-(\d+)" data-id="(\d+)">.*?<span class="cell-han" lang="ja">([^<]+)</g)];
    assert.deepEqual(cells.map(c => Number(c[1])), [1, 2, 3, 4, 5, 6].map(k => i * 6 + k));
    for (const [, id, , name] of cells) assert.equal(name, stratagems[id - 1].name);
  });
  assert.equal(chapterLabels.ja.length, 6);
  assert.equal(chapterLabels.en.length, 6);
});

test('existing URLs, anchors and language switching keep working', () => {
  for (const id of ['atlas', 'categories', 'concept', 'notes', 'search', 'category', 'languageJa', 'languageEn']) {
    assert.match(html, new RegExp(`id="${id}"`), id);
  }
  assert.match(html, /data-language="ja"/);
  assert.match(html, /data-language="en"/);
  // ?lang= wins, then the stored choice, then the browser language — the same order as i18n.js.
  assert.match(html, /get\('lang'\)/);
  assert.match(html, /localStorage\.getItem\('stratagems-language'\)/);
  assert.match(read('i18n.js'), /safeStorageGet\("stratagems-language"\)/);
  for (let id = 1; id <= 36; id++) assert.ok(html.includes(`id="stratagem-${id}"`), `no-JS target #stratagem-${id}`);
});

test('every UI string exists in Japanese and English, and the page pairs them', () => {
  assert.deepEqual(Object.keys(uiTranslations.en).sort(), Object.keys(uiTranslations.ja).sort());
  const ja = (html.match(/data-l="ja"/g) || []).length;
  const en = (html.match(/data-l="en"/g) || []).length;
  assert.ok(ja > 100);
  // Category member names are English-only; everything else is a pair.
  assert.equal(en - ja, 52);
  for (const [, key] of html.matchAll(/data-aria="([^"]+)"/g)) assert.ok(uiTranslations.en[key] && uiTranslations.ja[key], key);
});

test('the page is accessible without scripts: one h1, labelled fields, safe external links', () => {
  assert.equal((html.match(/<h1\b/g) || []).length, 1);
  for (const [, id] of html.matchAll(/<(?:input|select)[^>]*\bid="([^"]+)"/g)) assert.match(html, new RegExp(`<label for="${id}"`), id);
  for (const [img] of html.matchAll(/<img\b[^>]*>/g)) assert.match(img, /\balt="/);
  for (const [a] of html.matchAll(/<a\b[^>]*target="_blank"[^>]*>/g)) assert.match(a, /rel="noopener noreferrer"/);
  assert.match(html, /<a class="skip-link" href="#atlas">/);
  assert.match(html, /<noscript><div class="entries-static">/);
  const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map(m => m[1]);
  assert.equal(new Set(ids).size, ids.length, 'ids are unique');
});

test('local assets resolve and only self-hosted fonts are used', () => {
  for (const [, url] of html.matchAll(/(?:href|src)="([^"#:]+)"/g)) {
    assert.ok(fs.existsSync(path.join(dir, url.split('?')[0])), url);
  }
  assert.doesNotMatch(html + read('style.css'), /fonts\.googleapis|fonts\.gstatic/);
  for (const [, url] of read('style.css').matchAll(/url\("((?:\.\.\/)*[\w./-]+\.woff2)"\)/g)) {
    assert.ok(fs.existsSync(path.join(dir, url)), url);
  }
  assert.ok(fs.existsSync(path.join(dir, 'fonts/OFL-noto-serif-jp.txt')));
});

test('the display-face subset covers every name and chapter label it sets', () => {
  const glyphs = new Set(read('fonts/atlas-han-600.txt').trim());
  const display = stratagems.map(s => s.name).join('') + chapterLabels.ja.map(c => c.num + c.name + c.short).join('') + '三十六計一二三四五六';
  const missing = [...new Set(display)].filter(c => !glyphs.has(c));
  assert.deepEqual(missing, [], 'run site-redesign/tools/build_stratagems_font.py');
});
