"""Build `tokenizer.spm` from an encoder's `tokenizer.json`.

    python -m api.prepare_query_tokenizer --encoder-dir D:/ThoughtMap/encoder

Reads the vocabulary, the piece scores and the normalizer's precompiled
charsmap out of `tokenizer.json` and writes them as a SentencePiece model, then
proves the two agree before it writes anything permanent.

Why this exists as its own step, rather than inside `prepare_query_encoder`:
the ONNX export needs torch and sentence-transformers and a network round trip
to Hugging Face. This needs none of that. An encoder directory prepared before
the SentencePiece path existed can be upgraded in place, in seconds, without
re-exporting 449 MB of weights that are not changing.

The output is derived entirely from `tokenizer.json` — same pieces, same
scores, same normalizer — so it is a re-encoding of the existing artifact and
not a new model. The verification step is what makes that claim checkable
rather than asserted: every sample must produce byte-identical ids, or nothing
is written.

Build-time dependencies: `sentencepiece` and `protobuf`. A serving instance
needs only `sentencepiece`.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .query_tokenizer import (
    ADDED_TOKENS,
    BOS_ID,
    EOS_ID,
    JSON_FILENAME,
    MAX_SEQUENCE_LENGTH,
    SPM_FILENAME,
)


#: Text the build must agree on before it writes the model. Chosen to exercise
#: the parts of a tokenizer that break: scripts with no spaces, combining
#: marks, compatibility-normalised characters, and the added-token literals.
#: The corpus itself is a far larger sample and is used when `--corpus` is
#: given; this list is what makes the check runnable without a 542 MB artifact.
VERIFICATION_SAMPLES: tuple[str, ...] = (
    "",
    " ",
    "   ",
    "\t\n",
    "Plato",
    "PLATO",
    "  leading and trailing  ",
    "the nature of justice",
    "the categorical imperative and the kingdom of ends",
    "l'homme révolté",
    "Übermensch",
    "naïve café",
    "存在と時間",
    "こころ",
    "論語",
    "哲学とは何か",
    "도덕경",
    "Бытие и время",
    "Ἠθικὰ Νικομάχεια",
    "الوجود والزمان",
    "השאלה על ההוויה",
    "Ⅷ roman numeral",
    "ﬁ ligature",
    "ﬀ",
    "①②③",
    "e\u0301 combining",
    "é precomposed",
    "emoji 😀 and 𝔘𝔫𝔦𝔠𝔬𝔡𝔢",
    "multiple    internal     spaces",
    "hyphen-ated and em—dash and en–dash",
    "123 456 7.89 1,000,000",
    "<s> </s> <unk> <pad> <mask>",
    "a query ending in <mask>",
    "a" * 300,
    "http://example.com/path?q=1&r=2",
    "C++ и Python; naïveté",
    "\u200b zero width \u00a0 nbsp",
    "夏目漱石 and Natsume Sōseki",
    "the " * 200,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_model(tokenizer_json: Path) -> bytes:
    """Serialise a SentencePiece model carrying tokenizer.json's vocabulary."""
    try:
        from sentencepiece import sentencepiece_model_pb2 as pb
    except Exception as exc:  # pragma: no cover - build-time dependency
        raise SystemExit(
            "Building tokenizer.spm needs `sentencepiece` and `protobuf`:\n"
            f"    pip install sentencepiece protobuf\ncause={exc}"
        ) from exc

    blob = json.loads(tokenizer_json.read_text(encoding="utf-8"))
    model = blob.get("model") or {}

    if model.get("type") != "Unigram":
        raise SystemExit(
            f"{tokenizer_json} holds a {model.get('type')!r} model. This converter "
            "handles Unigram, which is what this encoder's tokenizer uses."
        )
    normalizer = blob.get("normalizer") or {}
    if normalizer.get("type") != "Precompiled":
        raise SystemExit(
            f"{tokenizer_json} uses a {normalizer.get('type')!r} normalizer. Only "
            "Precompiled carries over to SentencePiece unchanged."
        )

    proto = pb.ModelProto()
    proto.trainer_spec.model_type = pb.TrainerSpec.UNIGRAM
    proto.trainer_spec.vocab_size = len(model["vocab"])
    proto.trainer_spec.bos_id = BOS_ID
    proto.trainer_spec.eos_id = EOS_ID
    proto.trainer_spec.pad_id = ADDED_TOKENS["<pad>"]
    proto.trainer_spec.unk_id = int(model.get("unk_id", 3))
    proto.trainer_spec.bos_piece = "<s>"
    proto.trainer_spec.eos_piece = "</s>"
    proto.trainer_spec.pad_piece = "<pad>"
    proto.trainer_spec.unk_piece = "<unk>"

    proto.normalizer_spec.name = "precompiled"
    proto.normalizer_spec.precompiled_charsmap = base64.b64decode(
        normalizer["precompiled_charsmap"]
    )
    # The three flags the Metaspace pre-tokenizer implies: a leading ▁ on every
    # fragment, whitespace collapsed, and spaces represented as ▁.
    proto.normalizer_spec.add_dummy_prefix = True
    proto.normalizer_spec.remove_extra_whitespaces = True
    proto.normalizer_spec.escape_whitespaces = True

    special = {
        0: pb.ModelProto.SentencePiece.CONTROL,
        1: pb.ModelProto.SentencePiece.CONTROL,
        2: pb.ModelProto.SentencePiece.CONTROL,
        int(model.get("unk_id", 3)): pb.ModelProto.SentencePiece.UNKNOWN,
        ADDED_TOKENS["<mask>"]: pb.ModelProto.SentencePiece.CONTROL,
    }
    for index, (piece, score) in enumerate(model["vocab"]):
        entry = proto.pieces.add()
        entry.piece = piece
        entry.score = float(score)
        if index in special:
            entry.type = special[index]

    return proto.SerializeToString()


def compare(tokenizer_json: Path, spm_path: Path, samples) -> list[tuple[str, list, list]]:
    """Every sample where the two disagree. Empty means identical."""
    from tokenizers import Tokenizer

    from .query_tokenizer import HuggingFaceQueryTokenizer, SentencePieceQueryTokenizer

    reference = HuggingFaceQueryTokenizer(tokenizer_json)
    candidate = SentencePieceQueryTokenizer(spm_path)

    mismatches: list[tuple[str, list, list]] = []
    for text in samples:
        # One string at a time: batching pads to the batch's longest row, which
        # would compare padding rather than tokenization.
        expected_ids, expected_mask = reference.encode_batch([text])
        actual_ids, actual_mask = candidate.encode_batch([text])
        if not (
            expected_ids.tolist() == actual_ids.tolist()
            and expected_mask.tolist() == actual_mask.tolist()
        ):
            mismatches.append((text, expected_ids.tolist()[0], actual_ids.tolist()[0]))
    return mismatches


def _corpus_samples(limit: int) -> list[str]:
    from .config import get_settings
    from .repositories import create_search_index_repository

    frame = create_search_index_repository(get_settings()).load_index()
    texts: list[str] = []
    for column in ("title", "author", "notes"):
        if column in frame.columns:
            texts.extend(str(v) for v in frame[column].dropna().unique().tolist())
    return texts[:limit] if limit else texts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--encoder-dir", type=Path, required=True)
    parser.add_argument(
        "--corpus",
        action="store_true",
        help="Also verify against every corpus title, author and note.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Cap the corpus sample.")
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Write a golden id fixture here for the CI regression test.",
    )
    args = parser.parse_args(argv)

    directory: Path = args.encoder_dir
    tokenizer_json = directory / JSON_FILENAME
    if not tokenizer_json.exists():
        print(f"ERROR: {tokenizer_json} does not exist.")
        return 1

    print(f"reading  {tokenizer_json} ({tokenizer_json.stat().st_size / 1048576:.1f} MB)")
    payload = build_model(tokenizer_json)

    # Write beside the target and only rename after verification passes, so a
    # failed build can never leave a half-trusted model in place.
    staged = directory / (SPM_FILENAME + ".staged")
    staged.write_bytes(payload)
    print(f"built    {staged.name} ({len(payload) / 1048576:.1f} MB)")

    samples = list(VERIFICATION_SAMPLES)
    if args.corpus:
        try:
            corpus = _corpus_samples(args.limit)
            samples.extend(corpus)
            print(f"verifying against {len(corpus):,} corpus strings + "
                  f"{len(VERIFICATION_SAMPLES)} edge cases")
        except Exception as exc:
            staged.unlink(missing_ok=True)
            print(f"ERROR: --corpus requested but the corpus did not load: {exc}")
            return 1
    else:
        print(f"verifying against {len(samples)} edge cases "
              "(pass --corpus for the full check)")

    mismatches = compare(tokenizer_json, staged, samples)
    if mismatches:
        staged.unlink(missing_ok=True)
        print(f"\nFAILED: {len(mismatches)} of {len(samples):,} samples differ. "
              "Nothing written.")
        for text, expected, actual in mismatches[:5]:
            print(f"  text     {text[:70]!r}")
            print(f"    expected {expected[:20]}")
            print(f"    got      {actual[:20]}")
        return 1

    print(f"verified : {len(samples):,} samples, 0 mismatches")

    final = directory / SPM_FILENAME
    staged.replace(final)
    print(f"wrote    {final}")

    manifest_path = directory / "encoder_manifest.json"
    if manifest_path.exists():
        manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.setdefault("files", {})[SPM_FILENAME] = {
            "bytes": final.stat().st_size,
            "sha256": _sha256(final),
        }
        manifest["tokenizer_max_length"] = MAX_SEQUENCE_LENGTH
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"updated  {manifest_path}")
    else:
        print(f"NOTE: no encoder_manifest.json in {directory}; nothing to update.")

    if args.fixture:
        from .query_tokenizer import HuggingFaceQueryTokenizer

        reference = HuggingFaceQueryTokenizer(tokenizer_json)
        fixture_texts = list(VERIFICATION_SAMPLES)
        if args.corpus:
            # A deterministic stride over the corpus, so the fixture is a real
            # sample rather than the alphabetical head of it.
            corpus = _corpus_samples(0)
            stride = max(1, len(corpus) // 400)
            fixture_texts.extend(corpus[::stride][:400])
        records = []
        for text in fixture_texts:
            ids, mask = reference.encode_batch([text])
            records.append({"text": text, "ids": ids.tolist()[0], "mask": mask.tolist()[0]})
        args.fixture.parent.mkdir(parents=True, exist_ok=True)
        args.fixture.write_text(
            json.dumps(
                {
                    "note": (
                        "Golden token ids from tokenizers.Tokenizer, the reference "
                        "implementation. Regenerate with `python -m "
                        "api.prepare_query_tokenizer --fixture`."
                    ),
                    "max_sequence_length": MAX_SEQUENCE_LENGTH,
                    "samples": records,
                },
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
        print(f"fixture  {args.fixture} ({len(records):,} samples)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
