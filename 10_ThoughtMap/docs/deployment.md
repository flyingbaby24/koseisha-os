# ThoughtMap deployment

Everything needed to bring up ThoughtMap on a new machine, with the measurements
the choices rest on. A new operator should not need any prior conversation.

Written at the end of phase T7 (release candidate). All figures were measured
on the canonical 63,891-document corpus.

**Release:** `thoughtmap-corpus-20260909-v1`

---

## 1. What a deployment consists of

```text
Git  ──────────────────────────────────────────────────────────
  application code                 web/ , threejs/
  documents_master.csv             27 MB
  parameter_scores.csv
  map_projection_3d.json           12.6 MB
  corpus_manifest.json             the contract between all of these

External artifact storage  ────────────────────────────────────
  thoughtmap_canonical_embeddings.csv          542 MB
  thoughtmap_canonical_embeddings.csv.vectors.npz   103 MB  (derived)
  encoder/                                     466 MB  (ONNX query encoder)
```

Total persistent storage: **~1.2 GB**.

The embedding artifact is far past GitHub's 100 MB limit and is **not** in
version control. `corpus_manifest.json` records its exact size, SHA-256, model
and document count, and the runtime refuses to serve a corpus that does not
match (§4).

Git LFS was considered and not adopted: it would put ~650 MB of derived,
regenerable data into repository history permanently, in exchange for
convenience that a checksum-verified fetch already provides.

---

## 2. Required environment

| Variable | Required | Meaning |
| --- | --- | --- |
| `THOUGHTMAP_EMBEDDINGS_PATH` | **yes** | Absolute path to the canonical embedding artifact. Resolved to an absolute path at startup, so every component agrees on what it means. |
| `THOUGHTMAP_DEPLOYMENT_MODE` | for anything public | `development` (default), `public-demo`, `production`. |
| `THOUGHTMAP_ALLOWED_ORIGINS` | only if split-origin | Comma-separated frontend origins. Unset means no cross-origin access; `*` is refused outside development. |
| `THOUGHTMAP_WARMUP` | no | `off` \| `corpus` \| `full`. Defaults to `full` for public modes, `off` locally. |
| `THOUGHTMAP_LIBRARY_ENABLED` | no | Defaults **off** outside development. See §8. |
| `THOUGHTMAP_BACKEND` | no | `csv` (default). |
| `THOUGHTMAP_SEARCH_RATE_LIMIT` | no | Searches per second per client. `0` (default) disables. |
| `THOUGHTMAP_SEARCH_RATE_BURST` | no | Burst allowance, default 20. Public demo uses 15. |
| `THOUGHTMAP_TRUST_PROXY_HEADERS` | no | Read `X-Forwarded-For` for the rate-limit key. Only where a proxy overwrites it. |
| `THOUGHTMAP_VERIFY_ARTIFACT_CHECKSUM` | no | Hash the 542 MB artifact at startup (~6 s). Off by default; the size check already catches the realistic failure. |
| `THOUGHTMAP_ENCODER_PROVIDER` | for public modes | `onnx` (default outside development) or `sentence-transformers`. Never falls back silently. |
| `THOUGHTMAP_ENCODER_DIR` | with `onnx` | Directory holding `model.onnx`, `model.onnx.data`, `tokenizer.json`, `encoder_manifest.json`. |
| `THOUGHTMAP_ENCODER_THREADS` | no | ONNX intra-op threads, default 2 (the measured knee). |
| `THOUGHTMAP_VERIFY_ENCODER_CHECKSUMS` | no | Hash the encoder files at startup as well as checking sizes. |
| `VITE_THOUGHTMAP_API_BASE_URL` | frontend build | Where the browser reaches the API. Defaults to same-origin `/api`. |

`THOUGHTMAP_ALLOWED_ORIGINS` is **not** required for a same-origin deployment:
unset means no cross-origin access at all, which is exactly right when the
frontend and API share a hostname. It is required only when they do not.

Nothing has a machine-specific default. Nothing is guessed by scanning disks.

---

## 3. Bringing up a deployment

From an empty environment, in this order. Every step exits non-zero on failure,
so each can gate the next.

### 1-2. Provision

An instance with **>= 2 GB RAM** and a **persistent disk of >= 2 GB**, mounted
somewhere stable (`/data` below). See §7 for why the free tier of most
platforms will not do.

### 3-4. Acquire and verify the artifacts

```bash
cd 10_ThoughtMap/web
export THOUGHTMAP_EMBEDDINGS_PATH=/data/thoughtmap_canonical_embeddings.csv
export THOUGHTMAP_ENCODER_DIR=/data/encoder

# corpus embeddings + parsed-vector cache
python -m api.prepare_corpus_artifacts \
    --source https://storage.example/thoughtmap_canonical_embeddings.csv \
    --build-cache

# ONNX query encoder
python -m api.prepare_corpus_artifacts \
    --encoder-source https://storage.example/encoder
```

Both verify SHA-256 against a manifest. A truncated download fails here rather
than as a search that quietly returns less.

### 5. Configure

```bash
export THOUGHTMAP_DEPLOYMENT_MODE=public-demo
export THOUGHTMAP_ENCODER_PROVIDER=onnx
export THOUGHTMAP_SEARCH_RATE_LIMIT=2
export THOUGHTMAP_SEARCH_RATE_BURST=15
export THOUGHTMAP_TRUST_PROXY_HEADERS=true   # only behind a proxy that sets it
# Personal Library stays off: it authenticates nobody.
```

See `.env.example` for the full annotated set.

### 6. Build the frontend

```bash
cd ../threejs && npm ci && npm run build
# serve threejs/dist statically; see deploy/Caddyfile.example
```

### 7. Start the API

```bash
cd ../web
python -m uvicorn api.main:app --host 0.0.0.0 --port "$PORT" --workers 1
```

One worker. Not a default — see §8.

### 8. Wait for readiness

```bash
curl -fsS http://127.0.0.1:8078/ready | jq .ready
```

Roughly **4 seconds** from start. `/health` answers throughout; `/ready` stays
503 until the corpus and encoder are loaded.

### 9. Verify

```bash
python -m api.release_check --base-url https://thoughtmap.example/api
```

Runs the corpus release identity, corpus integrity, encoder verification,
readiness and the full smoke suite. Exit 0 means the deployment may serve
traffic.

### 10. Expose the public URL

Only after step 9 passes.

## 4. The corpus manifest is the deployment gate

`corpus_manifest.json` pins one corpus version (currently `20260909`) and every
artifact belonging to it. At startup the API checks, in increasing cost order:

1. **Artifact size** against `embedding_artifact_bytes` — a `stat()`, instant.
2. **Coverage after the join** — every loaded document must have an embedding.
3. **Model identity** — one embedding model across the corpus.
4. **Projection node count** against the document count.
5. **Checksum**, only when `THOUGHTMAP_VERIFY_ARTIFACT_CHECKSUM=1`.

A mismatch does not serve a partial corpus and does not crash the process. It
fails readiness with a message naming both files and the variable to change:

```text
Embedding artifact does not match the corpus manifest.
  artifact : .../embeddings_master.csv
  size     : 41,621,468 bytes
  expected : 541,994,243 bytes (thoughtmap_canonical_embeddings.csv)
Set THOUGHTMAP_EMBEDDINGS_PATH to the canonical artifact.
```

This exists because a legacy `embeddings_master.csv` used to sit in the
repository covering 4,584 of 63,891 documents, and it joined *cleanly*. Used by
mistake, search would have returned less and nothing would have looked broken.

T7 removed that file from the working tree once the guard proved no
configuration could load it. The guard stays: the same failure would arise from
a truncated download of the real artifact.

---

## 5. Health, readiness and startup

Two endpoints, two questions:

```text
GET /health   the process is alive.        Restart me if this fails.
GET /ready    the corpus is usable.        Send me traffic only if this passes.
GET /config   what this deployment offers. Read by the frontend at load.
```

A process is legitimately **healthy and not ready** for the whole of startup.
Conflating the two either kills a warming process or routes traffic to one that
would serve 7% of the corpus. Measured, from process start:

```text
t= 0.0s  /health=200  /ready=503  blocked_by=[embedding_model]
t=18.8s  /health=200  /ready=200  ready
```

`/ready` reads state the warmup task wrote; it re-validates nothing, so it is
safe to poll.

### Startup profile (warm caches, one process)

| stage | time |
| --- | ---: |
| static checks (manifest, artifact, encoder, projection) | 0.4 s |
| corpus load — documents, parameters, join, vectors, matrix | **2.3 s** |
| query encoder (ONNX Runtime) | **1.3 s** |
| **total to ready** | **3.6 s** |

T6 measured 28 s for the same work. Almost all of the difference is the query
encoder, and the reason is worth keeping:

- The old "model load" was almost entirely `import sentence_transformers`
  (~18–20 s), not weight loading (~2.6 s); `import torch` alone was 2.9 s.
  Replacing the *runtime* rather than the model is what fixed startup. ONNX
  Runtime imports in 0.3 s and loads its session in ~1 s, and produces
  embeddings identical to the previous stack within 4.5e-13 cosine distance.
- With `THOUGHTMAP_WARMUP=off` the *first* search still pays whatever the
  encoder costs, because the query radar profile needs it too. Public modes
  therefore default to `full` and hold readiness false until it completes.

Profile any machine with:

```bash
python -m api.startup_profile --json profile.json
python -m api.startup_profile --drop-vector-cache   # true cold parse
```

---

## 6. The vector cache, and why restarts are fast

Parsing 63,891 JSON vectors out of the 542 MB CSV costs ~90 s. The result is
cached beside the artifact as `<artifact>.vectors.npz` (103 MB), keyed on the
artifact's **SHA-256** from the manifest, so the cache stays valid when the
artifact is copied to another machine.

When the cache matches by checksum, the API **does not read the CSV at all** —
it already has every doc_id and vector, and the raw strings would be discarded
anyway. Measured effect at full corpus:

| | corpus load | resident after load |
| --- | ---: | ---: |
| artifact read (no cache) | 18–50 s | 1,374 MB |
| vector cache, CSV skipped | **4.1 s** | **337 MB** |

Verified equivalent, not assumed: `python -m api.verify_corpus
--compare-load-paths` reads the artifact the slow way and compares. Result on
this corpus — 63,891 rows, identical doc_id order, **max absolute vector
difference 0.0**.

The cache is derived data: git-ignored, written atomically, rejected on any
version/checksum/shape mismatch, and rebuildable with
`prepare_corpus_artifacts --build-cache`.

---

## 7. Choosing a host

Measured requirements for one instance at full corpus:

| resource | requirement |
| --- | --- |
| RAM | 1,235 MB steady, **1,257 MB peak** → provision ≥ 2 GB |
| disk | ~1.2 GB persistent (embeddings 542 MB + vector cache 103 MB + encoder 466 MB) |
| startup | ~4 s to ready; `/health` answers throughout |
| largest response | 12.6 MB, 3.7 MB gzipped |

### Artifact delivery: persistent disk, seeded from object storage

| option | verdict |
| --- | --- |
| **A. Build-time download** | Rejected. On Render, disks are not accessible during build, and baking 542 MB into the image inflates every deploy. |
| **B. Runtime startup download** | Rejected as primary. 542 MB on every cold start, and the vector cache would have to be rebuilt or re-fetched too. |
| **C. Persistent disk** | **Recommended.** Artifact and cache survive deploys and restarts, giving the measured 4.1 s corpus load. |
| **D. Object storage** | **Recommended as the source.** Provider-neutral; `prepare_corpus_artifacts --source https://…` seeds the disk once and verifies the checksum. |

C and D together: object storage holds the canonical artifact, the disk holds
the working copy plus the derived cache.

### Render specifics, checked rather than assumed

- **Free tier is unsuitable.** It cannot attach a persistent disk, and it spins
  down after 15 minutes of inactivity — so every visit after a quiet period
  would re-fetch 542 MB and re-parse it.
- **A service with a disk cannot scale to multiple instances.** That costs
  nothing here: the measured recommendation is a single instance anyway (§8).
- Disks are inaccessible during build commands, which is what rules out A.
- Pick the instance size against Render's current pricing page at deploy time;
  the requirement is ≥ 2 GB RAM. Do not rely on remembered plan limits.

---

## 8. Workers, concurrency and limits

**Run one worker.** Each worker is a separate process holding its own copy of
the corpus, the 93.6 MB embedding matrix and the model — roughly 1 GB each.
Two workers double the memory for no throughput gain, because throughput is
already flat:

| concurrent | keyword p50 / p95 | semantic p50 / p95 | keyword rps | semantic rps |
| ---: | --- | --- | ---: | ---: |
| 1 | 202 / 231 ms | 33 / 37 ms | 4.9 | 29.4 |
| 2 | 274 / 322 ms | 44 / 47 ms | 7.1 | 45.0 |
| 5 | 514 / 567 ms | 84 / 98 ms | 9.7 | 57.2 |
| 10 | 1,052 / 1,276 ms | 189 / 215 ms | 9.3 | 52.6 |
| 20 | 2,161 / 2,360 ms | 353 / 399 ms | 9.2 | 53.8 |

Zero errors at every level, including 20 concurrent. Semantic search improved
roughly tenfold in T7 (5.8 to 53 rps) because the embedding matrix is built
once at load instead of per request. Keyword search is unchanged at **~9 rps**:
it never touches that matrix, and its cost is the keyword scorer.

The process therefore saturates at **~9 keyword or ~53 semantic searches per
second**, and keyword is the binding constraint. No global lock was added; the
remaining ceiling is the interpreter plus NumPy.

Because that ceiling is low, a public URL should have some abuse protection:

```bash
export THOUGHTMAP_SEARCH_RATE_LIMIT=2
export THOUGHTMAP_SEARCH_RATE_BURST=15
```

A refusal is a 429 with `Retry-After`, answered in **1–2 ms** — a refused
request must not cost what it was trying to consume. A reverse proxy or
provider edge is a better place for this when one exists; the in-process
limiter is per-process and keyed on client address.

---

## 9. Caching and payloads

| endpoint | cache policy | why |
| --- | --- | --- |
| `/map` | `public, max-age=300, must-revalidate` + `ETag` | Identical for every caller; changes only on re-projection. |
| `/search` | `no-store` | Can depend on `user_email`; query cardinality makes shared caching a poor trade. |
| `/users/**` | `no-store` | Per-person. |
| `/ready`, `/config` | `no-store` | Deployment state. |

The `/map` ETag is the projection's own dataset fingerprint, so a regenerated
projection invalidates every browser cache without a restart.

`/map` is pre-encoded and pre-compressed once per corpus version:

| | before T6 | after |
| --- | ---: | ---: |
| gzip response | 898 ms | **4.4 ms** |
| uncompressed | 1,133 ms | 24 ms |
| conditional (304) | — | 1.8 ms |

Payload 12.6 MB → **3.7 MB gzipped**. Brotli is not produced by the
application; if the serving layer offers it, it will apply at that layer.

---

## 10. Frontend

```bash
npm ci
npm run build          # tsc --noEmit && vite build
# serve threejs/dist as static files
```

`base` is relative, so `dist/` can be served from a domain root or a subpath
without rebuilding. `VITE_THOUGHTMAP_API_BASE_URL` points the browser at the
API; unset, it uses same-origin `/api`, which is what a reverse proxy in front
of both should provide.

Bundle, gzipped:

| asset | size | when |
| --- | ---: | --- |
| entry `index.js` | **14.8 kB** | immediately |
| `index.css` | 3.6 kB | immediately |
| `three.js` | 118.1 kB | after the UI is interactive |
| scene + interaction + tooltip | 11.9 kB | with three.js |

Before T6 this was one 141.8 kB chunk that had to parse before anything
appeared. Three.js is now a separate vendor chunk that changes only when the
dependency does, so it stays cached across application deploys.

Measured load order:

```text
 29 ms  entry chunk done
 37 ms  DOM ready, search usable
 43 ms  /config, /ready answered
 47 ms  three.js loaded
 95 ms  /map request starts   ← after the UI is interactive
149 ms  /map (3.6 MB) complete
```

The search UI never waits for the map. A map failure leaves search, results,
the radar and selection working.

### Same origin or split?

Prefer **same origin** (`https://host/` and `https://host/api/…`). It removes
CORS from the deployment entirely, keeps `VITE_THOUGHTMAP_API_BASE_URL` at its
default, and leaves the door open for cookie-based auth later. A split
deployment works but requires `THOUGHTMAP_ALLOWED_ORIGINS` to be correct, which
is the configuration mistake most likely to reach production unnoticed.

---

## 11. Public demo mode and the Personal Library

The Personal Library identifies people by a normalised, SHA-256-hashed email
and **authenticates nobody**. Anyone who knows or guesses an address can read
and modify that library.

That is acceptable on a developer's machine. It is not acceptable on a public
URL, so:

- `THOUGHTMAP_LIBRARY_ENABLED` defaults to **off** in `public-demo` and
  `production`.
- The routes themselves answer **404**, not just a hidden button. A hidden
  button is not a boundary.
- The refusal deliberately avoids 401/403 and any "sign in" wording. There is
  nothing to sign in to, and implying otherwise would be a false promise.
- The UI removes the Save control and the Library tab entirely, and says so:
  *"Public demo. Explore and search the full corpus; saving to a Personal
  Library is disabled here."*

The whole code path is intact and switches back on with one variable, for a
future authenticated deployment.

**Do not enable the Personal Library on a public URL until real authentication
exists.**

---

## 12. Observability

Structured single-line events on stdout: `startup`, `search`, `map`,
`map.not_modified`, `library.save`, `library.error`, `search.rate_limited`,
`error.unhandled`, `shutdown`.

Search logs carry stage timings — `search_total_ms`, `index_ms`,
`embedding_ms`, `profile_ms`, `ranking_ms`, `response_build_ms` — so a future
regression is visible without a profiler.

Queries are logged by **length and a 12-character hash**, never as text, and no
Personal Library identity is logged in any form. A public beta's logs must not
become a record of what individuals searched for.

Unhandled errors log their traceback and return a fixed sentence. No traceback
ever reaches a browser.

---

## 13. Corpus releases

A corpus release is a content event, not application startup work. To publish
one:

1. Regenerate the embedding artifact and `documents_master.csv`.
2. Regenerate the projection: `python -m api.generate_map_projection`.
3. Regenerate `corpus_manifest.json` with a new `corpus_version`, new
   `embedding_artifact_sha256` and the new counts.
4. Upload the artifact to object storage.
5. On each deployment: `prepare_corpus_artifacts --source … --force
   --build-cache`, then `verify_corpus`, then restart.

Idempotent by construction: every step is checksum-verified, and a half-applied
release fails readiness rather than serving a mixture. The vector cache
invalidates itself on the new checksum, and `/map` ETags change with the new
projection fingerprint.

There is an unmerged local Gutenberg batch of 14,072 rows plus queued
candidates. It is deliberately **not** part of this baseline; merging it is a
corpus release, to be executed by the process above.

---

## 14. Operational commands

```bash
python -m api.prepare_corpus_artifacts [--source PATH|URL] [--build-cache] [--force]
python -m api.verify_corpus [--compare-load-paths] [--json report.json]
python -m api.startup_profile [--drop-vector-cache] [--json profile.json]
python -m api.benchmark_runtime --mode inprocess|http [--concurrency 1,2,5,10]
python -m api.smoke --base-url URL [--frontend-url URL] [--library-identity ID]
```

All are run from `10_ThoughtMap/web` and exit non-zero on failure.

---

## 15. Known limits of this deployment

- Single instance. No horizontal scaling while a persistent disk is attached,
  and multiple workers duplicate ~1 GB each.
- ~6–8 searches/second ceiling per process.
- The Personal Library has no authentication and is off publicly.
- Readiness is checked at page load; a mid-session API outage surfaces through
  per-request error handling rather than the startup banner.
- `sentence-transformers` import dominates startup (~18–20 s). ONNX Runtime was
  measured as a fix and deferred — see the T6 report.
