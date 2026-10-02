# Jinn Project official site — audit (before redesign)

Scope: `docs/index.html` and `docs/index-ja.html` (www.jinn-project.com top pages),
plus the shared `docs/style.css` that 28 sub-pages also load.
Measured on commit `efe653a` with a local static server, Chromium 1194,
axe-core 4, Lighthouse 12 (Google Fonts are unreachable from the test sandbox,
so font cost is under-reported in the "before" numbers).

## Baseline numbers

| Check | Mobile | Desktop |
| --- | --- | --- |
| Lighthouse Performance | 88 (FCP 2.0 s, LCP 3.4 s, SI 4.0 s) | 100 |
| Lighthouse Accessibility | 96 | 96 |
| Lighthouse Best Practices | 96 (console 404: no favicon) | 96 |
| Lighthouse SEO | 100 | 100 |
| axe-core violations | color-contrast ×10 | color-contrast ×9 |
| Page weight | 529 KiB | 671 KiB |

## Findings

### Brand identity
1. **The logo is invisible.** `images/logo.png` is black ink on transparency;
   `.logo img{filter:grayscale(1) brightness(2)}` keeps black black, so on the
   `#070b10` header the mark disappears on every page that shares `style.css`.
2. The visual language (neon cyan, outlined display type, HUD grids) is the
   generic "dark tech" template. The project's genuinely distinctive assets —
   the hand-drawn ink cherub, the ink-painted Kunizukuri landscape, Mandalizm's
   watercolour output, the motto *Thought / Body / Material / System* — are
   either invisible or buried in the footer.
3. There is no statement of what Jinn Project *is*: no About, no principles.

### Information architecture
4. Navigation has 10 peer items mixing in-page anchors, product pages and an
   external link, set in 9.8 px uppercase mono. Collapses to 0.55 rem at 1000 px.
5. The hero is a 5-slide auto-rotating carousel: 4/5 of the hero content is
   hidden at any time; on mobile the visuals are hidden and the slide tabs
   show only "01…05" with no labels.
6. ThoughtMap appears in 4 sections, Source of Thought in 5. "Ecosystem",
   "Research" and "Publications" repeat the same idea three times.
7. Project grid: 4 cards + 1 orphaned, differently-styled Kunizukuri card;
   status ("coming soon", "public alpha", "playable") is styled inconsistently.
8. Stats animate up from **0**; without JS or before scrolling they read "0".
   "65% Source of Thought" has no unit or meaning; "1,200+ GitHub commits" is
   not verifiable from the repository.
9. `#contact` is the footer and contains no contact route except Linktree/Patreon.

### UX / mobile
10. All sections start at `opacity:0` (`.reveal`) and depend on an
    IntersectionObserver; no-JS, failed JS or some crawlers get blank sections.
11. "Latest development" is injected by JS, so it is empty without JS and
    invisible to non-rendering crawlers.
12. Parallax tilt on pointer move on large cards.

### Accessibility
13. Contrast failures on micro labels (`#667d86` on `#0c1219`, 4.33:1 at 9.3 px).
14. Carousel uses `role=tablist` without `tabpanel`, `aria-controls`, or arrow
    key support; auto-rotation every 6.5 s.
15. Many labels at 0.53–0.62 rem (8.5–10 px).
16. Language switch is labelled "JP" with an emoji glyph; no visible focus style
    beyond the browser default on dark backgrounds.

### SEO
17. Canonical is `/index.html` rather than `/`; no `og:image` (but
    `twitter:card=summary_large_image`); no structured data; no `robots.txt`;
    no favicon.
18. `tools/generate-index-ja.mjs` is out of sync with the committed EN page
    (running it changes the meta description), and its dictionary replacement
    silently ignores strings that no longer exist.

### Performance
19. Google Fonts loaded via CSS `@import` → render-blocking chain
    (HTML → style.css → fonts CSS → woff2), 8 font files.
20. `logo.png` (145 KB, 500×500) is preloaded to render at 34×34.
21. Hero/feature screenshots are 1280 px JPEGs with no responsive variants;
    off-screen carousel images load eagerly.
