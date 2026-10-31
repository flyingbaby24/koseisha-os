# ThoughtMap Three.js — UI/UX overhaul (T8): before / after

Documentation only. Captured with Playwright (Chromium, SwiftShader WebGL)
against the real 63,891-node `map_projection_3d.json`, with the same scripted
sequence for both sides:

1. `initial` — map loaded, nothing searched
2. `results` — searched "plato republic" (after: with nothing selected, the
   map frames the results)
3. `selected` — Library ID set, results #2 and #4 saved, result #1 selected
4. `hover` — pointer over result #3's node
5. `fit-results` — Fit Results pressed
6. `library` — Library tab
7. `zero` — a search that matches nothing
8. `error` — a search the API fails
9. `options` — search options expanded (after only; before, they were always open)

Viewports: desktop 1440×900, tablet 1024×768, mobile 390×844 (@2x).

`before-*` is `main` at a425852; `after-*` is this branch.

**Search results in these captures come from a local fixture API**, not the
FastAPI search engine: the embedding artifact is not in version control, so
`/search` was served by a simple title/author keyword match over the corpus
CSVs (with the real per-document parameter scores, and a query profile made
from the top results). `/map` is the real artifact. The rankings shown are
therefore not ThoughtMap's — they only exercise the UI with contract-shaped
responses. No frontend code was changed to accommodate the fixture.
