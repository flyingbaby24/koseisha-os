# Jinn Project site redesign (2026-10)

Audit findings: [AUDIT.md](AUDIT.md). This file covers the information
architecture, the design system, how to build, and verification results.

## Concept — Ink & Signal

Jinn Project's own assets are hand-made (the ink cherub mark, Kunizukuri's sumi-ink
landscape, Mandalizm's painted output) and its subject is structure
(semantic maps, formations, systems). The design keeps both:

- **Ink**: warm paper text on sumi-ink surfaces, an editorial serif, the cherub
  mark at full visibility, and a vermilion *shu* seal colour used only for brand
  marks (section indexes, the hero emphasis, active state).
- **Signal**: hairline rules, mono labels and one cyan for anything interactive.
- **The field**: the hero plots the seven projects across the four domains of
  the existing motto — *Thought / Body / Material / System* — with lines for
  real shared data, mechanics or material. It is navigation, not decoration:
  each node jumps to the project's card.

## Information architecture

| # | Section (`id`) | Purpose | Replaces |
| - | --- | --- | --- |
| — | Hero (`#top`) | Who we are in one sentence, two CTAs, project field, "Now" strip of live releases | 5-slide auto carousel |
| 01 | Flagship (`#source-of-thought`) | Source of Thought: capture, key facts, game-site CTA, gallery/roadmap/blog | Flagship + carousel slide 1 |
| 02 | Work (`#projects`) | All 7 projects, uniform cards with status, filter (Games / Research / Apps & products) | "Five entry points" + orphan card |
| 03 | Research (`#research`, `#publications`) | Corpus → ThoughtMap → expressions loop; ORCID/GitHub/ThoughtMap intro | Ecosystem + Research + Publications (3 sections) |
| 04 | About (`#about`) | Four domains, three principles, verifiable figures | *(new)* + animated stats |
| 05 | Log (`#development`) | Latest 4 dev articles, rendered in HTML | JS-injected list |
| 06 | Contact (`#contact`) | Linktree, Patreon, GitHub | Footer-only links |

Navigation: 10 mixed items → 5 in-page items (Work, Research, About, Log, Contact)
plus a language switch (EN / 日本語) that keeps the reader's `#section`.
Every anchor that sub-pages link to (`#top`, `#projects`, `#research`,
`#publications`, `#contact`) is kept and covered by a test.

Removed on purpose: "65% Source of Thought" (no unit or meaning) and
"1,200+ GitHub commits" (not verifiable from the repository). Remaining figures
come from content already published on the site.

## Design system — `docs/assets/site.css`

| Token | Value | Use |
| --- | --- | --- |
| `--ink-0/1/2` | `#080a0d` `#0e1216` `#151a20` | page, raised, card |
| `--paper / -2 / -3` | `#ece8df` `#b9b4a9` `#948f86` | text; 16.2 / 9.6 / 6.2 : 1 on ink-0 |
| `--rule / --rule-strong` | `#252c34` / `#5a636d` | hairlines / control borders (≥3:1) |
| `--signal` | `#5fdcf2` | links, focus ring, interactive lines |
| `--shu` | `#ff6b4a` | brand marks only (7.0:1) |
| `--live / --alpha` | `#6fdc8c` / `#f0b85a` | project status |
| `--serif` | Instrument Serif → Hiragino/Yu Mincho | display |
| `--sans` | Inter (variable) → Hiragino Sans/Noto Sans JP | body, UI |
| `--mono` | IBM Plex Mono 500 | labels, metadata |

Components: `.kicker` (+ `.index`, `.seal`), `.btn` / `.btn-primary`, `.status`
(`-live`, `-alpha`, `-dev`), `.project-card`, `.loop`, `.row-links`, `.facts`,
`.domains`, `.figures`, `.log-list`, `.contact-grid`.

Fonts are self-hosted Latin subsets (≈106 KB total, SIL OFL; licences in
`docs/assets/fonts/`). Japanese uses system Mincho/Gothic stacks, with
`word-break: auto-phrase` for natural line breaks.

Motion is progressive: content is visible without JavaScript; only sections
below the fold fade in, field lines draw once, and `prefers-reduced-motion`
disables all of it.

## Building

```sh
# 1. Edit docs/index.html (English source of truth)
# 2. Regenerate both pages (SEO head + Japanese page)
node docs/tools/generate-index-ja.mjs
# 3. Test
node --test tests/*.mjs
```

The generator fails if any English string it translates no longer exists, so
the Japanese page cannot silently drift. CI (`.github/workflows/site-ci.yml`)
checks the committed pages equal the generator output and runs the tests.

Derived images: `python3 site-redesign/tools/build_assets.py` (Pillow) writes
WebP variants, the light ink mark, favicon and touch icons from the originals.
The social card is rendered from `tools/og-card.html` by `tools/og-card.mjs`
(Playwright).

## Shared stylesheet changes (all 28 sub-pages)

`docs/style.css` gained one appended block:
- the ink logo is inverted so it is visible on the dark header (it was invisible);
- nav / footer micro-labels raised to legible size and AA contrast;
- visible `:focus-visible` ring; `.sr-only` utility;
- the ten-item sub-page navigation switches to the menu button below 1000 px
  (it was clipped between 781 and 1000 px) and no longer collides with the logo
  or the language switch at 1024–1180 px.

`research/stratagems/index.html`: search field and category select now have labels.

## Verification (local static server, Chromium, Lighthouse 12, axe-core 4)

| | Before | After |
| --- | --- | --- |
| Lighthouse mobile — Perf / A11y / BP / SEO | 88 / 96 / 96 / 100 | 98 / 100 / 96* / 100 |
| Mobile LCP / TBT / CLS | 3.4 s / 0 ms / 0 | 2.2 s / 0 ms / 0.001 |
| Lighthouse desktop — Perf / A11y | 100 / 96 | 100 / 100 |
| Page weight (mobile) | 529 KiB | 242 KiB |
| axe violations, top pages (EN/JA × desktop/mobile) | 9–10 each | 0 |
| axe violations, 8 sampled sub-pages | 1–5 each | 0 (except one pre-existing heading-order on roadmap) |
| Tests | 14 | 21 (all pass) |

\* The only Best-Practices deduction is the Cloudflare analytics beacon, which
the test sandbox cannot reach.

Browser checks: no horizontal overflow at 390 / 820 / 1440 px; keyboard order,
skip link, mobile menu (focus moves in, Esc returns focus, scroll lock), filter
state announced via `role=status`, field links reveal filtered cards, language
switch keeps `#hash`, page fully readable with JavaScript disabled,
reduced-motion mode, all targets ≥ 24 px except inline text links.

## Known gaps / next steps

- Sub-pages still use the previous visual language; only shared fixes were
  applied. Migrating them to `assets/site.css` is the next phase.
- `research/source-of-thought/roadmap*.html` jumps from `h1` to `h3`.
- No real ThoughtMap or Stratagems screenshot exists in the repo; their cards use
  CSS illustrations. Replace with captures when available.
- Grounding Sole has no public page; its card is intentionally not a link.
- Mobile LCP in the lab is bounded by font loading on a throttled connection;
  consider `size-adjust` fallback metrics if field data shows it matters.
