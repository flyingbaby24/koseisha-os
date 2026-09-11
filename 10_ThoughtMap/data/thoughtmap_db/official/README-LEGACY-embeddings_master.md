# `embeddings_master.csv` — removed in T7

**Status: deleted from the working tree. Still in Git history at `ca5b41d`.**

This file used to sit in this directory and hold document embeddings. It was a
snapshot from before the T4.6 corpus recovery, covering **4,584 of the 63,891**
canonical documents — about 7%.

## Why it was dangerous

It joined *cleanly* against the full `documents_master.csv`. Nothing errored,
nothing looked wrong; search simply returned a small fraction of the corpus and
reported it as the whole thing. That is the worst shape a data bug can take.

T6 closed that off with `corpus_manifest.json`: the runtime compares the
artifact against the manifest's recorded size and checksum before reading it,
and refuses anything else. Pointing the API at this file produced:

```text
Embedding artifact does not match the corpus manifest.
  size     : 41,621,468 bytes
  expected : 541,994,243 bytes (thoughtmap_canonical_embeddings.csv)
```

## Why it was removed

Verified in T7: with the guard in place there is **no configuration in which
this file loads**. It was 41 MB of tracked data that every clone paid for and
no supported workflow could use.

History was not rewritten. `git show ca5b41d:10_ThoughtMap/data/thoughtmap_db/official/embeddings_master.csv`
recovers it if it is ever wanted for forensics.

## Where embeddings live now

Outside version control, as a checksummed external artifact:

```text
thoughtmap_canonical_embeddings.csv   542 MB   63,891 documents
```

Resolved at runtime through `THOUGHTMAP_EMBEDDINGS_PATH`, verified against
`corpus_manifest.json`, and acquired with:

```bash
python -m api.prepare_corpus_artifacts --source <path-or-url> --build-cache
```

The query encoder is provisioned the same way — see `docs/deployment.md`.
