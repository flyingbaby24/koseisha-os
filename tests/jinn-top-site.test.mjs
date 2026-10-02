import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const docs = path.join(root, 'docs');
const read = p => fs.readFileSync(path.join(docs, p), 'utf8');
const tops = ['index.html', 'index-ja.html'];
const walk = p => fs.readdirSync(p, { withFileTypes: true }).flatMap(e => e.isDirectory() ? walk(path.join(p, e.name)) : [path.join(p, e.name)]);
const ids = html => new Set([...html.matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
const visibleText = html => html
  .replace(/<script[\s\S]*?<\/script>/g, ' ')
  .replace(/<style[\s\S]*?<\/style>/g, ' ')
  .replace(/<head>[\s\S]*?<\/head>/, ' ')
  .split(/<[^>]+>/).map(s => s.trim()).filter(Boolean);

test('the generator is in sync with the committed top pages', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'jinn-top-'));
  fs.mkdirSync(path.join(tmp, 'docs/tools'), { recursive: true });
  fs.copyFileSync(path.join(docs, 'tools/generate-index-ja.mjs'), path.join(tmp, 'docs/tools/generate-index-ja.mjs'));
  fs.copyFileSync(path.join(docs, 'index.html'), path.join(tmp, 'docs/index.html'));
  execFileSync(process.execPath, [path.join(tmp, 'docs/tools/generate-index-ja.mjs')]);
  for (const p of tops) assert.equal(fs.readFileSync(path.join(tmp, 'docs', p), 'utf8'), read(p), p + ' differs from generator output; run node docs/tools/generate-index-ja.mjs');
  fs.rmSync(tmp, { recursive: true, force: true });
});

test('every local link, asset and fragment on the top pages resolves', () => {
  const failures = [];
  for (const p of tops) {
    const html = read(p);
    const own = ids(html);
    for (const [, url] of html.matchAll(/(?:href|src|srcset)="([^"]+)"/g)) {
      for (const candidate of url.split(',').map(s => s.trim().split(/\s+/)[0])) {
        if (/^(https?:|mailto:|data:)/.test(candidate)) continue;
        const [rel, hash] = candidate.split('#');
        if (!rel) { if (hash && !own.has(hash)) failures.push(`${p}: #${hash}`); continue; }
        let target = path.resolve(docs, rel.split('?')[0]);
        if (!target.startsWith(docs) || !fs.existsSync(target)) { failures.push(`${p}: ${candidate}`); continue; }
        if (fs.statSync(target).isDirectory()) target = path.join(target, 'index.html');
        if (!fs.existsSync(target)) failures.push(`${p}: ${candidate}`);
        else if (hash && target.endsWith('.html') && !ids(fs.readFileSync(target, 'utf8')).has(hash)) failures.push(`${p}: ${candidate}`);
      }
    }
  }
  assert.deepEqual(failures, []);
});

test('anchors that other pages use to link into the top pages still exist', () => {
  const failures = [];
  for (const file of walk(docs).filter(f => f.endsWith('.html'))) {
    for (const [, top, hash] of fs.readFileSync(file, 'utf8').matchAll(/href="(?:\.\.\/)*(index(?:-ja)?\.html)#([^"]+)"/g)) {
      if (path.dirname(file) === docs && !tops.includes(path.basename(file))) continue;
      if (!ids(read(top)).has(hash)) failures.push(`${path.relative(docs, file)} → ${top}#${hash}`);
    }
  }
  assert.deepEqual([...new Set(failures)], []);
});

test('top pages expose one h1, landmarks, labelled images and safe external links', () => {
  for (const p of tops) {
    const html = read(p);
    assert.equal([...html.matchAll(/<h1[\s>]/g)].length, 1, p);
    for (const tag of ['<header', '<main id="main"', '<footer', 'class="skip-link" href="#main"']) assert.ok(html.includes(tag), p + ': ' + tag);
    for (const [img] of html.matchAll(/<img\b[^>]*>/g)) {
      assert.match(img, /\salt="[^"]*"/, p + ': ' + img);
      assert.match(img, /\swidth="\d+"[^>]*\sheight="\d+"/, p + ': ' + img);
    }
    for (const [a] of html.matchAll(/<a\b[^>]*target="_blank"[^>]*>/g)) assert.match(a, /rel="noopener noreferrer"/, p + ': ' + a);
    assert.doesNotMatch(html, /data-counter|class="reveal"/, p + ': content must not depend on JS to become visible');
  }
});

test('Japanese top page carries no untranslated English sentences', () => {
  const names = /\b(Jinn Project|Source of Thought|ThoughtMap|Stratagems Atlas|Grounding Sole|Mandalizm|JinnSP|Daidarabotchi|Thought|Body|Material|System|Cyber Shrine|Family|Card|Skill|Formation|Resonance|Hate System|Skill Generation|Web|Three\.js|OSS|PWA|Android|iOS|ORCID|GitHub|Patreon|Atlas|Issue|EN|English|AI|embedding)\b/g;
  const leftovers = visibleText(read('index-ja.html'))
    .map(t => t.replace(names, ''))
    .filter(t => /[A-Za-z]{2,}(?:\s+[A-Za-z]{2,}){2,}/.test(t));
  assert.deepEqual(leftovers, []);
  assert.match(read('index-ja.html'), /<html lang="ja">/);
});

test('top pages ship canonical, reciprocal hreflang, social cards and structured data', () => {
  const expected = { 'index.html': 'https://www.jinn-project.com/', 'index-ja.html': 'https://www.jinn-project.com/index-ja.html' };
  for (const p of tops) {
    const html = read(p);
    assert.ok(html.includes(`<link rel="canonical" href="${expected[p]}">`), p);
    assert.ok(html.includes('<link rel="alternate" hreflang="en" href="https://www.jinn-project.com/">'), p);
    assert.ok(html.includes('<link rel="alternate" hreflang="ja" href="https://www.jinn-project.com/index-ja.html">'), p);
    assert.ok(html.includes('<link rel="alternate" hreflang="x-default" href="https://www.jinn-project.com/">'), p);
    const image = html.match(/property="og:image" content="https:\/\/www\.jinn-project\.com\/([^"]+)"/);
    assert.ok(image && fs.existsSync(path.join(docs, image[1])), p + ': og:image file');
    const ld = JSON.parse(html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1]);
    const logo = ld['@graph'].find(n => n['@type'] === 'Organization').logo.replace('https://www.jinn-project.com/', '');
    assert.ok(fs.existsSync(path.join(docs, logo)), p + ': Organization.logo file');
    const description = html.match(/<meta name="description" content="([^"]+)"/)[1];
    assert.ok(description.length >= 50 && description.length <= 200, p + ': description length ' + description.length);
  }
  assert.match(read('robots.txt'), /Sitemap: https:\/\/www\.jinn-project\.com\/sitemap\.xml/);
  assert.ok(read('sitemap.xml').includes('<loc>https://www.jinn-project.com/</loc>'));
  assert.ok(fs.existsSync(path.join(docs, 'favicon.ico')));
});

test('the top page loads only self-hosted fonts and a single stylesheet', () => {
  for (const p of tops) {
    const html = read(p);
    assert.doesNotMatch(html, /fonts\.googleapis|fonts\.gstatic/, p);
    assert.equal([...html.matchAll(/rel="stylesheet"/g)].length, 1, p);
  }
  const css = read('assets/site.css');
  assert.doesNotMatch(css, /@import/);
  for (const [, font] of css.matchAll(/url\((fonts\/[^)]+)\)/g)) assert.ok(fs.existsSync(path.join(docs, 'assets', font)), font);
});

test('the top pages show the current ThoughtMap corpus figure in every place', () => {
  for (const p of tops) {
    const html = read(p);
    assert.doesNotMatch(html, /32,695/, p);
    assert.equal(html.split('64,000').length - 1, 4, p);
  }
});
