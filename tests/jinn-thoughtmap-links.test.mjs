import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const docs = path.join(root, 'docs');
const authority = 'https://koseisha-os.onrender.com/';
const read = p => fs.readFileSync(path.join(docs, p), 'utf8');
const pages = ['index.html', 'index-ja.html', 'kunizukuri/index.html', 'kunizukuri/index-en.html', 'research/thoughtmap/index.html', 'research/thoughtmap/index-ja.html'];

test('all existing ThoughtMap primary links use the verified HTTPS authority', () => {
  for (const p of pages) {
    const html = read(p);
    assert.ok(!html.includes('thoughtmap.streamlit.app'), p);
    assert.ok(html.includes(authority), p);
    for (const a of html.matchAll(/<a\b[^>]*href="https:\/\/koseisha-os.onrender.com\/"[^>]*>/g)) {
      assert.match(a[0], /target="_blank"/);
      assert.match(a[0], /rel="noopener noreferrer"/);
    }
  }
});

test('both top pages preserve one existing project card and link to the localized introduction', () => {
  for (const [p, intro] of [['index.html', 'research/thoughtmap/'], ['index-ja.html', 'research/thoughtmap/index-ja.html']]) {
    const html = read(p);
    assert.equal([...html.matchAll(/class="project-card project-map"/g)].length, 1);
    assert.ok(html.includes('href="' + intro + '"'));
    assert.match(html, /class="project-card project-map" href="https:\/\/koseisha-os.onrender.com\/"/);
  }
});

test('introductions have bilingual routes, two launch actions and the shared site components', () => {
  for (const [p, lang] of [['research/thoughtmap/index.html', 'en'], ['research/thoughtmap/index-ja.html', 'ja']]) {
    const html = read(p);
    assert.ok(html.includes('<html lang="' + lang + '">'));
    assert.equal([...html.matchAll(/class="button primary" href="https:\/\/koseisha-os.onrender.com\/"/g)].length, 2);
    assert.match(html, /href="\.\.\/\.\.\/style.css"/);
    assert.match(html, /href="\.\.\/\.\.\/i18n\/language-switch.css"/);
    assert.match(html, /class="site-header"/);
    assert.match(html, /class="feature-list"/);
    assert.match(html, /hreflang="ja" href="index-ja.html"/);
    assert.match(html, /hreflang="en" href="\.\/"/);
  }
});

test('all local introduction links and assets resolve within the existing site', () => {
  for (const p of ['research/thoughtmap/index.html', 'research/thoughtmap/index-ja.html']) {
    for (const [, url] of read(p).matchAll(/(?:href|src)="([^"]+)"/g)) {
      if (/^(https:|#)/.test(url)) continue;
      const target = path.resolve(docs, path.dirname(p), url.split('#')[0]);
      assert.ok(target.startsWith(docs), url);
      assert.ok(fs.existsSync(target), p + ': ' + url);
      if (fs.statSync(target).isDirectory()) assert.ok(fs.existsSync(path.join(target, 'index.html')), url);
    }
  }
});

test('the sitemap includes both introduction routes and has no duplicate URL entries', () => {
  const xml = read('sitemap.xml');
  const urls = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1]);
  assert.equal(urls.length, new Set(urls).size);
  assert.ok(urls.includes('https://www.jinn-project.com/research/thoughtmap/'));
  assert.ok(urls.includes('https://www.jinn-project.com/research/thoughtmap/index-ja.html'));
});

test('the top-page localization source preserves the new link and translations', () => {
  const source = read('tools/generate-index-ja.mjs');
  assert.ok(source.includes('"About ThoughtMap":"ThoughtMapについて"'));
  assert.ok(source.includes('"Explore ThoughtMap →":"ThoughtMapについて →"'));
  assert.ok(source.includes('href="research/thoughtmap/index-ja.html"'));
});

