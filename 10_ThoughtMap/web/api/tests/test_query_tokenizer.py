"""The SentencePiece tokenizer must produce exactly what `tokenizers` did.

Swapping the tokenizer changes the first step of every semantic and hybrid
search. If one id differs, the query vector differs, and the ranking differs —
so the standard is byte equality on ids *and* attention masks, not similarity.

The full proof runs over 84,545 strings (`api.verify_tokenizer_equivalence`),
which needs the 542 MB corpus artifact and is far too slow for CI. What runs
here instead is a checked-in fixture: 439 strings — every edge case plus a
deterministic stride across the corpus — with the ids the reference
implementation produced, recorded by the same build step that writes
`tokenizer.spm`. That makes a divergence a failing test on the commit that
causes it, not a discovery in production.

Tests that need the encoder artifact skip without it. The rest — configuration,
refusal to substitute, padding arithmetic — run everywhere.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from api import config as config_module
from api.config import (
    HUGGINGFACE_TOKENIZER,
    SENTENCEPIECE_TOKENIZER,
    get_settings,
)
from api.query_tokenizer import (
    ADDED_TOKENS,
    MAX_SEQUENCE_LENGTH,
    PAD_ID,
    SPM_FILENAME,
    TokenizerUnavailableError,
    _pad_to_batch,
    create_query_tokenizer,
    tokenizer_path_for,
)

FIXTURE = Path(__file__).parent / "fixtures" / "tokenizer_ids.json"


def settings_with(**overrides):
    import os

    removed = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("THOUGHTMAP_")}
    try:
        base = get_settings()
    finally:
        os.environ.update(removed)
    return config_module.ApiSettings(**{**base.__dict__, **overrides})


def encoder_dir() -> Path | None:
    """The prepared encoder, when this machine has one."""
    directory = get_settings().encoder_dir
    if directory and (Path(directory) / SPM_FILENAME).exists():
        return Path(directory)
    return None


class GoldenIdTests(unittest.TestCase):
    """The regression test proper: recorded ids, reproduced exactly."""

    @classmethod
    def setUpClass(cls) -> None:
        if not FIXTURE.exists():
            raise unittest.SkipTest(f"no id fixture at {FIXTURE}")
        directory = encoder_dir()
        if directory is None:
            raise unittest.SkipTest("no prepared encoder with tokenizer.spm")
        cls.samples = json.loads(FIXTURE.read_text(encoding="utf-8"))["samples"]
        cls.tokenizer = create_query_tokenizer(directory, SENTENCEPIECE_TOKENIZER)

    def test_every_recorded_sample_tokenizes_identically(self) -> None:
        divergences = []
        for sample in self.samples:
            ids, mask = self.tokenizer.encode_batch([sample["text"]])
            if ids.tolist()[0] != sample["ids"] or mask.tolist()[0] != sample["mask"]:
                divergences.append(sample["text"])

        self.assertEqual(
            divergences,
            [],
            f"{len(divergences)} of {len(self.samples)} recorded samples "
            "tokenize differently under SentencePiece.",
        )

    def test_the_fixture_is_a_real_sample(self) -> None:
        # A fixture that quietly shrank to three ASCII words would pass the
        # test above and prove nothing.
        texts = [s["text"] for s in self.samples]
        self.assertGreaterEqual(len(texts), 200)
        self.assertTrue(any(len(t) > 100 for t in texts), "no long strings")
        self.assertTrue(
            any(any(ord(c) > 0x3000 for c in t) for t in texts),
            "no CJK or other non-Latin script",
        )
        self.assertTrue(any("<mask>" in t for t in texts), "no added-token literal")

    def test_dtypes_and_shapes_are_what_the_graph_expects(self) -> None:
        ids, mask = self.tokenizer.encode_batch(["Plato", "the nature of justice"])
        self.assertEqual(ids.dtype, np.int64)
        self.assertEqual(mask.dtype, np.int64)
        self.assertEqual(ids.shape, mask.shape)
        self.assertEqual(ids.shape[0], 2)


class BothImplementationsAgreeTests(unittest.TestCase):
    """Run the two side by side wherever both are installed."""

    @classmethod
    def setUpClass(cls) -> None:
        directory = encoder_dir()
        if directory is None:
            raise unittest.SkipTest("no prepared encoder with tokenizer.spm")
        cls.spm = create_query_tokenizer(directory, SENTENCEPIECE_TOKENIZER)
        cls.reference = create_query_tokenizer(directory, HUGGINGFACE_TOKENIZER)

    def assert_same(self, texts: list[str]) -> None:
        a_ids, a_mask = self.reference.encode_batch(texts)
        b_ids, b_mask = self.spm.encode_batch(texts)
        self.assertEqual(a_ids.tolist(), b_ids.tolist(), f"ids differ for {texts!r}")
        self.assertEqual(a_mask.tolist(), b_mask.tolist(), f"mask differs for {texts!r}")

    def test_a_mixed_length_batch_pads_the_same_way(self) -> None:
        # Batch padding is where an independent implementation most easily
        # diverges: the width comes from the longest row, not from a constant.
        self.assert_same(["a", "the nature of justice", "Plato", "存在と時間"])

    def test_truncation_agrees_at_the_boundary(self) -> None:
        for repeat in (60, 62, 63, 64, 65, 200):
            with self.subTest(repeat=repeat):
                self.assert_same(["the nature of justice " * repeat])

    def test_a_truncated_sequence_is_exactly_the_maximum(self) -> None:
        ids, _ = self.spm.encode_batch(["philosophy " * 300])
        self.assertEqual(ids.shape[1], MAX_SEQUENCE_LENGTH)

    def test_added_token_literals_agree(self) -> None:
        for text in ("<mask>", "<s> </s>", "a query ending in <mask>", "<unk><pad>"):
            with self.subTest(text=text):
                self.assert_same([text])

    def test_empty_and_whitespace_agree(self) -> None:
        self.assert_same([""])
        self.assert_same([" "])
        self.assert_same(["", "Plato"])


class PaddingTests(unittest.TestCase):
    """No artifact needed: this is arithmetic, and it must not drift."""

    def test_rows_are_right_padded_to_the_longest(self) -> None:
        ids, mask = _pad_to_batch([[0, 5, 2], [0, 5, 6, 7, 2]])

        self.assertEqual(ids.tolist(), [[0, 5, 2, PAD_ID, PAD_ID], [0, 5, 6, 7, 2]])
        self.assertEqual(mask.tolist(), [[1, 1, 1, 0, 0], [1, 1, 1, 1, 1]])

    def test_padding_uses_id_zero(self) -> None:
        # Not 1. `enable_padding()` with no arguments overrides tokenizer.json's
        # pad_id, and the ONNX graph has been fed 0 since T7. The value is inert
        # - those positions are masked out of attention and dropped by mean
        # pooling - but reproducing it is what keeps the inputs identical.
        self.assertEqual(PAD_ID, 0)
        ids, _ = _pad_to_batch([[0, 2], [0, 5, 2]])
        self.assertEqual(ids.tolist()[0][-1], 0)

    def test_an_empty_batch_does_not_raise(self) -> None:
        ids, mask = _pad_to_batch([])
        self.assertEqual(ids.shape, (0, 0))
        self.assertEqual(mask.shape, (0, 0))


class ConfigurationTests(unittest.TestCase):
    def test_sentencepiece_is_the_default(self) -> None:
        self.assertEqual(settings_with().encoder_tokenizer, SENTENCEPIECE_TOKENIZER)

    def test_an_unknown_tokenizer_is_a_configuration_error(self) -> None:
        import os

        os.environ["THOUGHTMAP_ENCODER_TOKENIZER"] = "telepathy"
        try:
            settings = get_settings()
        finally:
            del os.environ["THOUGHTMAP_ENCODER_TOKENIZER"]

        self.assertTrue(
            any("THOUGHTMAP_ENCODER_TOKENIZER" in e for e in settings.configuration_errors),
            settings.configuration_errors,
        )

    def test_each_kind_reads_its_own_file(self) -> None:
        directory = Path("/encoder")
        self.assertEqual(
            tokenizer_path_for(directory, SENTENCEPIECE_TOKENIZER).name, "tokenizer.spm"
        )
        self.assertEqual(
            tokenizer_path_for(directory, HUGGINGFACE_TOKENIZER).name, "tokenizer.json"
        )

    def test_an_unknown_kind_is_refused_rather_than_guessed(self) -> None:
        with self.assertRaises(TokenizerUnavailableError):
            tokenizer_path_for(Path("/encoder"), "telepathy")

    def test_a_missing_model_names_the_command_that_builds_it(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            with self.assertRaises(TokenizerUnavailableError) as caught:
                create_query_tokenizer(Path(directory), SENTENCEPIECE_TOKENIZER)

        message = str(caught.exception)
        self.assertIn("prepare_query_tokenizer", message)
        # It must not offer to silently use the 250 MB implementation instead;
        # it may only mention the switch that asks for it deliberately.
        self.assertIn("THOUGHTMAP_ENCODER_TOKENIZER", message)

    def test_the_added_tokens_are_the_five_the_vocabulary_declares(self) -> None:
        self.assertEqual(
            ADDED_TOKENS,
            {"<s>": 0, "<pad>": 1, "</s>": 2, "<unk>": 3, "<mask>": 250001},
        )


class ReadinessTests(unittest.TestCase):
    def test_a_missing_spm_fails_readiness_rather_than_the_first_search(self) -> None:
        import hashlib
        import json as json_module
        from tempfile import TemporaryDirectory

        from api.readiness import FAILED, ReadinessState, evaluate_query_encoder

        with TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "model.onnx").write_bytes(b"onnx-graph")
            (path / "tokenizer.json").write_text("{}", encoding="utf-8")
            files = {}
            for name in ("model.onnx", "tokenizer.json"):
                payload = (path / name).read_bytes()
                files[name] = {
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            (path / "encoder_manifest.json").write_text(
                json_module.dumps({"model_id": "test/model", "files": files}),
                encoding="utf-8",
            )

            settings = settings_with(
                encoder_provider="onnx",
                encoder_dir=path,
                encoder_tokenizer=SENTENCEPIECE_TOKENIZER,
            )
            state = ReadinessState(settings)
            evaluate_query_encoder(state, settings)

        snapshot = state.snapshot()
        check = next(c for c in snapshot["checks"] if c["name"] == "query_encoder")
        self.assertEqual(check["status"], FAILED)
        self.assertIn("tokenizer.spm", check["detail"])
        self.assertIn("prepare_query_tokenizer", check["detail"])

    def test_the_reference_tokenizer_is_accepted_on_the_same_directory(self) -> None:
        # The point of keeping it: an encoder directory without tokenizer.spm
        # is still usable, deliberately, for regression work.
        import hashlib
        import json as json_module
        from tempfile import TemporaryDirectory

        from api.readiness import OK, ReadinessState, evaluate_query_encoder

        with TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "model.onnx").write_bytes(b"onnx-graph")
            (path / "tokenizer.json").write_text("{}", encoding="utf-8")
            files = {}
            for name in ("model.onnx", "tokenizer.json"):
                payload = (path / name).read_bytes()
                files[name] = {
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            (path / "encoder_manifest.json").write_text(
                json_module.dumps({"model_id": "test/model", "files": files}),
                encoding="utf-8",
            )

            settings = settings_with(
                encoder_provider="onnx",
                encoder_dir=path,
                encoder_tokenizer=HUGGINGFACE_TOKENIZER,
            )
            state = ReadinessState(settings)
            evaluate_query_encoder(state, settings)

        snapshot = state.snapshot()
        check = next(c for c in snapshot["checks"] if c["name"] == "query_encoder")
        self.assertEqual(check["status"], OK)
        self.assertEqual(check["tokenizer"], HUGGINGFACE_TOKENIZER)


if __name__ == "__main__":
    unittest.main()
