"""Export the query encoder to ONNX, once, with a pinned identity.

    python -m api.prepare_query_encoder --out D:/ThoughtMap/encoder
    python -m api.prepare_query_encoder --out /data/encoder --verify

Run on a machine that has torch and sentence-transformers. The *result* needs
neither: a deployment loads `model.onnx` with onnxruntime and `tokenizer.json`
with the Rust tokenizer, so a deployed instance never contacts Hugging Face and
never needs a 2.5 GB torch install (T7 #8).

The output directory is a self-describing artifact:

    model.onnx              the graph
    tokenizer.json          the tokenizer, exported alongside it
    encoder_manifest.json   model id, revision, dimension, file checksums

The manifest pins the exact model revision. Nothing at runtime resolves a model
name against a remote registry, so "the model" cannot change under a deployment
without the manifest changing too (T7 #5).

Like the corpus embeddings, this is a heavy external artifact: it does not
belong in ordinary Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Bumped when the export procedure changes in a way that could alter outputs,
# so a stale encoder directory is recognisable rather than merely old.
ENCODER_VERSION = 1

# Opset 14 covers every operator this graph uses and is widely supported by
# onnxruntime releases. Pinned rather than defaulted so two exports of the same
# model produce the same graph.
ONNX_OPSET = 14


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export(model_name: str, out_dir: Path, opset: int = ONNX_OPSET) -> dict[str, Any]:
    import torch
    from sentence_transformers import SentenceTransformer

    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"loading {model_name} ...")
    started = time.perf_counter()
    model = SentenceTransformer(model_name)
    print(f"  loaded in {time.perf_counter() - started:.1f}s")

    transformer = model[0].auto_model
    tokenizer = model.tokenizer
    transformer.eval()

    # A two-example batch with different lengths, so the exported graph is
    # traced with both batch and sequence axes genuinely varying. Tracing on a
    # single fixed-size example is the classic way to bake in a shape that then
    # fails on the first real query.
    sample = tokenizer(
        ["Plato", "the nature of justice and the soul"],
        padding=True,
        truncation=True,
        max_length=128,
        return_tensors="pt",
    )

    input_names = [name for name in ("input_ids", "attention_mask", "token_type_ids") if name in sample]
    args = tuple(sample[name] for name in input_names)

    model_path = out_dir / "model.onnx"
    print(f"exporting to {model_path} (opset {opset}) ...")
    started = time.perf_counter()
    with torch.no_grad():
        torch.onnx.export(
            transformer,
            args,
            str(model_path),
            input_names=input_names,
            output_names=["last_hidden_state"],
            dynamic_axes={
                **{name: {0: "batch", 1: "sequence"} for name in input_names},
                "last_hidden_state": {0: "batch", 1: "sequence"},
            },
            opset_version=opset,
            do_constant_folding=True,
        )
    print(f"  exported in {time.perf_counter() - started:.1f}s")

    tokenizer_path = out_dir / "tokenizer.json"
    saved = Path(tokenizer.name_or_path)
    source = saved / "tokenizer.json"
    if source.exists():
        shutil.copyfile(source, tokenizer_path)
    else:
        # Fall back to asking the tokenizer to serialise itself.
        tokenizer.backend_tokenizer.save(str(tokenizer_path))
    print(f"  tokenizer written to {tokenizer_path}")

    dimension = int(transformer.config.hidden_size)
    revision = str(getattr(transformer.config, "_commit_hash", "") or "")

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "encoder_version": ENCODER_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_id": model_name,
        "revision": revision,
        "runtime": "onnxruntime",
        "opset": opset,
        "embedding_dimension": dimension,
        "pooling": "mean",
        "max_sequence_length": 128,
        "files": {},
    }

    # Every file in the directory, not just the two named above.
    #
    # torch writes tensors larger than the protobuf limit to a sidecar —
    # `model.onnx.data`, 470 MB of the 489 MB total. Listing only model.onnx
    # and tokenizer.json would produce a manifest that verifies 4% of the
    # artifact and calls it good, which is exactly the silent-partial-artifact
    # failure the corpus manifest exists to prevent.
    for path in sorted(out_dir.iterdir()):
        if not path.is_file() or path.name == "encoder_manifest.json":
            continue
        print(f"  hashing {path.name} ({path.stat().st_size / (1024 * 1024):,.1f} MB) ...")
        manifest["files"][path.name] = {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }

    manifest_path = out_dir / "encoder_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  manifest written to {manifest_path}")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--opset", type=int, default=ONNX_OPSET)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Load the exported encoder and check it against the manifest.",
    )
    args = parser.parse_args(argv)

    manifest = export(args.model, args.out, args.opset)

    total = sum(entry["bytes"] for entry in manifest["files"].values())
    print()
    print(f"model_id  : {manifest['model_id']}")
    print(f"revision  : {manifest['revision'] or '(not recorded by this model)'}")
    print(f"dimension : {manifest['embedding_dimension']}")
    print(f"size      : {total / (1024 * 1024):,.1f} MB")

    if args.verify:
        from .query_encoder import OnnxQueryEncoder, verify_encoder_artifacts

        verify_encoder_artifacts(args.out, manifest, verify_checksums=True)
        encoder = OnnxQueryEncoder(
            args.out / "model.onnx", args.out / "tokenizer.json", manifest["model_id"]
        )
        vector = encoder.encode(["Plato"])
        print(f"verify    : OK, encoded shape {vector.shape}")

    print()
    print("Do not commit this directory to Git. Publish it as an external")
    print("artifact and fetch it with `prepare_corpus_artifacts --encoder-source`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
