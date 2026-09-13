"""Where query text becomes a vector — and the only place that knows how.

Search ranking must not know which runtime produced a query embedding. It asks
a `TextEncoder` for one and ranks the result; whether that came from
sentence-transformers or ONNX Runtime is a deployment decision, made here and
nowhere else (T7 #4).

Two providers:

    onnx      ONNX Runtime + the `tokenizers` Rust tokenizer. Production.
    sentence  sentence-transformers. The historical implementation, kept for
              development and as the reference the equivalence suite compares
              against.

The provider is chosen by configuration, never by availability. A public
deployment configured for ONNX whose model is missing fails readiness with a
reason; it does not quietly fall back to a different runtime, because then two
deployments of the same commit could rank differently and nobody would know
(T7 #7).
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from .embedding_model import EmbeddingModelUnavailableError, TextEncoder
from .query_tokenizer import (
    TOKENIZER_HUGGINGFACE,
    TOKENIZER_KINDS,
    TOKENIZER_SENTENCEPIECE,
    TokenizerUnavailableError,
    create_query_tokenizer,
    tokenizer_path_for,
)


logger = logging.getLogger("thoughtmap.encoder")

PROVIDER_ONNX = "onnx"
PROVIDER_SENTENCE_TRANSFORMERS = "sentence-transformers"
PROVIDERS = (PROVIDER_ONNX, PROVIDER_SENTENCE_TRANSFORMERS)

MANIFEST_FILENAME = "encoder_manifest.json"
MODEL_FILENAME = "model.onnx"
TOKENIZER_FILENAME = "tokenizer.json"


#: Intra-op threads for ONNX Runtime. See OnnxQueryEncoder for the measurement.
DEFAULT_INTRA_OP_THREADS = 2


class QueryEncoderUnavailableError(EmbeddingModelUnavailableError):
    """The configured encoder cannot be used. Answered as 503, never 500."""


class OnnxQueryEncoder:
    """Query encoder backed by ONNX Runtime.

    Deliberately avoids `transformers`: importing it costs ~6 s and pulls in
    generation, quantisation and compilation machinery a sentence encoder never
    uses. `tokenizers` is the same Rust implementation underneath, imports in
    ~0.3 s, and is already an installed dependency.
    """

    def __init__(
        self,
        model_path: Path,
        tokenizer_path: Path,
        model_id: str = "",
        intra_op_threads: int = DEFAULT_INTRA_OP_THREADS,
        tokenizer_kind: str = "",
    ) -> None:
        try:
            import onnxruntime as ort
        except Exception as exc:
            raise QueryEncoderUnavailableError(
                "The ONNX query encoder needs onnxruntime. "
                f"cause={type(exc).__name__}: {exc}"
            ) from exc

        if not model_path.exists():
            raise QueryEncoderUnavailableError(
                f"ONNX query encoder model not found: {model_path}. "
                "Run `python -m api.prepare_query_encoder` or point "
                "THOUGHTMAP_ENCODER_DIR at a prepared encoder."
            )

        # The tokenizer file names its own implementation. `create_query_encoder`
        # always passes the kind explicitly, from configuration; this fallback
        # is for the direct constructor, which tests and the prepare scripts use.
        if not tokenizer_kind:
            tokenizer_kind = (
                TOKENIZER_SENTENCEPIECE
                if Path(tokenizer_path).name.endswith(".spm")
                else TOKENIZER_HUGGINGFACE
            )

        options = ort.SessionOptions()
        # Two intra-op threads, measured rather than guessed. On a 16-core
        # machine, encoding one short query costs 5.60 ms at one thread,
        # 4.66 ms at two and 4.06 ms at four: most of the gain arrives by two,
        # and the rest is not worth the risk.
        #
        # The risk is real: ONNX Runtime releases the GIL during `run()`, so
        # concurrent searches genuinely execute in parallel. Letting the
        # runtime size its own pool would put N_cores threads behind *each*
        # in-flight request on a box that saturates at 6-8 requests/second.
        options.intra_op_num_threads = intra_op_threads
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        try:
            self._session = ort.InferenceSession(
                str(model_path), sess_options=options, providers=["CPUExecutionProvider"]
            )
        except Exception as exc:
            raise QueryEncoderUnavailableError(
                f"ONNX model could not be loaded: {model_path}. "
                f"cause={type(exc).__name__}: {exc}"
            ) from exc

        try:
            self._tokenizer = create_query_tokenizer(
                Path(tokenizer_path).parent, tokenizer_kind
            )
        except TokenizerUnavailableError as exc:
            # Re-raised as the encoder's own error so callers and readiness see
            # one failure type for "the configured encoder cannot be used".
            raise QueryEncoderUnavailableError(str(exc)) from exc

        self._inputs = {i.name for i in self._session.get_inputs()}
        self.model_id = model_id
        self.tokenizer_kind = self._tokenizer.kind
        logger.info(
            "ONNX query encoder loaded model=%s tokenizer=%s path=%s",
            model_id,
            self._tokenizer.kind,
            model_path,
        )

    def encode(self, sentences: Any, show_progress_bar: bool = False) -> np.ndarray:
        """Embed one or more texts. Signature matches `TextEncoder`."""
        texts = [str(text) for text in sentences]
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)

        ids, mask = self._tokenizer.encode_batch(texts)

        feed: dict[str, np.ndarray] = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self._inputs:
            feed["token_type_ids"] = np.zeros_like(ids)
        feed = {name: value for name, value in feed.items() if name in self._inputs}

        hidden = self._session.run(None, feed)[0].astype(np.float32)

        # Mean pooling over non-padding tokens, which is this model's pooling.
        weights = mask.astype(np.float32)[..., None]
        summed = (hidden * weights).sum(axis=1)
        counts = np.clip(weights.sum(axis=1), 1e-9, None)
        return summed / counts


class SentenceTransformerEncoder:
    """Adapter over the historical sentence-transformers path."""

    def __init__(self, model_name: str) -> None:
        from .embedding_model import load_embedding_model

        self._model = load_embedding_model(model_name)
        self.model_id = model_name

    def encode(self, sentences: Any, show_progress_bar: bool = False) -> np.ndarray:
        return np.asarray(
            self._model.encode(list(sentences), show_progress_bar=show_progress_bar),
            dtype=np.float32,
        )


def encoder_manifest(directory: Path) -> dict[str, Any] | None:
    """Read the encoder's manifest, or None when absent."""
    path = Path(directory) / MANIFEST_FILENAME
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise QueryEncoderUnavailableError(
            f"Query encoder manifest is not valid JSON: {path}"
        ) from exc


def describe_encoder(settings) -> dict[str, Any]:
    """What this deployment intends to use, without loading anything."""
    directory = getattr(settings, "encoder_dir", None)
    manifest = encoder_manifest(directory) if directory else None
    return {
        "provider": getattr(settings, "encoder_provider", PROVIDER_SENTENCE_TRANSFORMERS),
        "tokenizer": getattr(settings, "encoder_tokenizer", TOKENIZER_SENTENCEPIECE),
        "directory": str(directory) if directory else "",
        "model_id": (manifest or {}).get("model_id", getattr(settings, "model_name", "")),
        "revision": (manifest or {}).get("revision", ""),
        "encoder_version": (manifest or {}).get("encoder_version", ""),
    }


@lru_cache(maxsize=2)
def get_query_encoder(settings) -> TextEncoder:
    """The encoder for this configuration, built at most once per process.

    An encoder costs 364 MB resident: 93 MB for the ONNX session, 250 MB for
    the tokenizer, and the rest runtime scratch. (The model's own weights are
    memory-mapped from `model.onnx.data` and barely appear in that figure.)
    Three consumers ask for an encoder - startup warmup, ranking, and the radar
    profile - and before this cache each built its own: 1,594 MB steady where
    one encoder needs 364 MB.

    `ApiSettings` is a frozen dataclass, so it hashes by value: two callers
    with the same configuration share a session, and a different configuration
    (a test with a different encoder directory) correctly gets its own.
    """
    return create_query_encoder(settings)


def create_query_encoder(settings) -> TextEncoder:
    """Build a NEW encoder for this deployment's configuration.

    Prefer `get_query_encoder`, which caches: each call here allocates another
    full copy of the model weights. This remains public for tests that need an
    isolated instance.

    Never silently substitutes a different provider. A configured-but-broken
    encoder raises, and readiness reports it (T7 #7).
    """
    provider = getattr(settings, "encoder_provider", PROVIDER_SENTENCE_TRANSFORMERS)

    if provider == PROVIDER_ONNX:
        directory = getattr(settings, "encoder_dir", None)
        if directory is None:
            raise QueryEncoderUnavailableError(
                "THOUGHTMAP_ENCODER_PROVIDER=onnx but THOUGHTMAP_ENCODER_DIR is unset. "
                "Point it at a directory prepared by `python -m api.prepare_query_encoder`."
            )

        directory = Path(directory)
        manifest = encoder_manifest(directory) or {}
        verify_encoder_artifacts(directory, manifest, verify_checksums=False)

        kind = getattr(settings, "encoder_tokenizer", TOKENIZER_SENTENCEPIECE)
        if kind not in TOKENIZER_KINDS:
            raise QueryEncoderUnavailableError(
                f"Unknown THOUGHTMAP_ENCODER_TOKENIZER={kind!r}. "
                f"Expected one of {', '.join(TOKENIZER_KINDS)}."
            )

        return OnnxQueryEncoder(
            model_path=directory / MODEL_FILENAME,
            tokenizer_path=tokenizer_path_for(directory, kind),
            model_id=str(manifest.get("model_id", "")),
            intra_op_threads=int(
                getattr(settings, "encoder_threads", DEFAULT_INTRA_OP_THREADS)
            ),
            tokenizer_kind=kind,
        )

    if provider == PROVIDER_SENTENCE_TRANSFORMERS:
        return SentenceTransformerEncoder(getattr(settings, "model_name", ""))

    raise QueryEncoderUnavailableError(
        f"Unknown THOUGHTMAP_ENCODER_PROVIDER={provider!r}. "
        f"Expected one of {', '.join(PROVIDERS)}."
    )


def verify_encoder_artifacts(
    directory: Path,
    manifest: dict[str, Any] | None = None,
    verify_checksums: bool = True,
) -> None:
    """Check the encoder directory against its manifest.

    Same discipline as the corpus artifact: sizes always, checksums on demand.
    A mismatch raises rather than loading, because an encoder that is not the
    one the equivalence suite validated has not been validated at all (T7 #5).
    """
    import hashlib

    directory = Path(directory)
    manifest = manifest if manifest is not None else encoder_manifest(directory)

    if not manifest:
        raise QueryEncoderUnavailableError(
            f"No {MANIFEST_FILENAME} in {directory}. The encoder must record the "
            "model identity and revision it was exported from; an unpinned model "
            "makes a deployment non-reproducible."
        )

    if not manifest.get("model_id"):
        raise QueryEncoderUnavailableError(
            f"{MANIFEST_FILENAME} does not pin a model_id."
        )

    for name, recorded in (manifest.get("files") or {}).items():
        path = directory / name
        if not path.exists():
            raise QueryEncoderUnavailableError(
                f"Query encoder file missing: {path}"
            )

        expected_bytes = int(recorded.get("bytes", 0) or 0)
        actual_bytes = path.stat().st_size
        if expected_bytes and actual_bytes != expected_bytes:
            raise QueryEncoderUnavailableError(
                f"Query encoder file has the wrong size: {path}\n"
                f"  found    {actual_bytes:,} bytes\n"
                f"  expected {expected_bytes:,} bytes"
            )

        expected_sha = str(recorded.get("sha256", "") or "")
        if verify_checksums and expected_sha:
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected_sha:
                raise QueryEncoderUnavailableError(
                    f"Query encoder file checksum does not match the manifest: {path}"
                )
