"""Prove the ONNX encoder ranks identically to the one it replaces.

    python -m api.verify_encoder_equivalence
    python -m api.verify_encoder_equivalence --json report.json --top 20

Swapping the query encoder changes the first step of every semantic and hybrid
search, so "close enough" is not a standard anyone can act on. This compares
the two encoders on the real 63,891-document corpus across a deliberately
awkward query set (T7 #6):

    English philosophical terms, Japanese, mixed Japanese/English, names,
    abstract concepts, very short queries, very long queries, punctuation,
    numerals, and non-Latin scripts beyond Japanese.

and checks five things, in increasing order of what a user would notice:

    1. embedding cosine similarity between the two encoders
    2. semantic top-N ordering
    3. hybrid top-N ordering
    4. source-filtered ordering
    5. query parameter (radar) profile agreement

Tolerance is 1e-6 on cosine distance. Ordering must be **identical** — a
tolerance on ranking would be meaningless, since a swapped pair either happens
or does not.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np


TOLERANCE = 1e-6

QUERIES: list[tuple[str, str]] = [
    # --- English philosophical terms -----------------------------------
    ("philosophy", "Plato"),
    ("philosophy", "justice"),
    ("philosophy", "the nature of the good"),
    ("philosophy", "epistemology and knowledge"),
    ("philosophy", "free will and determinism"),
    ("philosophy", "the categorical imperative"),
    ("philosophy", "dialectic"),
    ("philosophy", "virtue ethics"),
    ("philosophy", "phenomenology of spirit"),
    ("philosophy", "metaphysics of substance"),
    # --- names ----------------------------------------------------------
    ("name", "Aristotle"),
    ("name", "Immanuel Kant"),
    ("name", "Friedrich Nietzsche"),
    ("name", "Simone de Beauvoir"),
    ("name", "夏目漱石"),
    ("name", "Shakespeare"),
    ("name", "Marcus Aurelius"),
    ("name", "Lao Tzu"),
    # --- Japanese -------------------------------------------------------
    ("japanese", "月と海"),
    ("japanese", "正義とは何か"),
    ("japanese", "人生の意味"),
    ("japanese", "きみの声が聞こえる"),
    ("japanese", "孤独と自由"),
    ("japanese", "美しい風景"),
    ("japanese", "哲学入門"),
    ("japanese", "愛"),
    ("japanese", "現代社会における個人の役割について考える"),
    ("japanese", "夜明け前の静けさ"),
    # --- mixed Japanese / English ---------------------------------------
    ("mixed", "Plato の国家"),
    ("mixed", "modern 社会"),
    ("mixed", "justice と 正義"),
    ("mixed", "AI と倫理 ethics"),
    ("mixed", "東京 in the rain"),
    # --- abstract concepts ----------------------------------------------
    ("abstract", "loneliness"),
    ("abstract", "the passage of time"),
    ("abstract", "hope"),
    ("abstract", "melancholy and longing"),
    ("abstract", "what it means to belong"),
    ("abstract", "the tension between duty and desire"),
    ("abstract", "impermanence"),
    # --- short ----------------------------------------------------------
    ("short", "a"),
    ("short", "why"),
    ("short", "1"),
    ("short", "愛?"),
    ("short", "の"),
    # --- long -----------------------------------------------------------
    (
        "long",
        "I am looking for a work of moral philosophy that treats the question of "
        "justice not merely as a political arrangement but as a property of the "
        "soul, ideally one that proceeds by dialogue rather than by treatise, and "
        "which takes seriously the objection that justice is only the advantage "
        "of the stronger.",
    ),
    (
        "long",
        "近代以降の社会において、個人の自由と共同体への帰属意識がどのように緊張関係"
        "を持ちながら共存してきたのかを、文学作品を通して考察したい。特に、都市化と"
        "孤独の関係に着目した作品を探している。",
    ),
    (
        "long",
        "A long-form meditation on the experience of grief, written by someone who "
        "has lost a parent, that does not attempt to console the reader but instead "
        "describes precisely what the days after a death actually feel like.",
    ),
    # --- punctuation, numerals, other scripts ---------------------------
    ("edge", "What is justice?"),
    ("edge", "\"The Republic\" — Book IV"),
    ("edge", "1984"),
    ("edge", "chapter 12, section 3"),
    ("edge", "Достоевский"),
    ("edge", "λόγος"),
    ("edge", "  spaced   out  "),
    ("edge", "!!!"),
]


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator == 0:
        return 1.0 if float(np.abs(a - b).max()) == 0.0 else 0.0
    return float(np.dot(a, b) / denominator)


def run(top: int = 10, limit: int | None = None, reference: str = "torch") -> dict[str, Any]:
    """Compare the deployed encoder against a reference on the real corpus.

    Two references, because two different questions get asked of this suite:

    ``torch``
        sentence-transformers, the implementation ONNX replaced in T7. This
        re-proves the whole chain — export, runtime, tokenizer, pooling —
        against the original, and needs a torch install.
    ``tokenizers``
        the same ONNX graph driven by the Rust tokenizer instead of
        SentencePiece. This isolates a tokenizer change to itself: the corpus,
        the matrix, the graph and the pooling are the same objects for both
        runs, so a mismatch has exactly one possible cause. No torch needed.
    """
    from .config import HUGGINGFACE_TOKENIZER, SENTENCEPIECE_TOKENIZER, get_settings
    from .query_encoder import PROVIDER_ONNX, PROVIDER_SENTENCE_TRANSFORMERS, create_query_encoder
    from .query_profile import QueryProfileService
    from .search_service import create_search_service

    settings = get_settings()
    queries = QUERIES if limit is None else QUERIES[:limit]

    print(f"Comparing query encoders over {len(queries)} queries "
          f"(reference: {reference})\n")

    onnx_settings = _with(
        settings,
        encoder_provider=PROVIDER_ONNX,
        encoder_tokenizer=SENTENCEPIECE_TOKENIZER,
    )
    if reference == "tokenizers":
        reference_settings = _with(
            settings,
            encoder_provider=PROVIDER_ONNX,
            encoder_tokenizer=HUGGINGFACE_TOKENIZER,
        )
    else:
        reference_settings = _with(settings, encoder_provider=PROVIDER_SENTENCE_TRANSFORMERS)

    started = time.perf_counter()
    onnx_encoder = create_query_encoder(onnx_settings)
    onnx_load = time.perf_counter() - started

    started = time.perf_counter()
    reference_encoder = create_query_encoder(reference_settings)
    reference_load = time.perf_counter() - started

    print(f"onnx encoder loaded in {onnx_load:.2f}s")
    print(f"reference encoder loaded in {reference_load:.2f}s\n")

    # One service, one corpus load. The encoder is swapped on it so the corpus,
    # the matrix and the ranking code are literally the same objects for both
    # runs, leaving the encoder as the only difference.
    service = create_search_service(settings)
    service.repository.load_corpus()

    report: dict[str, Any] = {
        "tolerance": TOLERANCE,
        "reference": reference,
        "queries": len(queries),
        "top": top,
        "onnx_load_s": round(onnx_load, 2),
        "reference_load_s": round(reference_load, 2),
        "worst_cosine_distance": 0.0,
        "worst_query": "",
        "failures": [],
        "by_category": {},
    }

    order_mismatch: list[str] = []
    hybrid_mismatch: list[str] = []
    filtered_mismatch: list[str] = []
    profile_worst = 0.0
    profile_mismatch: list[str] = []
    encode_times = {"onnx": [], "reference": []}

    for category, query in queries:
        # --- 1. embedding agreement -------------------------------------
        started = time.perf_counter()
        onnx_vec = np.asarray(onnx_encoder.encode([query]), dtype=np.float64).reshape(-1)
        encode_times["onnx"].append((time.perf_counter() - started) * 1000)

        started = time.perf_counter()
        reference_vec = np.asarray(
            reference_encoder.encode([query]), dtype=np.float64
        ).reshape(-1)
        encode_times["reference"].append((time.perf_counter() - started) * 1000)

        distance = 1.0 - _cosine(onnx_vec, reference_vec)
        bucket = report["by_category"].setdefault(
            category, {"queries": 0, "worst_cosine_distance": 0.0}
        )
        bucket["queries"] += 1
        bucket["worst_cosine_distance"] = max(bucket["worst_cosine_distance"], distance)

        if distance > report["worst_cosine_distance"]:
            report["worst_cosine_distance"] = distance
            report["worst_query"] = query

        if distance > TOLERANCE:
            report["failures"].append(
                {"query": query, "category": category, "cosine_distance": distance}
            )

        # --- 2-4. ranking agreement --------------------------------------
        onnx_order = _ranked(service, onnx_encoder, query, top, mode="semantic")
        reference_order = _ranked(service, reference_encoder, query, top, mode="semantic")
        if onnx_order != reference_order:
            order_mismatch.append(query)

        if _ranked(service, onnx_encoder, query, top, mode="hybrid") != _ranked(
            service, reference_encoder, query, top, mode="hybrid"
        ):
            hybrid_mismatch.append(query)

        if _ranked(
            service, onnx_encoder, query, top, mode="semantic", source="gutendex"
        ) != _ranked(
            service, reference_encoder, query, top, mode="semantic", source="gutendex"
        ):
            filtered_mismatch.append(query)

        # --- 5. radar profile --------------------------------------------
        onnx_profile = _profile(QueryProfileService(lambda: onnx_encoder), query)
        reference_profile = _profile(QueryProfileService(lambda: reference_encoder), query)
        if onnx_profile is None or reference_profile is None:
            if onnx_profile is not reference_profile:
                profile_mismatch.append(query)
        else:
            if list(onnx_profile) != list(reference_profile):
                profile_mismatch.append(f"{query} (different axes)")
            else:
                delta = max(
                    abs(onnx_profile[key] - reference_profile[key])
                    for key in onnx_profile
                )
                profile_worst = max(profile_worst, delta)

    report["semantic_order_mismatches"] = order_mismatch
    report["hybrid_order_mismatches"] = hybrid_mismatch
    report["filtered_order_mismatches"] = filtered_mismatch
    report["profile_mismatches"] = profile_mismatch
    report["worst_profile_delta"] = profile_worst
    report["encode_p50_ms"] = {
        name: round(float(np.median(values)), 2) for name, values in encode_times.items()
    }

    report["ok"] = (
        not report["failures"]
        and not order_mismatch
        and not hybrid_mismatch
        and not filtered_mismatch
        and not profile_mismatch
        and profile_worst <= 1e-4
    )
    return report


def _with(settings, **overrides):
    """A copy of settings with fields replaced. ApiSettings is frozen."""
    import dataclasses

    return dataclasses.replace(settings, **overrides)


def _ranked(service, encoder, query: str, top: int, mode: str, source: str = "") -> list[str]:
    """doc_ids for this query under this encoder, in rank order."""
    service._model = encoder  # noqa: SLF001 - deliberate: swap only the encoder
    results = service.search(query=query, mode=mode, top=top, source=source)
    return [result.doc_id for result in results]


def _profile(profile_service, query: str) -> dict[str, float] | None:
    scores = profile_service.score_query(query, "general")
    if not scores:
        return None
    return {score.key: float(score.value) for score in scores}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--reference",
        choices=("torch", "tokenizers"),
        default="torch",
        help="What to compare against: sentence-transformers, or the same ONNX "
        "graph driven by the Rust tokenizer (isolates a tokenizer change).",
    )
    args = parser.parse_args(argv)

    report = run(top=args.top, limit=args.limit, reference=args.reference)

    print(f"queries                     : {report['queries']}")
    print(f"worst cosine distance       : {report['worst_cosine_distance']:.3e}"
          f"  (tolerance {TOLERANCE:.0e})")
    print(f"  worst query               : {report['worst_query']!r}")
    print(f"semantic order mismatches   : {len(report['semantic_order_mismatches'])}")
    print(f"hybrid order mismatches     : {len(report['hybrid_order_mismatches'])}")
    print(f"filtered order mismatches   : {len(report['filtered_order_mismatches'])}")
    print(f"radar profile mismatches    : {len(report['profile_mismatches'])}")
    print(f"worst radar axis delta      : {report['worst_profile_delta']:.3e}")
    print(f"encode p50 ms               : {report['encode_p50_ms']}")
    print(f"encoder load s              : onnx {report['onnx_load_s']}, "
          f"reference {report['reference_load_s']}")

    print("\nby category:")
    for category, stats in sorted(report["by_category"].items()):
        print(f"  {category:<12} {stats['queries']:>3} queries  "
              f"worst {stats['worst_cosine_distance']:.3e}")

    for name in ("failures", "semantic_order_mismatches", "hybrid_order_mismatches",
                 "filtered_order_mismatches", "profile_mismatches"):
        if report[name]:
            print(f"\n{name}:")
            for item in report[name][:20]:
                print(f"  {item}")

    print()
    print("RESULT:", "OK" if report["ok"] else "FAILED")

    if args.json:
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {args.json}")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
