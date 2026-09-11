# ThoughtMap — public demo

**Release:** `thoughtmap-corpus-20260909-v1`

## What this is

ThoughtMap is a way to search a large library of texts by *meaning* rather than
by keyword, and to see where any result sits among everything else.

Ask it for "the tension between duty and desire" and it will find works about
exactly that — including ones that never use those words, and ones written in a
different language from the question.

## The corpus

**63,891 documents**: Project Gutenberg literature and philosophy, plus a
collection of essays and notes.

Every document has been placed in a shared semantic space, so distance in the
map means something: things near each other are about similar things.

## What you can do

**Search, three ways.**

- *Semantic* — by meaning. Try "月と海", or "what it means to belong".
- *Keyword* — by the words in titles, authors and metadata.
- *Hybrid* — keyword matches, ordered by meaning.

Search works across languages in both directions. An English question can
surface a Japanese text, and the reverse.

**Explore the Thought Space.** All 63,891 documents are drawn as one 3D map.
Search results light up in place, everything else dims, and clicking a result
flies the camera to it. You can rotate, zoom, and frame either the whole corpus
or just your current results.

**Compare on the Thought Composition radar.** Every document — and every query
— has a profile across ten axes (Philosophy, Psychology, Science, Economics,
Karma, Emotion, Morality, Ideal, Individual, Community). Select a result and
your query and the document are drawn on the same radar, at the same scale, so
the comparison means something. The same numbers are available as a table for
anyone who would rather read them.

## Limitations of this demo

**Saving is turned off.** ThoughtMap has a Personal Library feature for keeping
a collection of documents. It is disabled here, because this demo has no
accounts and no sign-in, and a "personal" library without either would not be
private. Nothing you do is stored between visits.

**It is one small server.** Please be gentle with it. Rapid repeated searches
are rate-limited; if you hit that, waiting a moment is enough.

**The 3D map needs WebGL.** Without it the map is replaced by a short
explanation and everything else — search, results, the radar — still works.

**The corpus is a fixed snapshot.** Nothing is added while the demo is running.

## Notes

Search runs on the server; your browser downloads the map, not the model.
Queries are not stored: the logs record how long a search took and how many
results it returned, never the text of what was searched for.
