# Before / after captures

Evidence for the redesign PR. Documentation only: nothing here is served by
GitHub Pages, and these files can be dropped before or after merge.

- **before** = `main` at `efe653a`; **after** = `claude/brave-pasteur-p7xcqp` at `25d22a6`.
- Captured with Playwright + Chromium 1194 against a local static server.
- `*-fold`: first viewport (desktop 1440×900, mobile 390×844), normal motion,
  2.5 s after load so entrance animations have settled.
- `*-full`: whole page in the settled state (`prefers-reduced-motion: reduce`,
  counters finished, all images decoded), stitched from viewport captures;
  the fixed header is pinned to the top for the capture only. Desktop is scaled
  to 50 %, mobile to 75 %.
- The test sandbox cannot reach Google Fonts, so for the **before** captures the
  Google Fonts request was answered locally with the same Inter / IBM Plex Mono
  files (Fontsource) so the old page renders in its real typefaces.
- Japanese text renders with the sandbox's Noto Sans CJK; the intended Mincho
  headings (Hiragino / Yu Mincho) are not installed there.
