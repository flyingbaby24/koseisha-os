import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const docs = path.join(root, 'docs');
const site = path.join(docs, 'research/source-of-thought');
const read = p => fs.readFileSync(path.join(site, p), 'utf8');
const walk = p => fs.readdirSync(p, {withFileTypes:true}).flatMap(e => e.isDirectory() ? walk(path.join(p,e.name)) : [path.join(p,e.name)]);
const htmlFiles = walk(site).filter(p => p.endsWith('.html'));
const currentPages = ['index.html','index-ja.html','gallery.html','gallery-ja.html','roadmap.html','roadmap-ja.html','changelog.html','changelog-ja.html','devblog/index.html','devblog/index-ja.html'];

test('current introduction covers the public game and safe playable authority in both languages', () => {
  for (const p of ['index.html','index-ja.html']) {
    const h = read(p);
    for (const text of ['10-card Deck','5 Battle Members','5×5 Formation','Resonance','Mind','Human','System','Strategic SP','Specializations','Victory / Result','Three.js']) assert.ok(h.includes(text), p+': '+text);
    assert.equal([...h.matchAll(/class="button primary" href="https:\/\/sot-web.onrender.com\/"/g)].length,2);
    assert.match(h,/target="_blank" rel="noopener noreferrer"/);
    assert.ok(!h.includes('github.com/flyingbaby24/sot-web'));
    assert.ok(h.includes(p==='index.html'?'href="../thoughtmap/"':'href="../thoughtmap/index-ja.html"'));
  }
});

test('all twenty retained routes use shared Jinn identity and localized metadata', () => {
  assert.equal(htmlFiles.length,20);
  for (const p of htmlFiles) {
    const h=fs.readFileSync(p,'utf8');
    assert.match(h,/class="site-header"/); assert.match(h,/<footer id="contact">/);
    assert.match(h,/href="(?:\.\.\/)+style.css"/); assert.match(h,/i18n\/language-switch.css/);
    for(const marker of ['rel="canonical"','hreflang="en"','hreflang="ja"','property="og:url"','property="og:image"']) assert.ok(h.includes(marker),p+': '+marker);
    assert.match(h,/kunizukuri\/shell.js/);
  }
});

test('current pages contain no old platform, wishlist or screenshot placeholder claims', () => {
  for(const p of currentPages) {
    assert.doesNotMatch(read(p),/\bUnity\b|\bSteam\b|Wishlist|screenshot placeholder|coming soon/i,p);
  }
  for(const p of ['index.html','index-ja.html']) {
    const h=fs.readFileSync(path.join(docs,p),'utf8');
    assert.doesNotMatch(h,/Screenshot Placeholder|スクリーンショット プレースホルダー/);
    assert.ok(h.includes('screenshots/web-v1/battle.jpg'));
  }
});

test('historical articles and technical index are explicitly archive, not current specification', () => {
  for(const p of htmlFiles.filter(p=>p.includes(path.sep+'articles'+path.sep))) {
    const h=fs.readFileSync(p,'utf8');
    assert.match(h,/ARCHIVE \/ DEVELOPMENT HISTORY/);
    assert.match(h,/class="article-body"/);
    assert.match(h,/href="\.\.\/\.\.\/(?:index-ja.html)?">/);
  }
  assert.match(read('README.md'),/ARCHIVE \/ DEVELOPMENT HISTORY/);
});

test('every local route, asset and fragment referenced by the retained pages resolves', () => {
  const failures=[];
  for(const p of htmlFiles) for(const [,url] of fs.readFileSync(p,'utf8').matchAll(/(?:href|src)="([^"]+)"/g)) {
    if(/^(https?:|mailto:|data:)/.test(url)) continue;
    const [rel,hash]=url.split('#');
    let target=rel?path.resolve(path.dirname(p),rel.split('?')[0]):p;
    if(!target.startsWith(docs)||!fs.existsSync(target)){failures.push(p+': '+url);continue;}
    if(fs.statSync(target).isDirectory()) target=path.join(target,'index.html');
    if(!fs.existsSync(target)){failures.push(p+': '+url);continue;}
    if(hash&&target.endsWith('.html')&&!fs.readFileSync(target,'utf8').includes('id="'+hash+'"')) failures.push(p+': missing #'+hash);
  }
  assert.deepEqual(failures,[]);
});

test('seven actual captures match their byte-pinned provenance', () => {
  const audit=JSON.parse(read('screenshots/web-v1/provenance.json'));
  assert.equal(audit.images.length,7);
  for(const i of audit.images) {
    const bytes=fs.readFileSync(path.join(site,'screenshots/web-v1',i.file));
    assert.equal(bytes.length,i.bytes); assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),i.sha256);
    assert.ok(i.authority); assert.equal(i.synthetic,false);
  }
});

test('regeneration cannot restore the old microsite or overwrite the shared sitemap', () => {
  const src=read('tools/generate-localized-pages.mjs');
  assert.doesNotMatch(src,/writeFile|writeFileSync/);
  assert.match(src,/hreflang/);
  const xml=fs.readFileSync(path.join(docs,'sitemap.xml'),'utf8');
  assert.ok(xml.includes('<loc>https://www.jinn-project.com/research/source-of-thought/</loc>'));
  assert.ok(xml.includes('<loc>https://www.jinn-project.com/research/source-of-thought/index-ja.html</loc>'));
});

test('top pages preserve localized Source of Thought and independent ThoughtMap entries', () => {
  for(const [p,sot,map] of [['index.html','research/source-of-thought/','research/thoughtmap/'],['index-ja.html','research/source-of-thought/index-ja.html','research/thoughtmap/index-ja.html']]) {
    const h=fs.readFileSync(path.join(docs,p),'utf8');
    assert.ok(h.includes('href="'+sot+'"')); assert.ok(h.includes('href="'+map+'"'));
    assert.ok(h.includes('class="project-card project-map"'));
  }
});
