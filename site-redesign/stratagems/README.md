# Stratagems Atlas redesign

The audit of the previous page is in [`AUDIT.md`](AUDIT.md). This file covers the new information architecture, the design system, motion, the touch layout, and how the page is built.

Direction: an interactive editorial publication, a strategy atlas read like an archive document. It draws on paper, sumi ink, a red seal, map grids and annotation. It avoids dashboards, glass, neon and decorative motion. All research text, data, URLs, the language switch and the search behaviour are kept.

## Information architecture

| # | Section | Content | Previously |
| --- | --- | --- | --- |
| — | Masthead | Jinn Project home (language-aware), page name, Atlas / Categories / Concept / Notes, 日本語 / EN | Same items, dark bar |
| — | Hero | Kicker, title, lead, two actions, the three original figures, and a vertical 三十六計 title slip with a seal | Large outline headline |
| 01 | Atlas `#atlas` | Search and filters, board / list, the reader for the selected stratagem, a touch stepper | Search bar + tree/list + detail box |
| 02 | Categories `#categories` | The six cognitive groups → 22 sub-groups → members (the cognitive tree) | 36 one-item category cards |
| 03 | Concept `#concept` | Unchanged text | Same, before the atlas |
| 04 | Notes `#notes` | Unchanged text | Same |

### The board

- **The 36 stratagems as a 6 × 6 field.** The columns are the traditional six chapters (六套: 勝戦計, 敵戦計, 攻戦計, 混戦計, 併戦計, 敗戦計). Within a column, entries run in classical order. A stratagem's position on the board is therefore its place in the text.
- **The board is the persistent index.** It stays beside the reader on desktop, and it is one Tab stop with arrow-key movement.
- **Selection is a vermilion seal on the number.** Lines then draw from the selected cell:
  - solid vermilion to the stratagems it lists as related;
  - dotted indigo from the stratagems that list it.
- **Filters lift the matching cells.** Non-matches are hatched but stay readable at AA contrast, so the map shows where the matches sit.
- **List view** rearranges the same 36 links into rows with full names and cognitive categories, using a FLIP transition. In list view, filters hide non-matches.

### Filters

- **Search** uses the same fields and rules as before. Verified for 10 queries in each language against the old algorithm.
- **Chapter** (new, from the traditional grouping).
- **Cognitive group** (new, from the existing cognitive tree).
- **Cognitive category** (the original 36-value `<select>`).
- **Clear filters**, a badge with the number of active facets, and a live result count ("4 of 36 stratagems").
- As before, the first match opens when the current stratagem is filtered out.

### The entry (reader)

Every entry has the same hierarchy:

1. **Position rail** (36 ticks in six groups, the current chapter in vermilion), chapter, `07 / 36`, and *Copy link*.
2. **Number, Chinese title, translated title**, plus the reading (JA) and the cognitive category.
3. **The summary as a standfirst.**
4. **Cognitive principle** (認知原理) as a pull quote with a seal-red rule.
5. **Interpretation** (解釈) as paragraphs. The author's line breaks are now kept; before, they collapsed into one run-on paragraph.
6. **Cognitive reading:**
   - a three-node chain, stratagem → bias → behavioural reading;
   - related biases;
   - the cognitive process as a numbered flow;
   - related concepts;
   - the cognitive-tree placements, linked to `#categories`.
7. **Modern example**, the note essay (opens in a new tab) and references.
8. **Related stratagems**, and the stratagems that list this one. Both lists were already in the data but never shown.
9. **Previous / next.** Inside a filtered set, these step through the matches.

### Deep links

- **Format:** `#stratagem-N`, combined with the existing `?lang=` (for example `?lang=en#stratagem-32`).
- Selecting an entry updates the hash with `replaceState`, so stepping through 36 entries does not fill the history.
- Changing the hash by hand, or with Back/Forward, selects the entry.
- An unknown hash falls back to #1.
- `document.title` names the open stratagem.

## Design system (`style.css`)

| Token | Value | Use |
| --- | --- | --- |
| `--paper` / `--paper-raised` / `--paper-sunk` | `#f3eee4` / `#faf7f0` / `#e8e1d2` | Ground, raised cards, chapter headers |
| `--ink` / `--ink-2` / `--ink-3` | `#1b1913` / `#4a453b` / `#686153` | Text: 15.2 / 8.2 / 5.3 : 1 on paper (≥ 4.7 : 1 on every surface) |
| `--rule` / `--rule-strong` | `#cdc4b1` / `#9c917b` | Hairlines (non-text) |
| `--shu` / `--shu-deep` | `#b3341d` / `#962914` | Seal red: selection, outgoing relations, kickers (5.3 / 6.9 : 1) |
| `--ai` | `#2b4c66` | Indigo: the cognitive layer, incoming relations, links (7.8 : 1) |
| `--focus` | `#0b57a4` | 3 px focus ring (6.2 : 1) |

- **Type:**
  - *Jinn Atlas Han:* a 28 KB subset of Noto Serif JP SemiBold covering only the 36 names, the chapter names and 三十六計. It makes every Chinese title look the same on every OS.
  - *Instrument Serif* (Latin display), shared with the top page.
  - *IBM Plex Mono* for numbers and metadata only.
  - Body text uses the system sans: San Francisco, Segoe UI and Roboto for Latin, and the reader's Gothic for Japanese. Inter was left out to keep the first render light.
  - Japanese display text uses Hiragino/Yu Mincho.
- **Texture:** a 0.4 KB SVG noise tile for the paper grain.
- **Layout:**
  - ≥ 1100 px: a sticky board panel (46 %) beside the reader (54 %).
  - 700–1099 px: board above reader, with a bottom stepper.
  - < 700 px: the touch layout below.
- **Light only, by choice:** the page commits to the paper look and sets `color-scheme: light`.

## Motion

All motion is under 1 s, never blocks reading or scrolling, and is fully disabled with `prefers-reduced-motion`:

- **Ink wipe:** the Chinese title is revealed by a masked gradient (`@property --wipe`) when an entry changes.
- **Rise:** the summary and first sections rise 10 px.
- **Chain:** the arrows grow left to right (top to bottom on phones).
- **Seal stamp:** the selected cell's number is stamped (scale and rotate, 0.34 s).
- **Relation lines** draw in with `stroke-dashoffset`, staggered by 70 ms. Incoming lines fade in.
- **Position rail:** the current tick grows.
- **Board ↔ list:** a FLIP transition moves the same 36 elements.

## Touch layout (< 700 px)

- **Board:** six columns of vertical names (縦書き), so all 36 fit on one screen. Each target is about 59 × 104 px.
- **Chapter headers** show the numeral only. The full name stays in the heading for screen readers.
- **Filters** collapse into a disclosure (`<details>`). Search stays visible.
- **Opening an entry:** tapping a cell scrolls to the entry. A sticky stepper (‹ 07 / 36 無中生有 ›) appears while the reader is on screen. Its centre button returns to the board.
- **The chain diagram** stacks vertically.
- **Page height (390 px, JA):** about 10,000 px, down from 17,200.

## Accessibility

- **Keyboard:**
  - The skip link goes to the atlas.
  - The board is one Tab stop: ↑↓ move within a chapter, ←→ across chapters, Home/End jump.
  - Enter opens the stratagem and moves focus to its title.
- **Landmarks and labels:** no headings inside the navigation list; every field has a visible label; the result count is a live status; copying a link is announced.
- **Languages:** names carry `lang="ja"` in English mode, and translated names carry `lang="en"` in Japanese mode.
- **Without JavaScript:**
  - the board, the categories and a compact version of all 36 entries (summary + note link, in a `<noscript>`) are readable;
  - the board links jump to them.
- **Find-in-page:** hidden entries use `hidden="until-found"`, so the browser's find can reveal any entry, and the Atlas then selects it.

## How it is built

```text
docs/research/stratagems/
├── index.html        generated — do not edit by hand
├── stratagems.js     data: 36 records + cognitive tree (records unchanged; app code moved out)
├── stratagems-en.js  data: English records (unchanged)
├── i18n.js           UI strings JA/EN, chapter labels, language helpers
├── atlas.js          the interactive layer
├── style.css         design system
└── fonts/            Jinn Atlas Han subset (+ glyph list) and its OFL licence
docs/tools/build-stratagems.mjs          renders index.html from the data and i18n.js
site-redesign/tools/build_stratagems_font.py   rebuilds the font subset
tests/stratagems-atlas.test.mjs          8 regression tests (also run in Site CI)
```

```sh
node docs/tools/build-stratagems.mjs   # after editing data, i18n.js or the template
node --test tests/*.mjs
```

### Performance

The previous page was light: 162 KiB, mobile Lighthouse 97–98. The redesign keeps it there:

- **No flash of the wrong language.** The board, categories and text are pre-rendered, so the first paint needs no JavaScript.
- **Scripts load after first paint.** The 150 KB of data and app code is requested once the first paint is on screen (paint timing, with the `load` event as fallback), so it never competes with the stylesheet and fonts.
- **One display face preloaded:** the face the hero uses in the current language (Instrument Serif for EN, the Han subset for JA). The other faces use `swap` or `optional`.
- **Below-the-fold sections are laid out lazily** with `content-visibility: auto`: the categories and essays everywhere, and the whole atlas on phones.
- **One entry at load.** The reader renders only the selected entry. The other 35 are rendered on the first interaction (including Ctrl/Cmd+F, so find-in-page reaches them), which keeps the initial DOM near 1,300 nodes.

### Language pairs

The page prints every UI string as a JA/EN pair of spans. An inline head script sets `<html lang>` from `?lang=`, then `localStorage`, then the browser language, before first paint. That is the same order as before. CSS shows the pair that matches, so there is no flash of the wrong language. Only `aria-label`s and `<option>` text are swapped by script.
