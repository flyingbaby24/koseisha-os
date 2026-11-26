# Portfolio spec (copied for compatibility tests)

Verbatim copies from `flyingbaby24/Jinn-Portfolio`, branch `phase-3-1-soundscape`, commit `df871f5960c53d5e7c7d592eec6fe4d6ad3f757c`:

- `src/data/schema.mjs`, `src/data/soundscape.mjs`, `src/lib/media.mjs` — the site's own validators and key encoding
- `../fixtures/jinn-portfolio/data/*.json` — the real `data/` files at that commit

`tests/test_portfolio.py` runs the uploader's export through these validators with Node (when available)
and checks that the Python ports in `jinn_uploader/portfolio.py` report exactly the same problems.
Refresh the copies when the portfolio's schema changes.
