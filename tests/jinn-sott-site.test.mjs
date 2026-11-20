import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const docs = path.join(root, 'docs');
const site = path.join(docs, 'sott');
const read = p => fs.readFileSync(path.join(docs, p), 'utf8');
const pages = ['sott/index.html', 'sott/index-ja.html'];
const sections = ['top', 'territory', 'battlefield', 'decisions', 'gallery', 'ai', 'lineage', 'development'];
const ids = html => new Set([...html.matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
const visible = html => html.replace(/<script[\s\S]*?<\/script>/g, ' ').replace(/<head>[\s\S]*?<\/head>/, ' ');

test('the generator is in sync with the committed Source of Thought Tactics pages', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'jinn-sott-'));
  fs.mkdirSync(path.join(tmp, 'docs/tools'), { recursive: true });
  fs.mkdirSync(path.join(tmp, 'docs/sott'), { recursive: true });
  fs.copyFileSync(path.join(docs, 'tools/build-sott.mjs'), path.join(tmp, 'docs/tools/build-sott.mjs'));
  execFileSync(process.execPath, [path.join(tmp, 'docs/tools/build-sott.mjs')]);
  for (const p of pages) assert.equal(fs.readFileSync(path.join(tmp, 'docs', p), 'utf8'), read(p).replace(/\r\n/g, '\n'), p + ' differs from generator output; run node docs/tools/build-sott.mjs');
  fs.rmSync(tmp, { recursive: true, force: true });
});

test('both languages carry the same eight sections, one h1 and the page landmarks', () => {
  for (const p of pages) {
    const html = read(p);
    assert.equal([...html.matchAll(/<h1[\s>]/g)].length, 1, p);
    for (const id of sections) assert.ok(ids(html).has(id), p + ': #' + id);
    for (const tag of ['<header', '<main id="main"', '<footer', 'class="skip-link" href="#main"']) assert.ok(html.includes(tag), p + ': ' + tag);
    const levels = [...visible(html).matchAll(/<h([1-6])[\s>]/g)].map(m => Number(m[1]));
    levels.forEach((l, i) => assert.ok(i === 0 || l - levels[i - 1] <= 1, `${p}: heading level jumps from h${levels[i - 1]} to h${l}`));
  }
  assert.match(read(pages[0]), /<html lang="en"/);
  assert.match(read(pages[1]), /<html lang="ja"/);
});

test('every local link, asset and fragment on the pages resolves', () => {
  const failures = [];
  for (const p of pages) {
    const html = read(p), own = ids(html), dir = path.dirname(path.join(docs, p));
    for (const [, url] of html.matchAll(/(?:href|src|srcset|poster|data-poster|data-src|data-full)="([^"]+)"/g)) {
      for (const candidate of url.split(',').map(s => s.trim().split(/\s+/)[0])) {
        if (/^(https?:|mailto:|data:)/.test(candidate)) continue;
        const [rel, hash] = candidate.split('#');
        if (!rel) { if (hash && !own.has(hash)) failures.push(`${p}: #${hash}`); continue; }
        let target = path.resolve(dir, rel.split('?')[0]);
        if (!target.startsWith(docs) || !fs.existsSync(target)) { failures.push(`${p}: ${candidate}`); continue; }
        if (fs.statSync(target).isDirectory()) target = path.join(target, 'index.html');
        if (!fs.existsSync(target)) failures.push(`${p}: ${candidate}`);
        else if (hash && target.endsWith('.html') && !ids(fs.readFileSync(target, 'utf8')).has(hash)) failures.push(`${p}: ${candidate}`);
      }
    }
  }
  assert.deepEqual(failures, []);
});

test('images are labelled and sized, external links are safe, fonts are self-hosted', () => {
  for (const p of pages) {
    const html = read(p);
    for (const [img] of html.matchAll(/<img\b[^>]*>/g)) {
      assert.match(img, /\salt="[^"]*"/, p + ': ' + img);
      assert.match(img, /\swidth="\d+"[^>]*\sheight="\d+"/, p + ': ' + img);
    }
    for (const [a] of html.matchAll(/<a\b[^>]*target="_blank"[^>]*>/g)) assert.match(a, /rel="noopener noreferrer"/, p + ': ' + a);
    assert.doesNotMatch(html, /fonts\.googleapis|fonts\.gstatic/, p);
    assert.equal([...html.matchAll(/rel="stylesheet"/g)].length, 1, p);
  }
  const css = fs.readFileSync(path.join(site, 'sott.css'), 'utf8');
  assert.doesNotMatch(css, /@import/);
  for (const [, font] of css.matchAll(/url\(([^)]+\.woff2)\)/g)) assert.ok(fs.existsSync(path.resolve(site, font)), font);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
});

test('canonical, reciprocal hreflang, social card, structured data and sitemap entries', () => {
  const expected = { 'sott/index.html': 'https://www.jinn-project.com/sott/', 'sott/index-ja.html': 'https://www.jinn-project.com/sott/index-ja.html' };
  const xml = read('sitemap.xml');
  for (const p of pages) {
    const html = read(p);
    assert.ok(html.includes(`<link rel="canonical" href="${expected[p]}">`), p);
    assert.ok(html.includes('<link rel="alternate" hreflang="en" href="https://www.jinn-project.com/sott/">'), p);
    assert.ok(html.includes('<link rel="alternate" hreflang="ja" href="https://www.jinn-project.com/sott/index-ja.html">'), p);
    assert.ok(html.includes('<link rel="alternate" hreflang="x-default" href="https://www.jinn-project.com/sott/">'), p);
    const image = html.match(/property="og:image" content="https:\/\/www\.jinn-project\.com\/([^"]+)"/);
    assert.ok(image && fs.existsSync(path.join(docs, image[1])), p + ': og:image file');
    assert.ok(html.includes('name="twitter:card" content="summary_large_image"'), p);
    const ld = JSON.parse(html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1]);
    assert.ok(ld['@graph'].some(n => n['@type'] === 'VideoGame' && n.creativeWorkStatus === 'In development'), p);
    const description = html.match(/<meta name="description" content="([^"]+)"/)[1];
    assert.ok(description.length >= 50 && description.length <= 200, p + ': description length ' + description.length);
    assert.ok(xml.includes(`<loc>${expected[p]}</loc>`), p + ' missing from sitemap.xml');
  }
});

test('the public alpha is offered as a play link while the work stays in development; no private source link', () => {
  for (const p of pages) {
    const html = read(p), text = visible(html);
    const links = [...html.matchAll(/<a class="btn btn-gold btn-play" href="([^"]+)" target="_blank" rel="noopener noreferrer" data-play>([^<]+)</g)];
    assert.equal(links.length, 2, p + ': play link in the hero and in the development section');
    for (const [, href, label] of links) {
      assert.equal(href, 'https://sott-8kg.pages.dev/formation.html', p);
      assert.equal(label.trim(), p.endsWith('-ja.html') ? 'SoTTをプレイ' : 'PLAY SoTT', p);
    }
    assert.doesNotMatch(html, /github\.com\/flyingbaby24\/sott/, p);
    assert.match(text, p.endsWith('-ja.html') ? /開発中/ : /In development/, p);
  }
});

test('the page ships real media within budget and attaches video only on demand', () => {
  const media = path.join(site, 'media');
  const files = fs.readdirSync(media);
  assert.ok(files.filter(f => /^shot-[a-z]+\.webp$/.test(f)).length >= 8, 'at least eight screenshots');
  assert.ok(files.filter(f => f.endsWith('.mp4')).length >= 8, 'hero, highlight and six feature clips');
  const total = files.reduce((n, f) => n + fs.statSync(path.join(media, f)).size, 0);
  assert.ok(total < 32 * 1024 * 1024, 'media folder is ' + (total / 1048576).toFixed(1) + ' MB');
  for (const f of files) assert.ok(fs.statSync(path.join(media, f)).size < 12 * 1024 * 1024, f + ' is too large for the repository');
  for (const p of pages) {
    const html = read(p);
    for (const [video] of html.matchAll(/<video\b[^>]*>/g)) assert.match(video, /preload="none"/, p + ': ' + video);
    assert.doesNotMatch(html, /<source src=|<video[^>]*\ssrc=/, p + ': videos must be attached on demand');
    assert.doesNotMatch(html, /<video[^>]*autoplay/, p);
  }
});

test('the board data is the 50-node / 78-link graph with five starting nodes per side', () => {
  const window = {};
  new Function('window', fs.readFileSync(path.join(site, 'sott-data.js'), 'utf8'))(window);
  const d = window.SOTT_DATA;
  assert.equal(d.nodes.length, 50);
  assert.equal(d.edges.length, 78);
  assert.equal(d.start.A.length, 5);
  assert.equal(d.start.B.length, 5);
  assert.equal(d.keys.length, 10);
  const known = new Set(d.nodes.map(n => n[0]));
  for (const [a, b] of d.edges) assert.ok(known.has(a) && known.has(b));
  for (const w of d.works) assert.equal(w.p.length, 10, w.title);
});

test('Jinn Project and Source of Thought link to the work in the reader language, and it links back', () => {
  for (const [p, href] of [['index.html', 'href="sott/"'], ['index-ja.html', 'href="sott/index-ja.html"']]) {
    const html = read(p);
    assert.ok(html.split(href).length - 1 >= 3, p + ': card, research loop and footer link');
    assert.match(html, /<li class="work-item" data-kind="game">\s*<a class="project-card project-sott" id="p-sott"/, p + ': listed under Games');
    assert.ok(html.includes('data-node="sott"') && html.includes('data-pair="sot sott"'), p + ': project field');
  }
  assert.ok(read('assets/site.css').includes('[data-node="sott"]'));
  assert.ok(read('research/source-of-thought/index.html').includes('href="../../sott/"'));
  assert.ok(read('research/source-of-thought/index-ja.html').includes('href="../../sott/index-ja.html"'));
  const back = [
    ['sott/index.html', 'href="../"', 'href="../research/source-of-thought/"', 'href="../research/thoughtmap/"'],
    ['sott/index-ja.html', 'href="../index-ja.html"', 'href="../research/source-of-thought/index-ja.html"', 'href="../research/thoughtmap/index-ja.html"'],
  ];
  for (const [p, ...links] of back) {
    const html = read(p);
    for (const link of links) assert.ok(html.includes(link), p + ': ' + link);
    assert.ok(html.includes('jinn-mark-96') && html.includes('Jinn Project'), p + ': Jinn brand');
  }
});
