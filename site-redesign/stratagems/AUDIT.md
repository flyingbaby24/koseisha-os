# Stratagems Atlas: audit of the current page

Page: `docs/research/stratagems/` (https://www.jinn-project.com/research/stratagems/).
Audited on `main` at `e91ffbd` with a local static server (no compression),
Chromium 1194, Lighthouse 12 and axe-core 4.

## Files and dependencies

| File | Size | Role |
| --- | --- | --- |
| `index.html` | 6 KB | Shell. Static text in Japanese, replaced by JS through `data-i18n` keys. |
| `style.css` | 13 KB | Page-only stylesheet. Dark theme, gold accent, system fonts. |
| `stratagems.js` | 109 KB | The 36 Japanese records **and** the whole app (lines 2959–3424) **and** the cognitive tree. |
| `stratagems-en.js` | 21 KB | English translations of the 36 records and the cognitive tree. |
| `i18n.js` | 6 KB | UI strings (JA/EN) and language detection (`?lang=` → `localStorage` → browser). |
| `README.md` | 1 KB | Outdated install note. |

- **Self-contained.** The page loads no shared CSS or JS (`docs/style.css`, `docs/i18n/*`, `docs/assets/*`), so a redesign cannot regress other pages through shared files.
- **No other page loads its scripts or data.**
- **Inbound links** from 27 pages use only `research/stratagems/`, `research/stratagems/?lang=en` and `?lang=ja` (the top pages). These URLs must keep working. No inbound link uses a fragment.
- **Tests:** no existing test covers the page.

## Data model (unchanged by the redesign)

- **36 Japanese records** in traditional order (1 瞞天過海 … 36 走為上). Fields:
  - Identity: `name`, `reading`, `english`.
  - Classification: `category`, which has 36 distinct values, so each one maps to a single stratagem.
  - Cognitive reading: `bias`, `behavioral`, `summary`, `example`, `interpretation`, `principle`, `breakdown[]`.
  - Note article: `noteTitle`, `noteUrl`.
  - Relations: `relatedStratagems[]` (153 links, 105 of them one-directional), `relatedBiases[]`, `relatedConcepts[]`, `references[]` (only #34–36).
  - Empty everywhere: `relatedIdioms[]` and `relatedNotes[]`.
- **English records** translate the same fields, except `reading`, `english`, `noteUrl` and `relatedStratagems`.
- **Cognitive tree:** 6 groups → 22 sub-groups → 52 placements of the 36 stratagems. 15 stratagems sit in two or three sub-groups.
- **Traditional six chapters (勝戦計 … 敗戦計):** not encoded anywhere. They follow from the number, in blocks of 6.

## What works

- Every record has long-form content in both languages, and the app validates this at start-up.
- Search covers names, categories, summaries, biases, behavioural readings, examples, related concepts and biases (plus reading and English name in JA). It searches the Japanese fields too when the page is in English.
- Language choice survives reloads (`localStorage`) and is shareable (`?lang=`). Switching keeps scroll and tree state.
- Lighthouse is already high, and axe reports 0 violations on load and after scrolling, in both languages, at 390 and 1440 px.

## Problems

### Information architecture

1. **No overview of the system.** The 36 appear only as a long list or a tree of cards. On a phone the page is 18,576 px (EN) tall and nothing shows "36" at a glance.
2. **The traditional six chapters are missing**, although they are the classical structure of the text.
3. **"Cognitive categories" is a list of 36 one-item categories.** Every card reads "1 mapped". The `<select>` filter therefore selects exactly one stratagem.
4. **The tree view repeats 15 stratagems** (52 cards for 36 entries), so the same card can appear three times in one list.
5. **Relations are invisible.** `relatedStratagems`, `relatedBiases`, `relatedConcepts`, `references` and the cognitive-tree membership are in the data, but none is rendered in the detail view.
6. **No deep links.** Selecting a stratagem never changes the URL, so a stratagem cannot be shared or bookmarked.
7. **No position or progress.** There is no previous/next and no sense of where #07 sits in the 36.
8. **Stats** "36 / 36 / 1 Human Firmware" carry little information.

### Reading

9. **Line breaks are lost.** The Japanese interpretations are written in short paragraphs with deliberate line breaks (up to 8 paragraphs). They are rendered as one run-on `<p>`.
10. **The detail is a dense key/value block** ("Bias: … Behavioral Reading: … Modern Example: …") inside a scroll box with an inner scrollbar on desktop. The hierarchy between principle, interpretation and evidence is flat.
11. **English content gaps** (content, not design; listed for review, not changed):
    - In 33 of 36 English records, `interpretation` is identical to `summary`.
    - In 33 of 36 English records, `bias` is identical to `category`.

### Mobile

12. **Long scroll before the atlas:** the 36 one-item category cards come before it.
13. **The detail opens as a full-screen modal drawer, but focus escapes it.** After one Tab, focus is on the page behind it.

### Accessibility (found by keyboard and code review; axe does not detect them)

14. **The 36 category cards are click-only `<div>`s**, unreachable by keyboard.
15. **Duplicate `id="mobileDetailTitle"`** (desktop pane and mobile drawer). The drawer's `aria-labelledby` resolves to the hidden desktop copy.
16. **52 `<h3>`s inside the navigation list**, so the heading outline is mostly card titles.
17. **16 Tab stops before the first stratagem.** There is no arrow-key movement inside the list.
18. **No `prefers-reduced-motion` handling**, and `scroll-behavior: smooth` is always on.
19. **No content without JavaScript:** the atlas, categories and details are all rendered by script.

### Code

20. **`stratagems.js` mixes data and app code**, so any UI change touches the data file.
21. **Markup is built with string concatenation from data without escaping.** One `&` in the data is rendered as raw HTML.

## Baseline measurements (before)

**Lighthouse, median of 3 runs** (`?lang=en` / `?lang=ja`, local server, no compression):

| Page | Perf | A11y | Best Pr. | SEO | FCP | LCP | TBT | CLS | Weight | DOM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EN mobile | 98 | 100 | 96 | 100 | 1.9 s | 1.9 s | 19 ms | 0 | 162 KiB | 667 |
| EN desktop | 100 | 100 | 96 | 100 | 0.4 s | 0.4 s | 0 ms | 0 | 162 KiB | 667 |
| JA mobile | 97 | 100 | 96 | 100 | 1.9 s | 1.9 s | 151 ms | 0.026 | 162 KiB | 729 |
| JA desktop | 100 | 100 | 96 | 100 | 0.4 s | 0.5 s | 5 ms | 0 | 162 KiB | 729 |

Best Practices 96 is the Cloudflare analytics beacon, which the sandbox cannot reach.

**axe-core 4** (WCAG 2.0/2.1/2.2 A+AA + best practice): 0 violations at load and after scrolling, EN/JA × 390/1440 px.

**Page height:**

| Width | EN | JA |
| --- | --- | --- |
| 390 px | 18,576 px | 17,331 px |
| 820 px | 15,338 px | 15,708 px |
| 1440 px | 4,409 px | 4,269 px |
