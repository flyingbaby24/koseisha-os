# Full corpus reconciliation (phase T4.5)

**The short version.** The repository's searchable corpus is a snapshot taken on
2026-07-02 holding 4,915 rows, of which 331 are exact duplicates. The real
corpus has continued to grow outside git, in `D:\ThoughtMap`, and now holds
**62,306 Project Gutenberg works**. Those are genuine, individually embedded,
searchable documents — not chunks, not cards. Nothing was lost; the repository
snapshot was simply never updated, and it cannot be updated in the obvious way,
because the full embeddings file is ~542 MB and GitHub rejects files over
100 MB.

No data was modified during this audit. Everything below is measurement.

---

## 1. What the repository has

`data/thoughtmap_db/official/documents_master.csv` — 4,915 rows.

| source | rows |
| --- | ---: |
| gutendex | 3,330 |
| user_suno | 992 |
| user_note | 471 |
| zip | 122 |

Embeddings and parameter scores are 1:1 with it (4,915 each), 384-dimensional,
`paraphrase-multilingual-MiniLM-L12-v2`.

### It contains 331 duplicate documents

This is a real defect, found during this audit and present in every phase from
T0 to T4.

- 331 `gutenberg_id` values appear exactly twice.
- Each pair has an **identical `text_hash`** — the same content.
- One copy is stored bare (`doc_000000`), the other prefixed
  (`gutendex:doc_000000`).
- All 331 bare ids correspond exactly to the 331-row backup
  `documents_master.csv.bak_20260701_123220`.

The cause: the original import wrote bare ids; a later re-import through
`api.append_to_official_master` prefixes `doc_id` with the source, and its
duplicate check keys on `doc_id`. `doc_000000` and `gutendex:doc_000000` are
different strings, so the same 331 books were added a second time.

This is why a search for `Plato` returns **two identical "Symposium" rows at
similarity 0.7229** — visible in the T3 and T4 verification logs, and mistaken
for a quirk of the ranking at the time.

True unique document count in the repository: **4,584**.

---

## 2. Where the "60,000+" comes from

`D:\ThoughtMap\master\`, the live pipeline output, last written 2026-07-24:

| file | size | rows |
| --- | ---: | ---: |
| `documents_master.csv` | 27 MB | **62,306** |
| `embeddings_master.csv` | 528 MB | **62,306** |
| `map_points_latest.csv` | 997 KB | 62,306 (x/y blank) |
| `import_report.csv` | 1.4 MB | 10,898 |

The repository copy of the same two files is from 2026-07-02. The pipeline kept
running; git did not follow.

### These are canonical works, not derived records

Measured on `D:\ThoughtMap\thoughtmap_embeddings_from_gutendex.csv`
(53,320 rows, the accumulated embedding output):

- 53,278 unique `gutenberg_id`
- 53,243 unique `text_hash`
- 52,097 unique titles, 18,628 unique authors

One row is one Project Gutenberg work. Not chapters, not paragraphs, not
chunks. The `master` file is the same shape at 62,306 rows with **zero**
duplicate `gutenberg_id`.

This settles the classification question: **Case A**. The 60,000+ are canonical
searchable documents and the repository corpus is incomplete.

### The pipeline

```text
gutendex_books_master.csv          62,530 catalog entries (metadata only)
        |
        |  gutendex_to_thoughtmap_prune.py
        |    download text -> strip PG boilerplate ->
        |    embed with paraphrase-multilingual-MiniLM-L12-v2
        v
thoughtmap_embeddings_from_gutendex.csv     accumulated, resumable
        |
        |  import_thoughtmap_csv.py  (dedupe on text_hash/fallback_hash)
        |    import_report.csv records 10,898 skip_duplicate_hash
        v
D:\ThoughtMap\master\documents_master.csv   62,306
                     embeddings_master.csv  62,306
```

`run_import.bat` drives this in batches of 10 with a `missing_candidates.csv`
work queue. 88 candidates remain pending, and a newer 14,072-row export batch
(2026-07-27) has not yet been merged into the 2026-07-24 master.

### What the 60,000+ is *not*

- **Not cards.** `unity/Assets/StreamingAssets/cards.csv` holds 30 sample rows.
  The card and skill layer is derived from documents and is a separate concern.
- **Not chunks.** One row per `gutenberg_id`, verified above.
- **Not catalog-only metadata.** Every row carries a parsed 384-dim vector.

---

## 3. Why only 4,915 reached the repository

Three independent reasons, in order of importance:

1. **The snapshot was never refreshed.** The last commit touching the master is
   `ca5b41d` (2026-07-02). The corpus grew from 1,916 to 62,306 after that date,
   entirely outside git.
2. **It could not have been committed as-is.** 62,306 rows of 384-float vectors
   is 528 MB in CSV. GitHub rejects any file over 100 MB, and `git-lfs` — though
   installed (3.4.0) — is **not configured**: there is no `.gitattributes`. The
   repository's current 41 MB embeddings file is already the largest text file
   tracked.
3. **The two datasets use incompatible id schemes**, so a naive append would
   have made the duplication worse rather than better (see §4).

The historical `gutendex_books/` directory deleted in `86041b9` is unrelated to
the gap: it held ~89 whole book `.txt` files for the early lyric-comparison
experiments, not a corpus.

---

## 4. Identity reconciliation

The two masters disagree on `doc_id`:

| | scheme | example |
| --- | --- | --- |
| external master | bare, sequential | `doc_000000` |
| repository, most rows | source-prefixed | `gutendex:doc_000000` |
| repository, 331 rows | bare (the duplicates) | `doc_000000` |
| repository, personal | source-prefixed | `user_suno:doc_000000` |

A bare id is **ambiguous**: `doc_000000` is a Hegel volume in the gutendex space
and a completely different work in the personal space. Only `source:id` is
unique across the corpus.

Verified by joining on `gutenberg_id`, the source-native stable identity:

- All **2,999** unique gutendex works in the repository are present in the
  external master. Nothing in the repository is missing from it.
- All **3,330** repository gutendex rows map to the same external `doc_id` once
  the `gutendex:` prefix is stripped. The mapping is exact and lossless.
- `text_hash` differs for all 3,330 — the hashing changed between pipeline
  runs, so it is **not** usable as a cross-dataset key. `gutenberg_id` is.

### The external master has no personal documents

`D:\ThoughtMap\master` is 100% `gutendex`. The 1,585 personal works
(`user_suno` 992, `user_note` 471, `zip` 122) exist **only in the repository**.

Neither corpus is a superset of the other. A union is required.

---

## 5. Duplicate policy applied

Classified by every rule separately, because they disagree:

| rule | duplicates in current master |
| --- | ---: |
| exact `doc_id` | 0 |
| `source` + `gutenberg_id` | **331** |
| `source` + `title` + `author` | 397 |
| `text_hash` | 331 |

The merge keys on **`source` + `gutenberg_id`**. Title is deliberately not used:
`Pride and Prejudice` legitimately appears under several Gutenberg editions with
different `gutenberg_id` and different content, and merging those would destroy
real works. That case is covered by a test.

---

## 6. Recovery plan and dry run

`python -m api.recover_full_corpus --dry-run`

```text
  current documents            : 4915
  duplicates within current    : 331
  current unique documents     : 4584
    of which personal (carried): 1585
  candidate documents          : 62306
  new unique documents         : 59307
  duplicates skipped           : 2999
  updates to existing rows     : 0

  embedding-compatible rows    : 63891
  missing embeddings           : 0
  missing parameters           : 59307

  projected final documents    : 63891
  projected final embeddings   : 63891
  internally consistent        : yes
```

4,584 + 59,307 = 63,891. Every merged document has a compatible vector.

Canonical `doc_id` stays `source:bare`, which is what 4,584 existing rows
already use, so **no existing identifier changes**. The 331 bare duplicates
collapse onto the prefixed rows they duplicate. Personal Library has no saved
documents in the local store, so nothing references an id that would move.

Embeddings are compatible throughout: 384-dim,
`paraphrase-multilingual-MiniLM-L12-v2` on both sides (the personal store spells
it `sentence-transformers/paraphrase-...`, the same model). Nothing needs
re-embedding.

**59,307 documents have no parameter scores.** Not a blocker for search, which
needs only embeddings, and cheap to backfill through the canonical
`thought_composition.make_filter_scores` path — a 63,891 x 384 by 384 x 10
matrix product.

---

## 7. Measured cost at full scale

Against the real 62,306-row external embeddings file:

| operation | cost |
| --- | --- |
| read the 528 MB CSV | 11.5 s |
| parse to a float32 matrix | 15.8 s |
| resident matrix | 96 MB (62,306 x 384) |
| vectorised cosine over the corpus | 54 ms |
| per-row Python cosine x 62,306 | ~0.6 s |

Startup cost is ~27 s, paid once and cached by the repository layer.

`search_utils.work_similarity_by_vector` iterates rows in Python with
`DataFrame.iterrows`, which is far slower than the raw cosine figure above.
Semantic search measured ~0.3-0.45 s at 4,915 documents in T3/T4; at 13x the
corpus that extrapolates to roughly **4-6 s per semantic query**. Functional but
poor. Vectorising it is a contained change worth doing before the full corpus
goes live — noted for T6, not done here, because changing ranking code is out of
scope for an audit phase.

### Projection

T3 projected 4,915 documents in 92 s. UMAP does not scale linearly. At 62,306
the honest statement is that it has **not been benchmarked**, and a run in the
20-60 minute range with several GB of peak memory is the expectation. §18 of the
brief requires a benchmark before committing to the full run; that benchmark has
not been performed, so no projection was regenerated.

The renderer is not the constraint: T3 measured 50,000 synthetic nodes at
5.6 ms/frame as 4 scene objects, and T4 measured a full screen-space pick at
50,000 nodes in 3.0 ms.

---

## 8. Blocking decision: where does 542 MB live?

This is the one question the audit cannot answer on its own.

A merged `embeddings_master.csv` is **~542 MB**. Options:

1. **Git LFS.** `git-lfs` 3.4.0 is already installed. Needs a `.gitattributes`
   and a repository-side LFS budget. Keeps one canonical location.
2. **Keep the corpus out of git**, as it is today, and treat `D:\ThoughtMap` (or
   a synced object store) as the source of truth, with the API pointed at it via
   `THOUGHTMAP_DB_DIR`. The API already supports this.
3. **Commit documents + parameters, not embeddings.** Documents are 27 MB and
   parameters would be ~13 MB — both comfortably committable. Embeddings are
   fetched or generated separately. `api.db_source.OfficialDatabaseSource`
   already implements exactly this pattern for SQLite, with a download URL.
4. **Ship SQLite instead of CSV**, still too large for git without LFS, but a
   single artifact and a much faster load than parsing 542 MB of text.

Option 3 fits the existing architecture most closely and is the recommendation,
but it changes how the project is deployed, so it is the user's call.

**Nothing has been written.** `recover_full_corpus.py --apply` deliberately
stops after taking backups and prints this decision, rather than dropping a
542 MB file into the working tree.

---

## 9. Corpus classification (Case A)

| category | count |
| --- | ---: |
| canonical works, external gutendex master | 62,306 |
| canonical works, repository personal sources | 1,585 |
| canonical works, repository gutendex (subset of the above) | 2,999 |
| **true canonical corpus after union** | **63,891** |
| duplicate rows in the current repository master | 331 |
| canonical works not yet in the repository | 59,307 |
| catalog entries not yet downloaded/embedded | 224 (88 queued) |
| derived game records (cards) | 30 |
| chunks / intermediate rows | 0 |

---

## 10. State of the application

Unchanged and working. The 4,915-node projection and the T4 map remain in place;
no master, embedding, parameter or projection file was modified. The application
is never left without a usable projection.

The 331 duplicates are still present in the live corpus. They are cosmetic
rather than dangerous — duplicated search hits — and removing them is part of the
merge rather than a separate edit, so they were left alone pending the storage
decision.

---

# Phase T4.6 — Full corpus recovery

The T4.5 audit above is unchanged. This records what was done about it.

## 11. Decision taken

Option 3. Lightweight canonical metadata stays in version control; the
embedding master is an external artifact. Git LFS was not configured.

In git:

| artifact | rows | size |
| --- | ---: | ---: |
| `documents_master.csv` | 63,891 | 28 MB |
| `parameter_scores.csv` | 63,891 | 13 MB |
| `corpus_manifest.json` | — | 1 KB |
| `docs/removed-duplicate-pairs.csv` | 331 | 30 KB |

Outside git:

| artifact | rows | size |
| --- | ---: | ---: |
| embedding master | 63,891 | 542 MB |
| parsed vector cache (`.vectors.npz`) | 63,891 | 108 MB |

`corpus_manifest.json` identifies the embedding artifact by **SHA-256**, not by
path, so it can move to object storage or a build artifact without touching
search behaviour. `THOUGHTMAP_EMBEDDINGS_PATH` resolves it at runtime; nothing
scans drives, and a configured-but-missing path fails immediately naming the
path.

## 12. The merge

`python -m api.recover_full_corpus --dry-run` then `--apply`.

```text
current documents            : 4915
duplicates within current    : 331
current unique documents     : 4584
  of which personal (carried): 1585
candidate documents          : 62306
new unique documents         : 59307
duplicates skipped           : 2999
updates to existing rows     : 0
embedding-compatible rows    : 63891
missing embeddings           : 0
projected final documents    : 63891
internally consistent        : yes
```

Reconciliation keys on `gutenberg_id`, the source-native identity. Not on
title (different works share titles, and one work has several Gutenberg
editions), not on `text_hash` (it changed between ingestion runs, so it cannot
identify the same work across versions), not on the generated sequential
`doc_id`.

Public ids keep the established `source:bare` shape, which 4,584 rows already
used, so **no existing identifier changed**. The external master's bare ids
gained a `gutendex:` prefix — a mapping verified 3,330/3,330 during the audit.
The merge is idempotent: re-prefixing an already-merged master is a no-op, which
`test_corpus_integrity.py` asserts.

Final counts:

| source | rows |
| --- | ---: |
| gutendex | 62,306 |
| user_suno | 992 |
| user_note | 471 |
| zip | 122 |
| **total** | **63,891** |

## 13. The 331 duplicates

Recorded to `docs/removed-duplicate-pairs.csv` before removal. Every pair was
confirmed to be the same Gutenberg work: identical `gutenberg_id`, identical
`text_hash`, one copy under a bare id and one under the source-prefixed id. The
prefixed id was kept in all 331 cases.

Four regression tests now make the pattern impossible to reintroduce silently:
no two rows may share a `gutenberg_id`, no row may carry a bare `doc_id`, the
`doc_id` prefix must agree with the `source` column, and the historical
`Symposium` case is checked by name.

## 14. Parameter backfill

63,891 rows, all ten canonical axes, via
`thought_composition.make_filter_scores`. `filter_service.py` was not used.

The document vectors already existed, so the only model work was embedding the
ten category descriptions. Scoring is a single (63,891 x 384) @ (384 x 10)
product: **0.10 s**. Total runtime 148 s, almost entirely corpus loading.

Numerical equivalence against the pre-existing canonical rows, joined on
gutendex ids only (a bare `doc_000000` exists in both the gutendex and personal
id spaces and refers to different documents):

```text
compared        : 2999
max_abs_delta   : 2.10e-07
mean_abs_delta  : 1.00e-08
```

One document of 63,891 scores all zeros. That is canonical behaviour, not a
defect: `make_filter_scores` clips negative cosines to zero and skips
normalisation when the row total is zero. Rewriting it to a uniform 0.1 would
invent an affinity the model did not find.

## 15. Search performance, and what actually needed fixing

The audit predicted semantic search would be the blocker at ~4-6 s. Measured at
63,891 documents it was 1.6 s, and **keyword was the slowest mode at 3.4 s** —
it ran a per-row `DataFrame.apply` across nine metadata columns.

Three separate row-wise bottlenecks were vectorised:

1. **Keyword scoring** — now column-wise. `_keyword_score` remains the
   single-row definition of the rule; `keyword_scores` computes the same thing
   for the whole index.
2. **Top-N selection** — `work_similarity_by_vector` built a 63,891-row frame
   and then discarded all but ten. It now ranks with a stable descending
   argsort and materialises only the surviving rows.
3. **Parameter payload assembly** — `_add_parameter_scores_payload` called
   `pd.to_numeric` on a one-element Series per column per row: 638,910 Series
   constructions per load. This, not vector parsing, dominated repository load.

| measure | before | after | speedup |
| --- | ---: | ---: | ---: |
| cold repository load | 132.8 s | **16.4 s** | 8.1x |
| keyword | 3370 ms | **313 ms** | 10.8x |
| semantic | 1620 ms | **239 ms** | 6.8x |
| hybrid | 3244 ms | **335 ms** | 9.7x |

Averages over `Plato`, `love`, `war`, `identity`, `technology`. Cold load also
benefits from a parsed-vector cache stored beside the artifact and keyed on its
size and mtime.

Top results are unchanged by the optimisation and match the T4 values on the
smaller corpus:

```text
keyword   Plato -> 0.9700  Apology
semantic  Plato -> 0.7360  The Republic of Plato
hybrid    Plato -> 0.7828  The Republic of Plato
```

Source filtering verified at full scale for all four sources.

### Equivalence, not assertion

Ranking policy is unchanged, and that is pinned by tests rather than claimed.
`test_ranking_equivalence.py` re-implements the pre-T4.6 row-wise function
verbatim and asserts identical ordering and scores within 1e-6 across random
corpora, document-origin queries, exclusion, several top values, and after the
API's own 4-decimal rounding. `test_keyword_equivalence.py` does the same for
keyword scoring against `_keyword_score`. Hybrid weights (0.8 / 0.2) were not
retuned.

A ragged-dimension corpus raises, in both the old and new implementations. That
is preserved deliberately: mixed embedding dimensions are a data defect, and
silently scoring them would hide it.

## 16. Projection at full scale

UMAP benchmark, canonical configuration unchanged
(`n_components=3, n_neighbors=10, min_dist=0.2, metric=cosine, random_state=42`):

| rows | seconds |
| ---: | ---: |
| 5,000 | 36.1 (first run) |
| 15,000 | 8.5 |
| 30,000 | 19.0 |

The 5,000-row figure is **numba JIT compilation**, not projection cost: the
first UMAP call in a process compiles its kernels. Fitting a growth curve across
it produced a negative exponent (-0.44) and a nonsense estimate. Excluding the
warm-up, 15k -> 30k gives an exponent near 1.16. `benchmark_projection.py` now
runs an explicit warm-up pass and excludes it from the fit.

Full run: **63,891 documents in 101.8 s**.

| measure | value |
| --- | --- |
| nodes | 63,891 |
| duplicates | 0 |
| non-finite coordinates | 0 |
| doc_ids match the master | yes |
| x bounds | -6.8036 -> 15.9462 |
| y bounds | -6.1191 -> 13.8358 |
| z bounds | -5.4132 -> 15.5172 |
| bounding radius | 12.33 |
| fingerprint | `ce109523a9cd996285b1c84f37b50c95...` |

Extents 22.75 / 19.95 / 20.93 — volumetric, not near-planar.

### Clustering

KMeans k=8, seed 42, unchanged from T3 so the two projections stay comparable.
The balance is far healthier than on the old corpus, where one cluster held 68%
of everything:

```text
1:15289  2:10976  4:10647  7:9023  5:8776  6:7606  0:904  3:670
```

That earlier imbalance was an artefact of a corpus that was 68% Gutendex; at
62,306 Gutendex works out of 63,891 the clustering finds real structure instead
of separating one source. No cluster-count change was made.

## 17. Artifact size and transfer

| measure | value |
| --- | --- |
| uncompressed JSON | 12.62 MB |
| gzip | **3.67 MB** (29.5%) |
| JSON parse | 0.14 s |
| `/map` cold | 0.70 s |
| `/map` warm | 0.22 s |
| `/map` warm, gzipped | 0.85 s |

JSON stays. At 3.67 MB over the wire and 0.14 s to parse there is no measured
case for a binary format, so none was invented.

**gzip was not enabled.** `/map` was shipping 12.6 MB uncompressed because the
app had no compression middleware. `GZipMiddleware` with a 1 KB threshold cuts
every map load by 3.4x and leaves small search responses alone.

## 18. Renderer and picking at the real 63,891

Measured on the actual corpus, not synthetic, with a GPU sync point:

| measure | value |
| --- | --- |
| geometry build | 38.4 ms |
| NodeIndex build | 8.8 ms |
| frame | **1.19 ms** |
| orbit frame | 0.98 ms |
| project all nodes | 2.21 ms |
| pick scan (mouse radius) | 0.24 ms |
| **full pick** | **2.45 ms** |
| pick scan (touch radius) | 0.20 ms |
| emphasis update | 0.15 ms |
| selection update | 0.16 ms |
| Fit All | 0.30 ms |
| Reset | <0.1 ms |
| scene objects | **4** |

Screen-space O(N) picking is kept: 2.45 ms is well inside a frame budget, so the
acceleration structure T4 anticipated is still not needed. `THREE.Points` is
unchanged. No GL errors.

## 19. Search to map integrity

100% join rate across 220 results and 11 query/mode/source combinations:

```text
Plato/semantic   20/20      love/semantic         20/20
Plato/keyword    20/20      war/semantic          20/20
Plato/hybrid     20/20      identity/semantic     20/20
                            technology/semantic   20/20
love/gutendex    20/20      love/user_suno        20/20
love/user_note   20/20      love/zip              20/20
```

Source filters verified correct for all four sources.

## 20. The duplicate is gone, visibly

Searching `Symposium` returns 11 results, 0 duplicate doc_ids, 0 pairs sharing
a title and score.

The clearest evidence is the semantic `Plato` ranking itself:

```text
T3/T4 (4,915 corpus)      T4.6 (63,891 corpus)
0.7360 The Republic       0.7360 The Republic of Plato
0.7229 Symposium          0.7294 Theaetetus
0.7229 Symposium   <--    0.7229 Symposium
```

The duplicated row is gone and a real work occupies the slot it was stealing.

## 21. T4 interaction at full scale

All intact at 63,891 nodes: search emphasis (63,881 dimmed + 9 result + 1 top),
result click selects and focuses at the derived distance of 12.0, node click
resolves the correct doc_id, detail matches the selection for each of the first
three results with 10 parameter rows, drag does not select, Fit Results frames
the set, and a zero-result search dims all 63,891 uniformly with Fit Results
disabled.

## 22. Presentation: density-aware point size

The first full-corpus render was **wrong to look at**. Point diameter was tuned
against 4,915 nodes, and the map is always fitted to the same world extent, so
13x the documents in the same volume overlapped into blobs — worst under Fit
Results, where the camera sits close.

Fixed by making diameter a function of corpus size. Screen coverage goes as the
square of the radius, so holding total ink roughly constant means radius scales
with `1/sqrt(count)`: 0.70 world units at 4,915 becomes 0.194 at 63,891. The
ordinary-node size ceiling dropped from 26 px to 9 px; emphasised states still
multiply it, so a selected node remains unmistakable.

Corpus semantics were not touched — no nodes were dropped, no coordinates
changed. This is presentation only, which is what §27 asks for.

---

# Phase T5 — Parameter Radar + Personal Library

Runs against the canonical 63,891-document corpus throughout. The stale
4,915-node projection is not used anywhere.

## 23. Stale embedding safety

`embeddings_master.csv` is still tracked in git and covers 4,584 of 63,891
documents. It joins *cleanly* against the full documents master, so search
would simply return less and nothing would look broken.

`api/corpus_manifest.py` now makes that impossible:

- **Before reading**, the artifact's byte size is compared with
  `embedding_artifact_bytes`. Instant, and it catches the stale file (41 MB
  against an expected 542 MB) without spending a minute reading it.
- **After the join**, every loaded document must have an embedding. Coverage is
  measured against the documents actually present, not the recorded count, so a
  corpus that grows on purpose still passes.
- **Model identity** is checked, treating `sentence-transformers/x` and `x` as
  one model and refusing a mixture.
- A documents count differing from the manifest only *warns* — that is a stale
  manifest, not a wrong artifact.

Pointing the API at the stale file now fails immediately, naming both files and
the environment variable to set. The file is retained (deleting tracked data is
a deliberate decision, not a refactor side effect) and marked with
`data/thoughtmap_db/official/README-LEGACY-embeddings_master.md`.

## 24. Radar

**SVG**, not Three.js. It is a data chart, not part of the spatial map, and it
needs crisp text, DOM accessibility and a `viewBox` that scales itself; putting
it in the WebGL scene would buy nothing and cost all three.

`ParameterRadar` receives canonical values and renders them. It never fetches,
never owns selection, and never mutates its input — a test asserts the source
array is unchanged after rendering.

### Scale strategy: one shared, derived domain

A Thought Composition sums to 1.0, so an ordinary axis sits near 0.10. Two
tempting approaches are both wrong:

- A fixed 0..1 domain puts every real profile at 10% of the radius — an
  unreadable blob at the centre.
- Normalising each polygon to its own maximum makes every profile fill the
  chart, so query and document always look equally intense and the comparison
  says nothing.

So the domain is derived from **all displayed profiles together**, padded 25%,
snapped up to a 0.05 step, and clamped to 0.20..1.00. Query and document are
always drawn on the same scale, and the legend states it ("outer ring 20.0%").
Measured: the real `Plato` profile plots at >50% of the radius instead of ~14%.

### Overlay

One radar carries both profiles: the query in cyan, the selected document in
amber, same axes, same order, same scale, vertices carrying `<title>` tooltips
with the exact percentage. Verified live with `Plato` — two polygons, ten axis
labels, shared domain.

### All-zero profile

The known canonical all-zero document collapses to the centre, renders without
throwing or dividing by zero, and is explained in words: "No positive affinity
was detected on any axis." It is **not** rewritten to fake uniform values.

### Accessibility

Every chart ships the same numbers as a `table` behind a `details` disclosure,
plus an `aria-label` naming the top three axes per profile. The radar is never
the only way to read the data.

## 25. Personal Library

Existing FastAPI contract, unchanged: `POST /users/by-email/save`,
`GET /users/by-email/saved`, `DELETE /users/by-email/saved/{doc_id}`. No schema
was redesigned.

### Identity is a key, not a login

The backend trims, lowercases and SHA-256 hashes the address to derive a user
key, and performs no authentication. The UI says so: the field reads
**"Personal Library ID / email"** with the note *"An ID to find your library.
Not a sign-in — no password, no account."* Nothing in the interface says Sign
in, Account, or Secure. It is remembered in `localStorage` — appropriate,
because there is no secret to protect — and can be changed or cleared.

### Confirmed, not optimistic

A document is marked saved only after the server confirms. The map can never
show a saved ring for something that was never persisted. A failed save leaves
the state untouched and reports the error locally.

A **duplicate save is a success**, not an error: the document is in the library
either way, which is all the user asked for. Verified against the real backend,
which returns `saved: false, duplicate: true`.

### Map-only documents

A document selected straight from the map saves without searching for it first.
`DocumentSelectionResolver` already falls back to `MapNode` metadata, and the
existing save request accepts exactly those fields, so no new endpoint and no
extra payload on the 63,891-node map were needed.

### Failure isolation

The library has its own status, error and client. A Personal database failure
sets `libraryError` and nothing else — verified live: search results, map
status, map nodes and the current selection were all untouched while a save was
refused.

## 26. Saved state in the map

A new `Saved` node state sits **below** result emphasis:

```text
Selected > Hovered > TopResult > Result > Saved > Normal/Dimmed
```

That ordering is deliberate. A library of thousands must never drown out the
ten documents a search just returned. Visually it is a faint outer halo at
0.35 opacity against the bright ring selection and hover get.

No geometry is rebuilt. Saved membership updates the same two attribute arrays
search emphasis uses, at O(nodes + saved). Measured at 63,891 nodes:

| saved works | map update |
| ---: | ---: |
| 100 | 0.23 ms |
| 1,000 | 0.34 ms |
| 10,000 | 1.50 ms |

Personal state is **not** in `/map`. That payload stays corpus-wide and
cacheable; saved works load separately and join client-side on `doc_id`.

## 27. Live verification, real corpus and real backend

Local Personal repository (the supported development backend), 63,891 documents:

| step | result |
| --- | --- |
| map loaded | 63,891 nodes |
| semantic `Plato` | 10 results, top `0.7360 The Republic of Plato` |
| query radar | 10 axes, sum 1.000000 |
| search to map join | 10/10 |
| select result | radar shows both polygons, shared domain 20.0% |
| Save via UI | "Save" to "Saved" in 2.0 s, confirmed by server |
| duplicate save | duplicate true, treated as saved |
| result row marker | present |
| library list | 2 works, tab reads "Library (2)" |
| reload library | restored from backend on page load |
| saved node state | 2 nodes at `Saved` once outside the result set |
| saved item click | selects, focuses map node at distance 12.0, detail matches |
| delete | 2 to 1 saved, selection preserved, button back to "Save" |
| document after delete | still in the map and still searchable |

Deleting removes library membership only; the canonical corpus is untouched.

## 28. Mobile camera controls

The T4.6 gap is closed. Below 1100 px the labelled bar is replaced by three
compact circular controls — Reset, Fit All, Fit Results — measured at 40x40 px,
which is a real touch target. Same handler, same actions, and Fit Results is
disabled in both places together. At 375 px the radar renders 321 px wide with
no horizontal overflow.

## 29. Performance after saved-state integration

Real 63,891 nodes, GPU sync point, 1440x900:

| measure | value |
| --- | --- |
| frame | 3.51 ms |
| full pick | 2.70 ms |
| saved-state update (1,000) | 0.34 ms |
| idle renders in 50 ticks | **0** |

Render-on-demand is intact; neither the radar nor saved state introduced a
per-frame loop.

---

# Phase T6 — Production Deployment + Runtime Optimization

Deployment architecture, measurements and decisions live in
[`deployment.md`](deployment.md). This section records what T6 changed about
the corpus runtime specifically, and the measurements behind it.

## 30. The artifact read that was not needed

T4.6 added a parsed-vector cache keyed on the artifact's size and mtime. It
removed the ~90 s JSON parse, but a start still read all 542 MB of CSV — to
recover `embedding` strings that were then discarded in favour of the cached
vectors. Measured, that read was 10–42 s depending on file-cache state, and it
carried ~700 MB of strings through the process.

T6 keys the cache on the artifact's **SHA-256 from the manifest** instead. Two
consequences:

- The cache travels. Copying the artifact to a server changes its mtime but not
  its content, so a cache built once stays valid — which is what makes
  "ship the artifact and its cache together" a usable deployment strategy.
- When the checksum matches, the CSV is not read at all. The cache already
  holds every doc_id and vector, and the manifest supplies the model name.

| | corpus load | resident after load | peak |
| --- | ---: | ---: | ---: |
| artifact read | 18–50 s | 1,374 MB | 2,289 MB |
| cache, CSV skipped | **4.1 s** | **337 MB** | **1,257 MB** |

The fast path is deliberately narrow. It requires a manifest, a matching
recorded size, **and** a checksum match — not a size/mtime match. Matching on
mtime says "probably the same file on this machine"; matching on content says
"this is the artifact the manifest describes", which is the same claim the
guard already makes before search may run at all. Anything weaker reads the
artifact.

Verified rather than assumed. `verify_corpus --compare-load-paths` moves the
cache aside, loads the corpus from the artifact, and compares:

```text
[PASS] load_path_equivalence  artifact read and vector cache produce identical vectors
         rows: 63891
         doc_ids_identical: True
         max_abs_delta: 0.0
```

## 31. One redundant copy in the ranking loop

Profiling the warm semantic path found `cosine_against_matrix` spending
129–137 ms where the matmul itself costs 2.4 ms. The cost was copies, not
arithmetic:

```python
similarities[usable] = (matrix[usable] @ target) / denominator[usable]
```

`matrix[usable]` is boolean-mask indexing, which allocates and copies the whole
93.6 MB matrix — in order to select all of it, since in a healthy corpus every
row is usable.

The fix is to take the whole matrix when every row is usable. Same rows, same
float32 arithmetic, one fewer copy. Confirmed identical, not merely close:

```text
25 random queries: max abs delta 0.0, top-50 rank mismatches 0
zero-row case: identical = True (the partial-mask branch still runs)
reference (pre-T6)          p50 = 144.8 ms
cosine_against_matrix (T6)  p50 = 115.9 ms
```

The remaining ~60 ms is `np.stack` rebuilding the matrix from a pandas column
of 63,891 separate arrays on every request. Caching that stack is the obvious
next step and was **not** taken in T6: it interacts with the pre-ranking
filters, and T6 is not a redesign phase. It is recorded as the highest-value
T7 optimization, with the measurement to justify it.

## 32. Where startup time actually goes

The working assumption had been that startup is "the model". Measured, it is
the model's *import*:

| | time |
| --- | ---: |
| `import torch` | 2.9 s |
| `import sentence_transformers` | **18–20 s** |
| constructing SentenceTransformer from a warm cache | 2.6 s |
| corpus load (cache hit) | 4.1 s |

`transformers` accounts for ~7.4 s of the import on its own, and pulls in
generation, quantisation and compilation machinery a sentence encoder never
uses. This is a dependency cost, not something the application controls.

It matters because with `THOUGHTMAP_WARMUP=off` the first search pays all of
it — measured at **28 s for a first keyword search**, since the query radar
profile needs the model too. Public deployments therefore warm at startup and
hold readiness false until it completes.

## 33. ONNX Runtime: measured, and deferred

Evaluated in an isolated environment against the same model.

| | current stack | ONNX Runtime |
| --- | ---: | ---: |
| import | 18–20 s | 0.3 s (`onnxruntime`) / 5.9 s (via `optimum`) |
| model construction | 2.6 s | 1.26 s |
| warm query encode | 13.8 ms p50 | **3.9 ms p50** |
| batch of 8 | 26.3 ms | 13.3 ms |
| model on disk | ~470 MB | 465 MB |

Numerically equivalent, including the Japanese queries:

```text
per-query cosine(torch, onnx) : 1.00000000 across all 8 queries
min cosine                    : 0.999999999999762
max abs difference            : 7.7e-07
top-10 ranking mismatches     : 0/8 against a 5,000-document corpus
```

So ONNX is faster and behaviourally equivalent within 1e-6. It was still **not
adopted in T6**, because the phase's bar is a material improvement to
deployment or runtime:

- **Runtime: immaterial.** Query encoding is ~14 ms of a ~180 ms semantic
  request. Saving 10 ms is invisible, and the §48 gates already pass with
  margin.
- **Startup: real, but already handled.** It would cut ~14 s from a 28 s
  warmup. Readiness makes that cost operationally free — `/health` stays up,
  `/ready` gates traffic, and no user waits.
- **Deployment: worse.** It introduces a 465 MB ONNX artifact needing its own
  acquisition, checksum and release lifecycle — precisely the discipline T6
  established for one heavy artifact, now needed for two.
- It also replaces `sentence-transformers`' `encode()` with a hand-written
  tokenise-and-mean-pool path. The existing `TextEncoder` protocol means that
  drops in without touching scoring, but it is new code on the path that
  produces every embedding.

Recommended for T7 as a scoped change with these numbers in hand, where the
465 MB artifact can be folded into the same release process rather than bolted
beside it.

## 34. Memory, and why one worker

| after | resident |
| --- | ---: |
| corpus loaded | 337 MB |
| model loaded | 1,013 MB |
| several searches (steady) | 1,087 MB |
| peak | 1,273 MB |

The largest consumers are the model and its runtime (~700 MB) and the corpus
frame plus the 93.6 MB embedding matrix. Nothing small is worth optimising
against those.

Each worker is a separate process with its own copy of all of it. Since
throughput is flat from 2 concurrent requests upward (6–8 searches/second
regardless), a second worker doubles memory for no gain. **One worker.**

Memory-mapping the embedding matrix was evaluated and rejected on the same
measurement: the matrix is 93.6 MB of a 1,013 MB process, and the hot path is
already dominated by copying and arithmetic rather than by paging it in.
Memmap would add page-fault risk to the ranking loop to address 9% of resident
memory.

## 35. Verification

Deployment-like run: production `vite build` output served statically, API in
`public-demo` mode against the real 63,891-document corpus.

| check | result |
| --- | --- |
| smoke suite | 16/16 |
| `/health` during warmup | 200 throughout |
| `/ready` during warmup | 503, `blocked_by=[embedding_model]`, then 200 at 18.8 s |
| stale artifact configured | `/health` 200, `/ready` 503 naming both files and the variable |
| API unreachable | "ThoughtMap is not fully available." No traceback, no Python names |
| map | 63,891 nodes, ETag, 304 in 1.8 ms |
| search | keyword 251/294, semantic 201/220, hybrid 384/442 ms (p50/p95) |
| radar | two polygons, 10 axes, shared domain 20.0% |
| public-demo library | Save control absent, Library tab hidden, routes 404 |
| mobile 375 px | compact controls 40×40, no horizontal overflow |
| rate limit | burst allowed, excess 429 with `Retry-After` in 1–2 ms |

One correction found by this pass: readiness initially reported ready while the
model was still loading, because readiness was computed from the checks that
had been *written*, and a check nobody had written yet could not block. Checks
are now declared pending before warmup starts, so the default is "not yet"
rather than "apparently fine".

A second: a relative `THOUGHTMAP_EMBEDDINGS_PATH` meant two different things —
resolved against the working directory by the readiness check and against the
project root by the repository — so one file produced "wrong size" from one and
"not found" from the other. The path is now resolved once, where the setting is
read.

---

# Phase T7 — Release Candidate

Release: **`thoughtmap-corpus-20260909-v1`**. Deployment procedure and all
operational figures live in [`deployment.md`](deployment.md); this records what
T7 changed about the runtime and why.

## 36. The matrix that was rebuilt 63,891 times a second

T6 left one measured cost unpaid: `work_similarity_by_vector` received a
DataFrame and called `np.stack` on a column of 63,891 separate arrays, building
a fresh 93.6 MB block on **every request** to reproduce something that had not
changed since startup.

`SearchCorpus` now owns that block. One contiguous float32 matrix, one row-norm
vector, built once per corpus version, with explicit lifetime: it is
constructed in exactly one place, from the frame it is aligned to, and nothing
in the search path writes to it.

| | T6 | T7 |
| --- | ---: | ---: |
| semantic p50 (in-process) | 180.3 ms | **33.0 ms** |
| semantic p95 | 193.1 ms | **48.6 ms** |
| hybrid p50 | 388.2 ms | **227.7 ms** |
| semantic throughput | 5.8 rps | **53 rps** |

Keyword search is unchanged — it never touched the matrix.

### The bug that positional shortcuts would have caused

The obvious way to map a filtered frame back onto matrix rows is to use pandas
index labels. That is wrong here, and quietly so: `apply_metadata_filter` and
`apply_parameter_filter` both end with `reset_index(drop=True)`, so after any
filter the labels are `0..N-1` of the *subset*. Indexing the matrix with them
would have produced plausible numbers pointing at entirely different documents,
and every unfiltered test would still have passed.

Rows therefore carry an explicit `_matrix_row` column, stamped at construction,
which survives filtering, copying and reindexing. `verify_matrix_equivalence`
tests filtered searches specifically for this reason.

### Proven, not assumed

`python -m api.verify_matrix_equivalence`, on the real corpus:

```text
[PASS] matrix_bit_identical         max abs delta 0.0
[PASS] norms_bit_identical          row norms match a fresh computation
[PASS] vectors_are_matrix_views     the frame column and the matrix are one allocation
[PASS] similarity_bit_identical     max abs delta 0.0
[PASS] unfiltered_ranking_identical 5 queries, top-50 doc_id order and scores
[PASS] filtered_ranking_identical   source filters reset the index; positions still correct
```

The per-row vectors are *views* into the matrix rather than a second copy, so
holding it costs ~94 MB rather than ~190 MB.

## 37. ONNX Runtime adopted

T6 measured ONNX as equivalent and faster and deferred it, on the grounds that
the startup win was already neutralised by readiness and that a second heavy
artifact was not worth it. T7 revisited that with one fact T6 did not have:

**With the ONNX provider the process imports no torch, no transformers, no
sentence-transformers and no huggingface_hub.** Measured: 1.27 s from cold
import to a produced embedding, with `heavy modules imported: NONE`.

That changes the trade entirely. It is not "a faster encoder"; it is a
deployment that does not contain a 2.5 GB deep-learning framework and never
contacts a model registry to become ready.

| | sentence-transformers | ONNX Runtime |
| --- | ---: | ---: |
| import | 18–20 s | 0.3 s |
| session/model load | 2.6 s | 1.0–1.3 s |
| warm encode p50 | 13.8 ms | **4.7 ms** |
| runtime install | torch, ~2.5 GB | onnxruntime + tokenizers, ~60 MB |
| needs a model registry at start | yes | **no** |

### Equivalence

`verify_encoder_equivalence` compares the two encoders on the real corpus over
**56 queries** spanning English philosophical terms, names, Japanese, mixed
Japanese/English, abstract concepts, one-character queries, multi-sentence
queries, punctuation, numerals, Cyrillic and Greek:

```text
worst cosine distance     : 4.478e-13   (tolerance 1e-06)
semantic order mismatches : 0
hybrid order mismatches   : 0
filtered order mismatches : 0
radar profile mismatches  : 0
worst radar axis delta    : 1.639e-07
```

Seven orders of magnitude inside the required tolerance, and not one ranking
changed.

### No silent fallback

The provider is chosen by configuration, never by availability. A deployment
configured for ONNX whose encoder is missing or altered fails readiness with
the reason; it does **not** quietly load a different runtime. The alternative
would let two instances of one commit rank differently with nothing to say so.

The encoder ships as a checksummed artifact with a pinned model revision
(`e8f8c211226b894fcb81acc59f3b34ba3efd5f42`), acquired and verified exactly
like the corpus embeddings.

## 38. What the manifest nearly missed

The first encoder export produced a manifest listing `model.onnx` (1.3 MB) and
`tokenizer.json` — and torch had written the actual weights to a **470 MB
`model.onnx.data` sidecar** that the manifest did not mention. That manifest
would have verified 4% of the artifact and called it good.

The export now hashes every file in the directory. It is the same
silent-partial-artifact failure the corpus manifest exists to prevent, arriving
by a different route.

## 39. Access logs were recording what people searched for

The application's own structured events were careful from T6: query text is
logged as a length and a 12-character hash, and no Personal Library identity is
logged at all.

Reading the actual log file showed that none of that mattered, because uvicorn
records the full request target:

```text
INFO: "GET /search?q=Plato%20and%20the%20soul&mode=semantic HTTP/1.1" 200 OK
INFO: "GET /users/by-email/saved?email=logcheck@example.invalid HTTP/1.1" 200 OK
```

A filter now rewrites sensitive query-parameter values before the line is
written, keeping the endpoint and the operationally useful parameters:

```text
INFO: "GET /search?q=<redacted>&mode=semantic&top=5 HTTP/1.1" 200 OK
INFO: "GET /users/by-email/saved?email=<redacted> HTTP/1.1" 200 OK
```

This is only visible by reading logs rather than reasoning about logging code.

## 40. Same-origin deployments could not become ready

T6 treated an unset `THOUGHTMAP_ALLOWED_ORIGINS` in a public mode as a
configuration *error*, to force explicitness. But the recommended topology
serves the frontend and API from one hostname, where there is no cross-origin
request to allow — so the recommended deployment failed readiness on
`configuration` and never started.

Unset now means "no cross-origin access", which is correct and still fails
closed. `*` remains refused outside development. `/ready` reports the posture
explicitly as `cross_origin: same-origin only`.

Found by running the dry run, not by reading the code.

## 41. Failure and recovery

`python -m api.verify_failure_modes` starts the API in each broken
configuration and checks it fails honestly — 7/7:

| simulated failure | /health | /ready | names the cause |
| --- | --- | --- | --- |
| missing embedding artifact | 200 | 503 | the path |
| wrong embedding artifact | 200 | 503 | expected size + the variable |
| missing query encoder | 200 | 503 | the directory |
| corrupt query encoder | 200 | 503 | the file and its size |
| missing map projection | 200 | 503 | the artifact path |
| corrupted vector cache | 200 | **200** | recovers by reparsing |
| restored configuration | 200 | 200 | recovered |

The corrupt-cache case is the interesting one: it must *not* block readiness,
because it is recoverable, and it recovers by itself.

## 42. Verified in a browser

Production build, served through a same-origin reverse proxy, against the
public-demo API:

| check | result |
| --- | --- |
| console during startup, map, 3 searches, selection, resize, mobile | **0 messages of any kind** |
| load order | UI interactive at 52 ms; 3.6 MB map starts at 508 ms |
| semantic "Plato" | The Republic of Plato, Theaetetus, Symposium |
| keyword "Plato" | Apology, Apology/Crito/Phaedo, Charmides |
| semantic "月と海" | three Moon treatises |
| semantic "the tension between duty and desire" | 義務と理想, 安分守己…, 主観的苦悩… |
| radar | 2 polygons, 10 axes, shared domain |
| Fit Results / Reset Camera | frame results / whole 63,891-node map |
| mobile 375 px | no overflow, 40×40 controls, radar 321 px |
| WebGL disabled | explanation shown, search still returns 10 results |
| API killed mid-session | map survives, honest error, recovers on next success |
| accessibility | every control named, radar has a numeric table, results are a labelled listbox |

Cross-lingual retrieval in both directions is the result worth noting: an
English question returned Japanese essays, and a Japanese question returned
English texts.
