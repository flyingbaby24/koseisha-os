"""One command that says whether this deployment may serve traffic.

    python -m api.release_check                       # artifacts only
    python -m api.release_check --base-url http://127.0.0.1:8078   # + live checks

Runs the release gates in order of cost, stopping at nothing and reporting
everything (T7 §17, §39):

    1. corpus release identity      manifest, checksums, release_id
    2. corpus integrity             counts, dimensions, projection
    3. query encoder                manifest, pinned model, file checksums
    4. readiness                    /ready on a running instance
    5. smoke suite                  the paths a first visitor exercises

It orchestrates the existing tools rather than reimplementing them, and it is
not a test framework: unit tests belong in CI, which needs none of the heavy
artifacts this checks.

Exit status is 0 only when every gate passes, so it can gate a release.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# The corpus this release serves. A deployment whose counts differ is not this
# release, whatever its manifest says (T7 §17).
EXPECTED_DOCUMENTS = 63_891


@dataclass
class Gate:
    name: str
    ok: bool
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class ReleaseCheck:
    def __init__(self) -> None:
        self.gates: list[Gate] = []

    def record(self, name: str, ok: bool, detail: str = "", **data: Any) -> bool:
        self.gates.append(Gate(name, ok, detail, data))
        print(f"[{'PASS' if ok else 'FAIL'}] {name:<24} {detail}")
        for key, value in data.items():
            print(f"       {key}: {value}")
        return ok

    @property
    def ok(self) -> bool:
        return all(gate.ok for gate in self.gates)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "expected_documents": EXPECTED_DOCUMENTS,
            "gates": [
                {"name": g.name, "ok": g.ok, "detail": g.detail, **g.data}
                for g in self.gates
            ],
        }


def run(base_url: str | None, verify_checksums: bool, expected: int) -> ReleaseCheck:
    from .config import get_settings

    check = ReleaseCheck()
    settings = get_settings()

    print(f"ThoughtMap release check — mode={settings.deployment_mode}\n")

    # --- 1. release identity ---------------------------------------------
    try:
        from .corpus_release import gather

        facts = gather(settings)
        drifted = bool(
            facts["documents_recorded"]
            and facts["documents_recorded"] != facts["documents_sha256"]
        )
        check.record(
            "corpus release",
            not drifted and bool(facts["release_id"]),
            facts["release_id"],
            corpus_version=facts["corpus_version"],
            projection_fingerprint=facts["projection_fingerprint"][:16],
        )
    except Exception as exc:
        check.record("corpus release", False, f"{type(exc).__name__}: {exc}")

    # --- 2. corpus integrity ---------------------------------------------
    try:
        from .verify_corpus import verify

        started = time.perf_counter()
        report = verify(compare_load_paths=False)
        elapsed = time.perf_counter() - started

        loaded = next(
            (r for r in report.results if r.name == "corpus_load"), None
        )
        documents = int((loaded.data or {}).get("rows", 0)) if loaded else 0
        # verify() reports the count in its detail; re-derive it defensively.
        if not documents and loaded is not None:
            digits = "".join(c for c in loaded.detail.split(" ")[0] if c.isdigit())
            documents = int(digits or 0)

        counts_match = documents == expected
        check.record(
            "corpus integrity",
            report.ok and counts_match,
            f"{documents:,} documents (expected {expected:,}), {elapsed:.1f}s",
            failed_checks=[r.name for r in report.results if not r.ok] or "none",
        )
    except Exception as exc:
        check.record("corpus integrity", False, f"{type(exc).__name__}: {exc}")

    # --- 3. query encoder -------------------------------------------------
    try:
        from .config import ONNX_PROVIDER
        from .query_encoder import describe_encoder, verify_encoder_artifacts

        described = describe_encoder(settings)
        if settings.encoder_provider == ONNX_PROVIDER:
            verify_encoder_artifacts(
                settings.encoder_dir, verify_checksums=verify_checksums
            )
            check.record(
                "query encoder",
                True,
                f"{described['provider']} — {described['model_id']}",
                revision=described["revision"][:12] or "(unrecorded)",
                checksums="verified" if verify_checksums else "size only",
            )
        else:
            # Not a failure, but a public release should be self-contained.
            check.record(
                "query encoder",
                not settings.is_public,
                f"provider={described['provider']}"
                + (
                    " — a public release should use the ONNX encoder so it needs "
                    "no torch and no model registry"
                    if settings.is_public
                    else ""
                ),
            )
    except Exception as exc:
        check.record("query encoder", False, f"{type(exc).__name__}: {exc}")

    if not base_url:
        print("\n(no --base-url: readiness and smoke were not checked)")
        return check

    # --- 4. readiness -----------------------------------------------------
    try:
        import urllib.request

        with urllib.request.urlopen(f"{base_url.rstrip('/')}/ready", timeout=60) as response:
            snapshot = json.loads(response.read())
            status = response.status
    except Exception as exc:
        snapshot, status = {}, 0
        check.record("readiness", False, f"{type(exc).__name__}: {exc}")
    else:
        check.record(
            "readiness",
            status == 200 and snapshot.get("ready") is True,
            f"status={status}",
            corpus_version=snapshot.get("corpus_version", "?"),
            documents=snapshot.get("document_count", "?"),
            blocked_by=snapshot.get("blocked_by") or "none",
        )

    # --- 5. smoke ---------------------------------------------------------
    try:
        from .smoke import main as smoke_main

        print("\n--- smoke suite ---")
        code = smoke_main(["--base-url", base_url])
        check.record("smoke suite", code == 0, "see output above")
    except Exception as exc:
        check.record("smoke suite", False, f"{type(exc).__name__}: {exc}")

    return check


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument(
        "--expect-documents", type=int, default=EXPECTED_DOCUMENTS
    )
    parser.add_argument(
        "--verify-checksums",
        action="store_true",
        help="Hash the encoder files as well as checking their sizes.",
    )
    args = parser.parse_args(argv)

    check = run(args.base_url, args.verify_checksums, args.expect_documents)

    print()
    passed = sum(1 for gate in check.gates if gate.ok)
    print(f"{passed}/{len(check.gates)} gates passed")
    print("RESULT:", "OK" if check.ok else "FAILED")

    if args.json:
        args.json.write_text(json.dumps(check.as_dict(), indent=2), encoding="utf-8")
        print(f"Wrote {args.json}")

    return 0 if check.ok else 1


if __name__ == "__main__":
    sys.exit(main())
