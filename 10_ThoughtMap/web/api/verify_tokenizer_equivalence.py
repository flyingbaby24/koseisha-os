"""Prove the two tokenizers agree on the whole corpus.

    python -m api.verify_tokenizer_equivalence
    python -m api.verify_tokenizer_equivalence --json report.json

The CI regression test checks a 439-string fixture, which is what is affordable
on every commit. This is the full check: every corpus title, author and note,
plus the edge cases, compared on **ids and attention masks** through the same
`QueryTokenizer` contract the encoder uses.

Run it whenever `tokenizer.spm` is rebuilt, whenever `tokenizers` or
`sentencepiece` is upgraded, and before a release. It needs the corpus
artifact, so it does not run in CI.

The bar is zero mismatches. A rate would be meaningless: one differing id is
one query that ranks differently, and nobody would know which.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from .config import HUGGINGFACE_TOKENIZER, SENTENCEPIECE_TOKENIZER, get_settings
from .prepare_query_tokenizer import VERIFICATION_SAMPLES
from .query_tokenizer import create_query_tokenizer


def corpus_strings() -> list[str]:
    from .repositories import create_search_index_repository

    frame = create_search_index_repository(get_settings()).load_index()
    texts: list[str] = []
    for column in ("title", "author", "notes"):
        if column in frame.columns:
            texts.extend(str(value) for value in frame[column].dropna().unique().tolist())
    return texts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", type=Path, help="Write the report here.")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--show", type=int, default=8)
    args = parser.parse_args(argv)

    settings = get_settings()
    directory = settings.encoder_dir
    if directory is None:
        print("ERROR: THOUGHTMAP_ENCODER_DIR is not set.")
        return 1

    print("loading tokenizers ...")
    reference = create_query_tokenizer(Path(directory), HUGGINGFACE_TOKENIZER)
    candidate = create_query_tokenizer(Path(directory), SENTENCEPIECE_TOKENIZER)

    samples = list(VERIFICATION_SAMPLES)
    try:
        corpus = corpus_strings()
        samples.extend(corpus[: args.limit] if args.limit else corpus)
    except Exception as exc:
        print(f"ERROR: the corpus did not load: {type(exc).__name__}: {exc}")
        return 1

    print(f"comparing {len(samples):,} strings ...")
    started = time.perf_counter()
    mismatches: list[dict[str, Any]] = []
    for text in samples:
        # One string per call: a batch pads to its longest row, which would
        # compare padding width rather than tokenization.
        expected_ids, expected_mask = reference.encode_batch([text])
        actual_ids, actual_mask = candidate.encode_batch([text])
        if (
            expected_ids.tolist() != actual_ids.tolist()
            or expected_mask.tolist() != actual_mask.tolist()
        ):
            mismatches.append(
                {
                    "text": text[:200],
                    "expected": expected_ids.tolist()[0][:32],
                    "actual": actual_ids.tolist()[0][:32],
                }
            )
    elapsed = time.perf_counter() - started

    report = {
        "compared": len(samples),
        "mismatches": len(mismatches),
        "elapsed_s": round(elapsed, 1),
        "reference": HUGGINGFACE_TOKENIZER,
        "candidate": SENTENCEPIECE_TOKENIZER,
        "encoder_dir": str(directory),
        "examples": mismatches[: args.show],
    }

    print()
    print(f"compared   : {len(samples):,} strings in {elapsed:.1f}s")
    print(f"mismatches : {len(mismatches)}")
    for item in mismatches[: args.show]:
        print(f"  text     {item['text'][:70]!r}")
        print(f"    expected {item['expected'][:20]}")
        print(f"    actual   {item['actual'][:20]}")

    if args.json:
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"report     : {args.json}")

    print()
    print("RESULT:", "OK - identical" if not mismatches else "FAILED - ids differ")
    return 0 if not mismatches else 1


if __name__ == "__main__":
    sys.exit(main())
