// Source of Thought Tactics — work page. Progressive enhancement only: every section reads and every
// link works without this file. No libraries; SVG + CSS, driven by the real board graph in sott-data.js.
(() => {
  const D = window.SOTT_DATA;
  const root = document.documentElement;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const T = (() => { try { return JSON.parse($('#sott-i18n').textContent); } catch { return {}; } })();
  const t = (k, v = {}) => (T[k] ?? k).replace(/\{(\w+)\}/g, (_, n) => v[n] ?? '');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const conn = navigator.connection || {};
  const lite = reduce.matches || conn.saveData || (navigator.deviceMemory && navigator.deviceMemory <= 2) || (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 2);
  if (lite) root.classList.add('lite');
  const NS = 'http://www.w3.org/2000/svg';
  const svg = (tag, attrs = {}, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); parent?.appendChild(e); return e; };
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));

  // ---- Board geometry: the game's own node positions, seen from the battle camera's diagonal.
  const P = new Map(), ADJ = new Map();
  if (D) {
    for (const [id, x, y] of D.nodes) { P.set(id, [x - y, (x + y) * 0.5]); ADJ.set(id, []); }
    for (const [a, b] of D.edges) { ADJ.get(a).push(b); ADJ.get(b).push(a); }
  }
  const oct = (cx, cy, rx, ry) => { const k = 0.42; return [[-rx * k, -ry], [rx * k, -ry], [rx, -ry * k], [rx, ry * k], [rx * k, ry], [-rx * k, ry], [-rx, ry * k], [-rx, -ry * k]].map(([x, y]) => (cx + x).toFixed(2) + ',' + (cy + y).toFixed(2)).join(' '); };
  const nid = (n) => 'N' + String(n).padStart(3, '0');

  // ---- Header, index sheet, rail
  const header = $('.s-header');
  const sheet = $('.s-index'), menuBtn = $('.s-menu-btn');
  if (sheet && menuBtn) {
    const setOpen = (open, focusBack) => {
      sheet.classList.toggle('is-open', open); menuBtn.setAttribute('aria-expanded', String(open));
      sheet.inert = !open; root.style.overflow = open ? 'hidden' : '';
      if (open) $('a', sheet)?.focus(); else if (focusBack) menuBtn.focus();
    };
    sheet.inert = true; menuBtn.hidden = false;
    menuBtn.addEventListener('click', () => setOpen(menuBtn.getAttribute('aria-expanded') !== 'true'));
    sheet.addEventListener('click', (e) => { if (e.target.closest('a') || e.target === sheet) setOpen(false); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && sheet.classList.contains('is-open')) setOpen(false, true); });
  }
  const railLinks = $$('.s-rail a');
  const secs = railLinks.map((a) => $(a.hash)).filter(Boolean);
  if ('IntersectionObserver' in window && secs.length) {
    const spy = new IntersectionObserver((es) => { for (const e of es) if (e.isIntersecting) railLinks.forEach((a) => a.hash === '#' + e.target.id ? a.setAttribute('aria-current', 'true') : a.removeAttribute('aria-current')); }, { rootMargin: '-45% 0px -50% 0px' });
    secs.forEach((s) => spy.observe(s));
  }
  $$('.s-lang a').forEach((a) => a.addEventListener('click', (e) => { if (!location.hash) return; e.preventDefault(); const u = new URL(a.href, location.href); u.hash = location.hash; location.href = u.href; }));

  // ---- Reveal (only what starts below the fold is ever hidden)
  if (!reduce.matches && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver((es) => { for (const e of es) if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }, { rootMargin: '0px 0px -8% 0px' });
    const els = $$('[data-rv]'), below = els.filter((el) => el.getBoundingClientRect().top > innerHeight * 0.92);
    for (const el of below) { el.classList.add('rv'); io.observe(el); }
  }

  // ---- Hero: the board's links draw themselves, then the footage takes over
  const hero = $('.hero'), net = $('.hero-net'), video = $('.hero-media video');
  const heroNodes = [];
  if (hero && net && D) {
    net.setAttribute('viewBox', '-21 -11.2 42 22.4'); net.setAttribute('preserveAspectRatio', 'xMidYMid slice');
    const order = new Map(); // breadth-first from the two starting corners, so the network grows like territory
    const q = [...D.start.A, ...D.start.B]; q.forEach((n) => order.set(n, 0));
    while (q.length) { const n = q.shift(); for (const m of ADJ.get(n)) if (!order.has(m)) { order.set(m, order.get(n) + 1); q.push(m); } }
    const lines = new Map();
    for (const [a, b] of D.edges) {
      const [x1, y1] = P.get(a), [x2, y2] = P.get(b), d = Math.min(order.get(a), order.get(b)) * 0.11;
      const l = svg('line', { x1, y1, x2, y2, pathLength: 1, style: `--d:${d.toFixed(2)}` }, net);
      lines.set(a + '-' + b, l);
    }
    for (const [id] of D.nodes) {
      const [cx, cy] = P.get(id);
      const c = svg('circle', { cx, cy, r: 0.2, style: `--d:${(order.get(id) * 0.11 + 0.1).toFixed(2)}` }, net);
      if (D.start.B.includes(id)) c.classList.add('b');
      heroNodes.push({ id, cx, cy, el: c });
    }
    if (!reduce.matches) {
      net.classList.add('boot'); hero.classList.add('boot');
      setTimeout(() => { net.classList.remove('boot'); net.classList.add('settle'); }, 2600);
      // Pointer: the node under the cursor and its links answer, as a selected node does in the game.
      let hot = null;
      const light = (id) => {
        if (hot === id) return; hot = id;
        heroNodes.forEach((n) => n.el.classList.toggle('hot', n.id === id || (id != null && ADJ.get(id).includes(n.id))));
        lines.forEach((l, k) => { const [a, b] = k.split('-').map(Number); l.classList.toggle('hot', a === id || b === id); });
      };
      if (!lite && matchMedia('(hover: hover)').matches) {
        hero.addEventListener('pointermove', (e) => {
          const r = net.getBoundingClientRect(), s = Math.max(r.width / 42, r.height / 22.4);
          const x = (e.clientX - r.left - r.width / 2) / s, y = (e.clientY - r.top - r.height / 2) / s;
          let best = null, bd = 2.2 * 2.2;
          for (const n of heroNodes) { const d = (n.cx - x) ** 2 + (n.cy - y) ** 2; if (d < bd) { bd = d; best = n.id; } }
          light(best);
          hero.style.setProperty('--mx', ((e.clientX / innerWidth) - 0.5).toFixed(3)); hero.style.setProperty('--my', ((e.clientY / innerHeight) - 0.5).toFixed(3));
        }, { passive: true });
        hero.addEventListener('pointerleave', () => light(null));
      }
    }
  }
  // Hero film: muted loop. It never blocks the first paint (the poster is the LCP image) and can be paused.
  const vToggle = $('[data-video-toggle]');
  if (video) {
    const setLabel = () => { if (!vToggle) return; const on = !video.paused; vToggle.setAttribute('aria-pressed', String(!on)); $('span', vToggle).textContent = on ? t('pause') : t('play'); $('svg', vToggle).innerHTML = on ? '<path d="M1 0h3.5v12H1zM7.5 0H11v12H7.5z"/>' : '<path d="M1 0l10 6-10 6z"/>'; };
    video.addEventListener('playing', () => { video.classList.add('is-playing'); setLabel(); });
    video.addEventListener('pause', setLabel);
    const start = () => { if (video.dataset.loaded) return video.play().catch(() => {}); video.dataset.loaded = '1'; for (const s of $$('source', video)) s.src = s.dataset.src; video.load(); video.play().catch(() => {}); };
    if (vToggle) { vToggle.hidden = false; vToggle.addEventListener('click', () => (video.paused ? start() : video.pause())); setLabel(); }
    if (!reduce.matches && !conn.saveData) (document.readyState === 'complete' ? setTimeout(start, 300) : addEventListener('load', () => setTimeout(start, 300)));
    if ('IntersectionObserver' in window) new IntersectionObserver(([e]) => { if (!video.dataset.loaded || video.dataset.user) return; e.isIntersecting ? video.play().catch(() => {}) : video.pause(); }).observe(hero);
    vToggle?.addEventListener('click', () => { video.dataset.user = video.paused ? '' : '1'; });
  }

  // ---- One scroll loop: header state, hero depth, link joints
  const joints = $$('.joint'), linSvg = $('.lin-svg');
  let ticking = false;
  const frame = () => {
    ticking = false;
    const y = scrollY, vh = innerHeight;
    header?.classList.toggle('is-solid', y > vh * 0.55);
    if (hero && y < vh * 1.2 && !reduce.matches) hero.style.setProperty('--hp', clamp(y / vh).toFixed(3));
    for (const j of joints) { const r = j.getBoundingClientRect(); if (r.bottom < -50 || r.top > vh + 50) continue; j.style.setProperty('--p', clamp((vh * 0.92 - r.top) / (vh * 0.55)).toFixed(3)); }
    if (linSvg) { const r = linSvg.getBoundingClientRect(); if (r.bottom > 0 && r.top < vh) linSvg.style.setProperty('--p', clamp((vh * 0.8 - r.top) / (vh * 0.5)).toFixed(3)); }
  };
  const onScroll = () => { if (!ticking) { ticking = true; requestAnimationFrame(frame); } };
  addEventListener('scroll', onScroll, { passive: true }); addEventListener('resize', onScroll); frame();
  if (reduce.matches) joints.forEach((j) => j.style.setProperty('--p', 1));

  // ---- Mini board (shared by the flow stage)
  const drawMini = (el, opts = {}) => {
    el.innerHTML = ''; el.setAttribute('viewBox', '-20.5 -10.6 41 21.2');
    const E = new Map(), N = new Map();
    for (const [a, b] of D.edges) { const [x1, y1] = P.get(a), [x2, y2] = P.get(b); E.set(a + '-' + b, svg('line', { class: 'e', x1, y1, x2, y2 }, el)); }
    for (const [id] of D.nodes) { const [cx, cy] = P.get(id); N.set(id, svg('polygon', { class: 'n', points: oct(cx, cy, 0.9, 0.5) }, el)); }
    return { E, N, unit: (id, cls) => { const [cx, cy] = P.get(id); return svg('circle', { class: 'u ' + cls, cx, cy: cy - 0.15, r: 0.42 }, el); }, halo: (id) => { const [cx, cy] = P.get(id); return svg('circle', { class: 'halo', cx, cy: cy - 0.15, r: 0.5 }, el); } };
  };
  // Territory as the game grows it: each side claims the nodes its units pass through.
  const spread = (steps) => {
    const own = new Map(); const fa = [...D.start.A], fb = [...D.start.B];
    for (let i = 0; i < steps; i++) for (const [f, team] of [[fa, 'a'], [fb, 'b']]) {
      const next = []; for (const n of f) for (const m of ADJ.get(n)) if (!own.has(m) && !D.start.A.includes(m) && !D.start.B.includes(m)) { own.set(m, team); next.push(m); }
      f.length = 0; f.push(...next.slice(0, 5));
    }
    return own;
  };

  // ---- 02 Flow: work -> parameters -> unit -> network -> tactics
  // Built when the main thread is free, so the first screen is never waiting on diagrams further down.
  const idle = window.requestIdleCallback ? (f) => requestIdleCallback(f, { timeout: 1200 }) : (f) => setTimeout(f, 120);
  const stage = $('.flow-stage');
  if (stage && D) idle(() => {
    const picks = $$('.flow-pick button'), steps = $$('.flow-steps li');
    const work = $('.l-work', stage), params = $('.l-params', stage), unit = $('.l-unit', stage), netL = $('.l-net', stage);
    const dots = $$('.stage-steps i', stage), tag = $('.stage-tag', stage);
    const RANGE = { hp: [82, 132], sp: [70, 120], atk: [10, 28], def: [8, 18], spd: [82, 112], mob: [1, 3] };
    const ring = (r) => D.keys.map((_, i) => { const a = (-90 + 36 * i) * Math.PI / 180; return (50 + r * Math.cos(a)).toFixed(1) + ',' + (50 + r * Math.sin(a)).toFixed(1); }).join(' ');
    const sig = (w, r0 = 5, r1 = 38) => w.p.map((v, i) => { const a = (-90 + 36 * i) * Math.PI / 180, r = r0 + r1 * (v / D.peak) ** 0.8; return (50 + r * Math.cos(a)).toFixed(1) + ',' + (50 + r * Math.sin(a)).toFixed(1); }).join(' ');
    let cur = 0, step = 1, mini = null;
    const render = () => {
      const w = D.works[cur], top = w.p.indexOf(Math.max(...w.p));
      work.innerHTML = `<div class="work-card"><small>${t('workTag')} · No. ${w.id}</small><h4></h4><p>${w.concepts.map((c) => `<span>${c}</span>`).join('')}</p></div>`;
      $('h4', work).textContent = w.title;
      params.innerHTML = `<svg class="radar" viewBox="-34 -8 168 116" role="img" aria-label="${t('radarAlt')}"><polygon class="ring" points="${ring(43)}"/><polygon class="ring" points="${ring(24)}"/>${D.keys.map((k, i) => { const a = (-90 + 36 * i) * Math.PI / 180, x = 50 + 43 * Math.cos(a), y = 50 + 43 * Math.sin(a), lx = 50 + 52 * Math.cos(a), ly = 50 + 50 * Math.sin(a) + 1.2; return `<line class="axis" x1="50" y1="50" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}"/><text class="${i === top ? 'top' : ''}" x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="${Math.abs(lx - 50) < 6 ? 'middle' : lx > 50 ? 'start' : 'end'}">${t('k' + k)} ${w.p[i].toFixed(1)}</text>`; }).join('')}<polygon class="shape" points="${sig(w)}"/></svg>`;
      unit.innerHTML = `<div class="unit-card"><div class="unit-top"><svg viewBox="0 0 100 100" aria-hidden="true"><polygon class="ring" points="${ring(46)}"/><polygon class="shape" points="${sig(w, 6, 40)}"/></svg><div><p class="unit-role">${t('r' + w.role)}</p><p class="unit-sub">${t('k' + w.domain)} → ${t('r' + w.role)} · ${t('basic')} <b>${w.action}</b></p></div></div><div class="stats">${Object.keys(RANGE).map((k) => `<div><span>${k.toUpperCase()}</span><i style="--v:${clamp((w.s[k] - RANGE[k][0]) / (RANGE[k][1] - RANGE[k][0]), 0.04).toFixed(3)}"></i><b>${w.s[k].toFixed(k === 'mob' ? 2 : 1)}</b></div>`).join('')}</div></div>`;
      netL.innerHTML = '<svg class="mini" aria-hidden="true"></svg><p class="mini-tally"></p>';
      mini = drawMini($('svg', netL));
      paint();
    };
    const paint = () => {
      stage.dataset.step = step; dots.forEach((d, i) => d.classList.toggle('on', i < step));
      if (tag) tag.innerHTML = `<b>${String(step).padStart(2, '0')}</b> / 05 · ${t('s' + step)}`;
      steps.forEach((li, i) => li.classList.toggle('on', i + 1 === step));
      if (!mini) return;
      const svgEl = $('svg', netL); $$('.u,.halo', svgEl).forEach((e) => e.remove());
      const own = step >= 5 ? spread(4) : new Map();
      mini.N.forEach((el, id) => { el.setAttribute('class', 'n ' + (own.get(id) || (D.start.A.includes(id) && step >= 5 ? 'a' : D.start.B.includes(id) && step >= 5 ? 'b' : ''))); });
      const me = D.start.A[cur % D.start.A.length];
      mini.E.forEach((el, k) => { const [a, b] = k.split('-').map(Number); const oa = own.get(a), ob = own.get(b); el.setAttribute('class', 'e ' + (step >= 5 && oa && oa === ob ? oa : step === 4 && (a === me || b === me) ? 'a' : '')); });
      D.start.A.forEach((id) => mini.unit(id, id === me ? 'me' : 'a')); D.start.B.forEach((id) => mini.unit(id, 'b'));
      mini.halo(me);
      const a = [...own.values()].filter((v) => v === 'a').length, b = [...own.values()].filter((v) => v === 'b').length;
      $('.mini-tally', netL).innerHTML = step >= 5 ? `<b class="a">A ${a}/50</b><b class="b">B ${b}/50</b><span>${t('schematic')}</span>` : `<span>${t('boardReal')}</span>`;
    };
    picks.forEach((b, i) => b.addEventListener('click', () => { cur = i; picks.forEach((p, j) => p.setAttribute('aria-pressed', String(i === j))); render(); }));
    render();
    if ('IntersectionObserver' in window) {
      const io = new IntersectionObserver((es) => { for (const e of es) if (e.isIntersecting) { step = Number(e.target.dataset.step); paint(); } }, { rootMargin: '-48% 0px -48% 0px' });
      steps.forEach((s) => io.observe(s));
    }
  });

  // ---- 03 Board: read the network, march for territory, cut a link
  const boardEl = $('.board');
  if (boardEl && D) idle(() => {
    const read = $('.read-main p'), readT = $('.read-main b'), modeBtns = $$('.seg button'), frameEl = $('.board-frame');
    const tallyA = $('[data-tally="a"]'), tallyB = $('[data-tally="b"]'), tallyNote = $('.tally small');
    boardEl.setAttribute('viewBox', '-21 -11 42 22');
    const E = new Map(), G = new Map();
    for (const [a, b] of D.edges) {
      const [x1, y1] = P.get(a), [x2, y2] = P.get(b), k = a + '-' + b;
      const line = svg('line', { class: 'e', x1, y1, x2, y2 }, boardEl), hit = svg('line', { class: 'e-hit', x1, y1, x2, y2, 'data-edge': k }, boardEl);
      E.set(k, { line, hit, a, b, cut: false });
    }
    for (const [id] of D.nodes) {
      const [cx, cy] = P.get(id);
      const g = svg('g', { class: 'node', 'data-node': id, tabindex: -1, role: 'button', 'aria-label': nid(id) }, boardEl);
      svg('polygon', { class: 'n', points: oct(cx, cy, 1.02, 0.56) }, g); svg('polygon', { class: 'ring', points: oct(cx, cy, 1.3, 0.74) }, g);
      svg('circle', { class: 'n-hit', cx, cy, r: 1.25 }, g);
      const tx = svg('text', { x: cx, y: cy + 1.55, 'font-size': 0.62 }, g); tx.textContent = nid(id); tx.style.fontSize = '0.62px';
      G.set(id, g);
    }
    const unitLayer = svg('g', {}, boardEl);
    let mode = 'read', sel = null, own, units, picked = null, kb = D.start.A[0];
    const live = (a, b) => { const e = E.get(a + '-' + b) || E.get(b + '-' + a); return e && !e.cut; };
    const nb = (id) => ADJ.get(id).filter((m) => live(id, m));
    const reset = () => { own = new Map(); units = [...D.start.A.map((n) => ({ team: 'a', at: n })), ...D.start.B.map((n) => ({ team: 'b', at: n }))]; E.forEach((e) => { e.cut = false; }); sel = null; picked = null; };
    const comp = (start) => { const seen = new Set([start]), q = [start]; while (q.length) { const n = q.shift(); for (const m of nb(n)) if (!seen.has(m)) { seen.add(m); q.push(m); } } return seen; };
    const draw = () => {
      const near = new Set(), far = new Set();
      if (mode === 'read' && sel != null) { nb(sel).forEach((m) => near.add(m)); near.forEach((m) => nb(m).forEach((k) => { if (k !== sel && !near.has(k)) far.add(k); })); }
      if (mode === 'march' && picked != null) nb(units[picked].at).filter((m) => !units.some((u) => u.at === m)).forEach((m) => near.add(m));
      const isolated = new Set();
      if (mode === 'cut') units.forEach((u) => { const c = comp(u.at); if (!units.some((o) => o !== u && o.team === u.team && c.has(o.at))) isolated.add(u.at); });
      G.forEach((g, id) => {
        const o = own.get(id);
        g.setAttribute('class', 'node' + (o ? ' ' + o : '') + (id === sel && mode === 'read' ? ' sel' : '') + (near.has(id) ? ' near' : '') + (far.has(id) ? ' far' : '') + (mode === 'read' && sel != null && id !== sel && !near.has(id) && !far.has(id) ? ' dim' : '') + (isolated.has(id) ? ' lost' : '') + (id === kb && boardEl.matches(':focus-within') ? ' kb' : ''));
        g.setAttribute('tabindex', id === kb ? 0 : -1);
      });
      E.forEach((e) => {
        const oa = own.get(e.a), ob = own.get(e.b);
        e.line.setAttribute('class', 'e' + (e.cut ? ' cut' : mode === 'read' && sel != null ? ((e.a === sel || e.b === sel) ? ' hot' : ' dim') : oa && oa === ob ? ' ' + oa : ''));
      });
      unitLayer.innerHTML = '';
      units.forEach((u, i) => { const [cx, cy] = P.get(u.at); const c = svg('circle', { class: 'unit ' + u.team, cx, cy: cy - 0.12, r: i === picked ? 0.62 : 0.46 }, unitLayer); if (i === picked) c.style.stroke = 'var(--amber)'; });
      const a = [...own.values()].filter((v) => v === 'a').length, b = [...own.values()].filter((v) => v === 'b').length;
      for (const [el, n] of [[tallyA, a], [tallyB, b]]) { $('i', el).style.setProperty('--v', (n / 50).toFixed(3)); $('b', el).textContent = n + ' / 50'; }
      const met = a >= 23 && a - b >= 4;
      tallyNote.textContent = met ? t('tallyMet') : t('tallyRule');
      tallyNote.style.color = met ? 'var(--amber)' : '';
      if (mode === 'cut') { const ia = units.filter((u) => u.team === 'a' && isolated.has(u.at)).length, ib = units.filter((u) => u.team === 'b' && isolated.has(u.at)).length, cuts = [...E.values()].filter((e) => e.cut).length; say(t('cutT'), cuts ? t('cutState', { cuts, a: ia, b: ib }) : t('cutHint')); }
    };
    const say = (title, text) => { readT.textContent = title; read.textContent = text; };
    const enemyMove = () => { // the other side marches too: toward the nearest node it does not own
      const mine = units.filter((u) => u.team === 'b'); let best = null;
      for (const u of mine) for (const m of nb(u.at)) { if (units.some((o) => o.at === m)) continue; const score = (own.get(m) === 'b' ? 0 : own.get(m) === 'a' ? 3 : 2) - Math.hypot(...P.get(m)) * 0.08 + Math.random() * 0.4; if (!best || score > best.score) best = { u, m, score }; }
      if (best) { best.u.at = best.m; own.set(best.m, 'b'); }
    };
    const act = (id) => {
      kb = id;
      if (mode === 'read') { sel = sel === id ? null : id; if (sel == null) say(t('readT'), t('readHint')); else { const n1 = nb(id), n2 = new Set(); n1.forEach((m) => nb(m).forEach((k) => { if (k !== id && !n1.includes(k)) n2.add(k); })); say(nid(id), t('readNode', { links: n1.length, two: n1.length + n2.size })); } }
      else if (mode === 'march') {
        const ui = units.findIndex((u) => u.at === id);
        if (ui >= 0 && units[ui].team === 'a') { picked = picked === ui ? null : ui; say(t('marchT'), picked == null ? t('marchHint') : t('marchPicked')); }
        else if (picked != null && nb(units[picked].at).includes(id) && ui < 0) { const was = own.get(id); units[picked].at = id; own.set(id, 'a'); const e = E.get(units[picked].at + '-' + id); enemyMove(); say(t('marchT'), was === 'b' ? t('marchFlip', { n: nid(id) }) : t('marchClaim', { n: nid(id) })); }
        else say(t('marchT'), picked == null ? t('marchHint') : t('marchBad'));
      }
      draw();
    };
    const setMode = (m) => { mode = m; sel = null; picked = null; modeBtns.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.mode === m))); frameEl.dataset.mode = m; say(t(m + 'T'), t(m + 'Hint')); draw(); };
    reset();
    boardEl.addEventListener('click', (e) => {
      const g = e.target.closest('g.node'); if (g) return act(Number(g.dataset.node));
      const h = e.target.closest('.e-hit'); if (h && mode === 'cut') { const ed = E.get(h.dataset.edge); ed.cut = !ed.cut; if (!ed.cut) ed.line.classList.add('pulse'); draw(); }
    });
    boardEl.addEventListener('keydown', (e) => {
      const dir = { ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] }[e.key];
      if (dir) { e.preventDefault(); const [x, y] = P.get(kb); let best = null, bs = Infinity; for (const [id] of D.nodes) { if (id === kb) continue; const [px, py] = P.get(id), dx = px - x, dy = (py - y) * 2, along = dx * dir[0] + dy * dir[1]; if (along <= 0.2) continue; const off = Math.abs(dx * dir[1]) + Math.abs(dy * dir[0]), s = along + off * 2.2; if (s < bs) { bs = s; best = id; } } if (best != null) { kb = best; draw(); G.get(kb).focus(); } }
      else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); act(kb); }
      else if (e.key === 'Escape') { sel = null; picked = null; draw(); }
    });
    boardEl.addEventListener('focusin', (e) => { const g = e.target.closest('g.node'); if (g) { kb = Number(g.dataset.node); draw(); } });
    boardEl.addEventListener('focusout', () => requestAnimationFrame(draw));
    modeBtns.forEach((b) => b.addEventListener('click', () => setMode(b.dataset.mode)));
    $('[data-board-reset]')?.addEventListener('click', () => { reset(); setMode(mode); });
    $('.board-ui').hidden = false; $('.board-fallback')?.remove();
    setMode('read');
  });

  // ---- Posters of the films below the fold arrive when the reader gets near them
  const posters = $$('video[data-poster]');
  if ('IntersectionObserver' in window) { const po = new IntersectionObserver((es) => { for (const e of es) if (e.isIntersecting) { e.target.poster = e.target.dataset.poster; po.unobserve(e.target); } }, { rootMargin: '900px 0px' }); posters.forEach((v) => po.observe(v)); } else posters.forEach((v) => { v.poster = v.dataset.poster; });

  // ---- Films with an explicit play button (lazy: nothing is fetched before the click)
  $$('.screen[data-film]').forEach((s) => {
    const v = $('video', s), b = $('.play', s);
    b?.addEventListener('click', () => { for (const src of $$('source', v)) src.src = src.dataset.src; v.load(); v.controls = true; s.classList.add('is-on'); v.play().catch(() => {}); v.focus(); });
  });

  // ---- 04 Decisions: the text you are reading chooses the clip
  const player = $('.dec-player');
  if (player) {
    const items = $$('.dec-list li'), vids = $$('video', player), meta = $('.dec-meta b', player), bar = $('.dec-bar', player);
    let on = -1, visible = false;
    const show = (i) => {
      if (i === on) return; on = i;
      items.forEach((li, j) => li.classList.toggle('on', i === j));
      vids.forEach((v, j) => { if (j === i) { if (!v.dataset.loaded) { v.dataset.loaded = '1'; v.src = v.dataset.src; } v.classList.add('on'); if (visible && !reduce.matches) v.play().catch(() => {}); } else { v.classList.remove('on'); v.pause(); } });
      meta.textContent = items[i].dataset.label;
    };
    vids.forEach((v) => v.addEventListener('timeupdate', () => { if (v.classList.contains('on') && v.duration) bar.style.setProperty('--v', (v.currentTime / v.duration).toFixed(3)); }));
    if ('IntersectionObserver' in window) {
      const io = new IntersectionObserver((es) => { for (const e of es) if (e.isIntersecting) show(items.indexOf(e.target)); }, { rootMargin: '-50% 0px -49% 0px' });
      items.forEach((li) => io.observe(li));
      new IntersectionObserver(([e]) => { visible = e.isIntersecting; const v = vids[on]; if (!v) return; visible && !reduce.matches ? v.play().catch(() => {}) : v.pause(); }, { rootMargin: '200px 0px' }).observe(player);
      new IntersectionObserver(([e], o) => { if (e.isIntersecting) { if (on < 0) show(0); o.disconnect(); } }, { rootMargin: '600px 0px' }).observe(player);
    } else show(0);
    const tog = $('[data-dec-toggle]', player);
    tog?.addEventListener('click', () => { const v = vids[on]; if (!v) return; v.paused ? v.play().catch(() => {}) : v.pause(); });
  }

  // ---- 05 Gallery lightbox
  const lb = $('.lightbox');
  if (lb && lb.showModal) {
    const thumbs = $$('.gal button'), img = $('.lb-stage', lb).appendChild(Object.assign(new Image(), { width: 1920, height: 1080, alt: '' })), cap = $('.lb-bottom p', lb), count = $('.lb-count', lb);
    let i = 0, opener = null;
    const go = (n) => { i = (n + thumbs.length) % thumbs.length; const b = thumbs[i]; img.src = b.dataset.full; img.alt = $('img', b).alt; cap.textContent = b.dataset.caption; count.textContent = String(i + 1).padStart(2, '0') + ' / ' + String(thumbs.length).padStart(2, '0'); };
    thumbs.forEach((b, n) => b.addEventListener('click', () => { opener = b; go(n); lb.showModal(); }));
    $('[data-lb-prev]', lb).addEventListener('click', () => go(i - 1)); $('[data-lb-next]', lb).addEventListener('click', () => go(i + 1));
    $('[data-lb-close]', lb).addEventListener('click', () => lb.close());
    lb.addEventListener('click', (e) => { if (e.target === lb || e.target.classList.contains('lb-stage')) lb.close(); });
    lb.addEventListener('keydown', (e) => { if (e.key === 'ArrowLeft') go(i - 1); if (e.key === 'ArrowRight') go(i + 1); });
    lb.addEventListener('close', () => { img.removeAttribute('src'); opener?.focus(); });
  }

  // ---- 07 Lineage: links between the cards are measured, not guessed
  const lin = $('.lineage');
  if (lin && linSvg) {
    const drawLin = () => {
      linSvg.innerHTML = ''; if (getComputedStyle(linSvg).display === 'none') return;
      const r0 = lin.getBoundingClientRect(), box = (s) => { const r = $(s, lin).getBoundingClientRect(); return { l: r.left - r0.left, r: r.right - r0.left, t: r.top - r0.top, b: r.bottom - r0.top, cx: r.left - r0.left + r.width / 2, cy: r.top - r0.top + r.height / 2 }; };
      linSvg.setAttribute('viewBox', `0 0 ${r0.width} ${r0.height}`);
      const org = box('.org'), tm = box('.tm'), sot = box('.sot'), here = box('.here');
      for (const c of [tm, sot, here]) svg('path', { d: `M${org.cx} ${org.b} V${(org.b + c.t) / 2} H${c.cx} V${c.t}` }, linSvg);
      svg('path', { class: 'flow', pathLength: 1, d: `M${tm.r} ${tm.cy} H${sot.l}` }, linSvg);
      svg('path', { class: 'flow', pathLength: 1, d: `M${sot.r} ${sot.cy} H${here.l}` }, linSvg);
    };
    drawLin(); addEventListener('resize', drawLin); document.fonts?.ready.then(drawLin);
  }
})();
