# Stratagems Atlas: before / after captures

Evidence for the Stratagems Atlas redesign PR. These files are documentation only: GitHub Pages does not serve them, and they can be dropped before or after merging.

- **before** = `main` at `e91ffbd`; **after** = `claude/brave-pasteur-p7xcqp` at `0172677`.
- **How they were captured:** Playwright + Chromium 1194 against the same local static server, with `prefers-reduced-motion: reduce` so every frame is settled.
- **Widths:** desktop 1440 × 900, tablet 820 × 1180, phone 390 × 844.
- **Names:**
  - `*-fold` is the first screen.
  - `*-entry32` / `*-entry7` show a selected stratagem.
  - `*-atlas` is the phone board.
  - `*-search` shows filtering by "trust".
  - `*-full` is the whole page.
- **Scaling:** desktop images are scaled to 960 px, the tablet search to 560 px, the full desktop page to 480 px and the full phone page to 240 px.
- **Fonts:** Japanese Mincho headings appear in a fallback face, because the capture machine has no Hiragino or Yu Mincho.
