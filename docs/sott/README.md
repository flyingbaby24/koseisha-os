# Source of Thought Tactics — work page

`https://www.jinn-project.com/sott/` (English) and `/sott/index-ja.html` (Japanese).

## Building

```sh
node docs/tools/build-sott.mjs     # writes index.html and index-ja.html from one template
node --test tests/*.mjs            # tests/jinn-sott-site.test.mjs covers this page
```

Both pages come from the template and the two string tables in
`docs/tools/build-sott.mjs`. Edit that file, not the generated HTML: CI fails when
the committed pages differ from the generator output. The Jinn Project home page
links here from `docs/index.html`; its Japanese translations of those strings live in
`docs/tools/generate-index-ja.mjs`.

| File | Role |
| --- | --- |
| `sott.css` | Page styles. Fonts are the self-hosted files in `docs/assets/fonts/`. |
| `sott.js` | Progressive enhancement: hero network, scroll-linked stages, the board diagram, lazy video, lightbox. No libraries. |
| `sott-data.js` | The 50-node / 78-link board graph, the starting nodes of the recorded battle and six roster works with their ten parameters, read from the running game. |
| `media/` | Screenshots, films and the social card (see below). |

The page reads without JavaScript (the diagrams are replaced by their text),
honours `prefers-reduced-motion` (no autoplay, no reveal motion) and never
takes over scrolling: pinned sections use `position: sticky` only.

## Media provenance

Everything in `media/` is a capture of the SoTT development build; nothing is
mocked up or generated.

- **Battle footage and screenshots** — one complete TACTICAL battle (5 vs 5,
  50 nodes, board seed 73) recorded on 19 November 2026 at 1920×1080 from the
  development build, ruleset 0.28.1. Both sides were played by the game's built-in
  AI through the normal interface; the battle ended in a territory victory after
  115 commands. Screenshots (`shot-*.webp`) are unretouched frames of the real UI.
- **Films** — `hero.mp4`, `highlight.mp4` and the six `d-*.mp4` clips are cut from
  that recording. Edits are limited to trimming, cropping to the board, scaling and
  short fades. No sound.
- **AI recording** — `ai-play.mp4` is a 16-second silent excerpt of the local
  rehearsal recording of the AI VTuber experiment (18 November 2026): a local
  Qwen3 4B model played team A for a whole battle (10 formation decisions, 76 legal
  actions; the 150-command replay re-simulated to an identical result).
- **Social card** — `og-sott.jpg` is a real battle screenshot, cropped and darkened,
  with the page title set over it.

The interactive board on the page is labelled as an explanatory diagram: it uses the
real board graph, but movement is simplified and there is no combat.

## Status wording

SoTT has no public build. The page says "In development", offers no play button and
does not link to the game's source. Change that wording only when a public build
exists.
