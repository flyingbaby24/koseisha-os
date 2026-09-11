"""Freeze the current corpus as a named, checksummed release.

    python -m api.corpus_release --show
    python -m api.corpus_release --stamp

A corpus release is the four artifacts that must agree with one another, plus
one name for the set (T7 §18):

    documents_master.csv        documents_sha256
    <embeddings artifact>       embedding_artifact_sha256
    parameter_scores.csv        parameters_sha256
    map_projection_3d.json      projection_fingerprint

Any of these changing changes what a search returns or where a node sits, so
they are versioned together under a single `release_id`:

    thoughtmap-corpus-20260909-v1

`--stamp` fills in whatever the manifest is missing and writes the release id.
It never invents data: every value is computed from the file it describes, and
a file that is absent is reported rather than skipped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .corpus_manifest import MANIFEST_FILENAME


RELEASE_PREFIX = "thoughtmap-corpus"
RELEASE_REVISION = 1


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def release_id(corpus_version: str, revision: int = RELEASE_REVISION) -> str:
    return f"{RELEASE_PREFIX}-{corpus_version or 'unversioned'}-v{revision}"


def gather(settings) -> dict[str, Any]:
    """Everything that identifies this corpus release, computed from disk."""
    from .map_projection import DEFAULT_ARTIFACT_PATH, read_artifact
    from .repositories import _official_documents_path

    documents_path = _official_documents_path(settings.db_dir)
    directory = documents_path.parent
    manifest_path = directory / MANIFEST_FILENAME
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))

    facts: dict[str, Any] = {
        "release_id": release_id(str(manifest.get("corpus_version", ""))),
        "corpus_version": manifest.get("corpus_version", ""),
        "document_count": manifest.get("document_count", 0),
        "manifest_path": str(manifest_path),
    }

    facts["documents_sha256"] = _sha256(documents_path) if documents_path.exists() else ""
    facts["documents_recorded"] = str(manifest.get("documents_sha256", ""))

    parameters_path = directory / "parameter_scores.csv"
    facts["parameters_sha256"] = _sha256(parameters_path) if parameters_path.exists() else ""
    facts["parameters_recorded"] = str(manifest.get("parameters_sha256", ""))

    artifact = settings.embeddings_path
    facts["embedding_artifact_recorded"] = str(manifest.get("embedding_artifact_sha256", ""))
    facts["embedding_artifact_present"] = bool(artifact and artifact.exists())

    if DEFAULT_ARTIFACT_PATH.exists():
        projection = read_artifact(DEFAULT_ARTIFACT_PATH)
        facts["projection_fingerprint"] = str(
            projection.get("projection", {}).get("dataset_fingerprint", "")
        )
        facts["projection_nodes"] = len(projection.get("nodes", []))
    else:
        facts["projection_fingerprint"] = ""
        facts["projection_nodes"] = 0
    facts["projection_recorded"] = str(manifest.get("projection_fingerprint", ""))

    return facts


def stamp(settings) -> dict[str, Any]:
    """Write the release identity and any missing checksums into the manifest."""
    facts = gather(settings)
    manifest_path = Path(facts["manifest_path"])
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))

    changes: list[str] = []

    def record(key: str, value: Any) -> None:
        if value and manifest.get(key) != value:
            manifest[key] = value
            changes.append(key)

    record("release_id", facts["release_id"])
    record("release_revision", RELEASE_REVISION)
    record("parameters_sha256", facts["parameters_sha256"])
    record("projection_fingerprint", facts["projection_fingerprint"])
    record("projection_node_count", facts["projection_nodes"])

    # The documents checksum is already recorded; only fill it if empty, and
    # never silently overwrite a recorded value with a different one — that
    # would hide a changed corpus rather than surface it.
    if not manifest.get("documents_sha256"):
        record("documents_sha256", facts["documents_sha256"])

    # A machine-specific path helps nobody but the machine it was written on.
    if manifest.pop("embedding_artifact_local_hint", None) is not None:
        changes.append("embedding_artifact_local_hint (removed)")

    if changes:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    facts["changes"] = changes
    return facts


def _print(facts: dict[str, Any]) -> None:
    print(f"release id           : {facts['release_id']}")
    print(f"corpus version       : {facts['corpus_version']}")
    print(f"documents            : {facts['document_count']:,}")
    print(f"projection nodes     : {facts['projection_nodes']:,}")
    print(f"projection fingerprint: {facts['projection_fingerprint'][:32]}")
    print(f"documents sha256     : {facts['documents_sha256'][:32]}")
    print(f"parameters sha256    : {facts['parameters_sha256'][:32]}")
    print(f"embeddings sha256    : {facts['embedding_artifact_recorded'][:32]}")
    print(f"embedding present    : {facts['embedding_artifact_present']}")

    recorded = facts["documents_recorded"]
    if recorded and recorded != facts["documents_sha256"]:
        print()
        print("WARNING: documents_master.csv does not match the recorded checksum.")
        print("  This is a different corpus than the manifest describes.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--show", action="store_true", help="Report without writing.")
    parser.add_argument("--stamp", action="store_true", help="Write the release identity.")
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    from .config import get_settings

    settings = get_settings()

    if args.stamp:
        facts = stamp(settings)
        _print(facts)
        print()
        print("manifest updated:" if facts["changes"] else "manifest already current.")
        for change in facts["changes"]:
            print(f"  {change}")
    else:
        facts = gather(settings)
        _print(facts)

    if args.json:
        args.json.write_text(json.dumps(facts, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json}")

    recorded = facts["documents_recorded"]
    drifted = bool(recorded and recorded != facts["documents_sha256"])
    return 1 if drifted else 0


if __name__ == "__main__":
    sys.exit(main())
