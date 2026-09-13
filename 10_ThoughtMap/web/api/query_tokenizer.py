"""Query text to token ids — two implementations of one contract.

The ONNX graph needs `input_ids` and `attention_mask`. Producing them is the
single most memory-expensive thing this service does, and the cost is not the
model:

    ONNX Runtime session (450 MB of weights)      93 MB resident
    tokenizers.Tokenizer (250,002-piece Unigram)  250 MB resident

ONNX Runtime memory-maps `model.onnx.data`, so the 366 MB vocabulary table is
file-backed and only the rows a query touches are ever faulted in. The Rust
tokenizer has no such property: it builds a trie over the same vocabulary on
the heap, at roughly 1 KB per piece, and holds it for the life of the process.

SentencePiece holds the identical vocabulary for 41 MB. It is the
implementation `tokenizers`' Unigram model was ported from, so this is not an
approximation — measured over 84,541 strings (every corpus title, author and
note, plus deliberately awkward edge cases) the two produce **identical** ids.
`verify_tokenizer_equivalence` re-runs that proof against the full corpus;
`tests/test_query_tokenizer.py` runs it against a checked-in fixture on every
commit.

Two behaviours have to be reproduced rather than re-derived, because the
encoder's inputs must not change:

- **Truncation.** `tokenizer.json` carries `max_length: 128`, and it counts the
  two special tokens the post-processor adds. So 126 pieces of content.
- **Padding.** The encoder calls `enable_padding()` with no arguments, which
  *overrides* the file's `pad_id: 1` with 0. Padding with id 0 (`<s>`) rather
  than 1 (`<pad>`) looks wrong and is inert: those positions are masked out of
  attention and dropped by mean pooling. It is reproduced here exactly, because
  the goal is identical model inputs, not inputs that are merely as good.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

import numpy as np


#: Total length including the two special tokens the post-processor adds.
MAX_SEQUENCE_LENGTH = 128

#: What `enable_padding()` with no arguments actually uses. See the module
#: docstring: this is 0, not the `pad_id: 1` recorded in tokenizer.json.
PAD_ID = 0

BOS_ID = 0
EOS_ID = 2

#: The five tokens `tokenizers` treats as *added*: it cuts them out of the text
#: before the Unigram model sees them, so the literal string "<mask>" in a
#: query becomes one control token rather than five pieces. SentencePiece has
#: no equivalent notion, so the split is reproduced here. Without it, a query
#: containing one of these literals is the one and only input on which the two
#: implementations disagree.
ADDED_TOKENS: dict[str, int] = {
    "<s>": 0,
    "<pad>": 1,
    "</s>": 2,
    "<unk>": 3,
    "<mask>": 250001,
}

_ADDED_PATTERN = re.compile("(" + "|".join(re.escape(t) for t in ADDED_TOKENS) + ")")

TOKENIZER_SENTENCEPIECE = "sentencepiece"
TOKENIZER_HUGGINGFACE = "tokenizers"
TOKENIZER_KINDS = (TOKENIZER_SENTENCEPIECE, TOKENIZER_HUGGINGFACE)

SPM_FILENAME = "tokenizer.spm"
JSON_FILENAME = "tokenizer.json"

#: Which file each kind reads. Used by readiness to say what is missing.
TOKENIZER_FILENAMES = {
    TOKENIZER_SENTENCEPIECE: SPM_FILENAME,
    TOKENIZER_HUGGINGFACE: JSON_FILENAME,
}


class TokenizerUnavailableError(RuntimeError):
    """The configured tokenizer cannot be loaded. Answered as 503, never 500."""


class QueryTokenizer(Protocol):
    """Everything the encoder needs from a tokenizer."""

    kind: str

    def encode_batch(self, texts: list[str]) -> tuple[np.ndarray, np.ndarray]:
        """`(input_ids, attention_mask)`, both int64 and `(batch, sequence)`."""


def _pad_to_batch(rows: list[list[int]]) -> tuple[np.ndarray, np.ndarray]:
    """Right-pad to the longest row, exactly as `BatchLongest` does."""
    width = max((len(row) for row in rows), default=0)
    ids = np.full((len(rows), width), PAD_ID, dtype=np.int64)
    mask = np.zeros((len(rows), width), dtype=np.int64)
    for index, row in enumerate(rows):
        ids[index, : len(row)] = row
        mask[index, : len(row)] = 1
    return ids, mask


class SentencePieceQueryTokenizer:
    """The production tokenizer: same vocabulary, 41 MB instead of 250 MB."""

    kind = TOKENIZER_SENTENCEPIECE

    def __init__(self, model_path: Path) -> None:
        model_path = Path(model_path)
        if not model_path.exists():
            raise TokenizerUnavailableError(
                f"SentencePiece tokenizer not found: {model_path}. Build it from "
                "the encoder's tokenizer.json with\n"
                "    python -m api.prepare_query_tokenizer --encoder-dir "
                f"{model_path.parent}\n"
                "or set THOUGHTMAP_ENCODER_TOKENIZER=tokenizers to use the "
                "reference implementation."
            )

        try:
            import sentencepiece as spm  # noqa: PLC0415
        except Exception as exc:
            raise TokenizerUnavailableError(
                "The SentencePiece tokenizer needs the `sentencepiece` package. "
                f"cause={type(exc).__name__}: {exc}"
            ) from exc

        processor = spm.SentencePieceProcessor()
        try:
            processor.LoadFromFile(str(model_path))
        except Exception as exc:
            raise TokenizerUnavailableError(
                f"SentencePiece model could not be loaded: {model_path}. "
                f"cause={type(exc).__name__}: {exc}"
            ) from exc
        self._processor = processor

    def _pieces(self, text: str) -> list[int]:
        # Fast path: almost every real query contains none of the five added
        # tokens, and splitting on them costs a regex pass per query.
        if "<" not in text:
            return self._processor.EncodeAsIds(text)

        ids: list[int] = []
        for fragment in _ADDED_PATTERN.split(text):
            if not fragment:
                continue
            added = ADDED_TOKENS.get(fragment)
            if added is not None:
                ids.append(added)
            else:
                ids.extend(self._processor.EncodeAsIds(fragment))
        return ids

    def encode_batch(self, texts: list[str]) -> tuple[np.ndarray, np.ndarray]:
        limit = MAX_SEQUENCE_LENGTH - 2  # the post-processor's <s> and </s>
        rows = [[BOS_ID] + self._pieces(text)[:limit] + [EOS_ID] for text in texts]
        return _pad_to_batch(rows)


class HuggingFaceQueryTokenizer:
    """The reference implementation, kept so equivalence stays checkable.

    This is what shipped in T7 and what the SentencePiece path is verified
    against. It is not the production choice only because of its footprint.
    """

    kind = TOKENIZER_HUGGINGFACE

    def __init__(self, tokenizer_path: Path) -> None:
        tokenizer_path = Path(tokenizer_path)
        if not tokenizer_path.exists():
            raise TokenizerUnavailableError(
                f"Query encoder tokenizer not found: {tokenizer_path}."
            )

        try:
            from tokenizers import Tokenizer  # noqa: PLC0415
        except Exception as exc:
            raise TokenizerUnavailableError(
                "The reference tokenizer needs the `tokenizers` package. "
                f"cause={type(exc).__name__}: {exc}"
            ) from exc

        self._tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self._tokenizer.enable_truncation(max_length=MAX_SEQUENCE_LENGTH)
        self._tokenizer.enable_padding()

    def encode_batch(self, texts: list[str]) -> tuple[np.ndarray, np.ndarray]:
        encoded = self._tokenizer.encode_batch(texts)
        ids = np.array([item.ids for item in encoded], dtype=np.int64)
        mask = np.array([item.attention_mask for item in encoded], dtype=np.int64)
        return ids, mask


def tokenizer_path_for(directory: Path, kind: str) -> Path:
    """Which file `kind` reads out of an encoder directory."""
    try:
        return Path(directory) / TOKENIZER_FILENAMES[kind]
    except KeyError:
        raise TokenizerUnavailableError(
            f"Unknown tokenizer {kind!r}. Expected one of {', '.join(TOKENIZER_KINDS)}."
        ) from None


def create_query_tokenizer(directory: Path, kind: str) -> QueryTokenizer:
    """Build the configured tokenizer. Never substitutes a different one.

    A missing SentencePiece model is an error with a command in it, not a
    silent fall back to the 250 MB implementation: an instance that quietly
    used 200 MB more than its budget would look fine until it was killed.
    """
    path = tokenizer_path_for(directory, kind)
    if kind == TOKENIZER_SENTENCEPIECE:
        return SentencePieceQueryTokenizer(path)
    return HuggingFaceQueryTokenizer(path)
