// Jinn Project top page. Progressive enhancement only: every section is
// readable and every link works before (or without) this file.
(() => {
  const root = document.documentElement;
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');

  // Header: solid background once the page scrolls.
  const header = document.querySelector('[data-header]');
  const onScroll = () => header?.classList.toggle('is-scrolled', scrollY > 16);
  requestAnimationFrame(onScroll);
  addEventListener('scroll', onScroll, { passive: true });

  // Mobile navigation sheet.
  const nav = document.getElementById('site-nav');
  const toggle = document.querySelector('.nav-toggle');
  const setOpen = (open, { focusToggle = false } = {}) => {
    nav.classList.toggle('is-open', open);
    header.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    root.style.overflow = open ? 'hidden' : '';
    if (open) nav.querySelector('a')?.focus();
    else if (focusToggle) toggle.focus();
  };
  if (nav && toggle) {
    toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'));
    nav.addEventListener('click', (event) => { if (event.target.closest('a')) setOpen(false); });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && nav.classList.contains('is-open')) setOpen(false, { focusToggle: true });
    });
    // Keep keyboard focus inside header while the sheet is open.
    header.addEventListener('focusout', (event) => {
      if (nav.classList.contains('is-open') && !header.contains(event.relatedTarget) && event.relatedTarget) setOpen(false);
    });
    matchMedia('(min-width: 900px)').addEventListener('change', (e) => { if (e.matches) setOpen(false); });
  }

  // Current section in the main navigation.
  const navLinks = [...document.querySelectorAll('.site-nav a[href^="#"]')];
  const byId = new Map(navLinks.map((a) => [a.hash.slice(1), a]));
  const sections = [...byId.keys()].map((id) => document.getElementById(id)).filter(Boolean);
  if ('IntersectionObserver' in window && sections.length) {
    const spy = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        navLinks.forEach((a) => a.removeAttribute('aria-current'));
        byId.get(entry.target.id)?.setAttribute('aria-current', 'location');
      }
    }, { rootMargin: '-40% 0px -55% 0px' });
    sections.forEach((s) => spy.observe(s));
  }

  // Work index filter.
  const filters = document.querySelector('.filters');
  if (filters) {
    const buttons = [...filters.querySelectorAll('button[data-filter]')];
    const items = [...document.querySelectorAll('.work-item')];
    const status = filters.querySelector('.filter-status');
    const template = filters.dataset.statusTemplate || '{n} / {total}';
    const apply = (kind) => {
      let shown = 0;
      for (const item of items) {
        const match = kind === 'all' || item.dataset.kind === kind;
        item.hidden = !match;
        if (match) shown += 1;
      }
      buttons.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.filter === kind)));
      status.textContent = kind === 'all' ? '' : template.replace('{n}', shown).replace('{total}', items.length);
    };
    buttons.forEach((b) => b.addEventListener('click', () => apply(b.dataset.filter)));
    filters.hidden = false;
  }

  // Field nodes link to project cards: make sure a filtered-out card is shown.
  document.querySelectorAll('.field-nodes a, .now a[href^="#"]').forEach((a) => {
    a.addEventListener('click', () => {
      const target = document.querySelector(a.hash);
      const item = target?.closest('.work-item');
      if (item?.hidden) filters?.querySelector('[data-filter="all"]')?.click();
    });
  });

  // Language switch keeps the reader's place.
  document.querySelectorAll('.lang-switch a, .footer-nav a[hreflang]').forEach((a) => {
    a.addEventListener('click', (event) => {
      if (!location.hash) return;
      event.preventDefault();
      const url = new URL(a.href, location.href);
      url.hash = location.hash;
      location.href = url.href;
    });
  });

  // Reveal sections below the fold. Elements already on screen are never hidden.
  if (!reduceMotion.matches && 'IntersectionObserver' in window) {
    const targets = document.querySelectorAll('.section-head, .feature-grid, .work-grid, .loop, .open-work, .domains, .principles, .figures, .log-list, .contact-grid');
    const reveal = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add('is-revealed');
        entry.target.classList.remove('is-pending');
        reveal.unobserve(entry.target);
      }
    }, { rootMargin: '0px 0px -8% 0px' });
    // Measure everything first, then write, so setup costs one layout.
    const below = [...targets].filter((el) => el.getBoundingClientRect().top > innerHeight);
    for (const el of below) {
      el.classList.add('is-pending');
      reveal.observe(el);
    }
  }
})();
