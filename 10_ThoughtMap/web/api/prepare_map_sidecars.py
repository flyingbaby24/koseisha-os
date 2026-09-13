"""Publish the `/map` response beside an existing projection artifact.

    python -m api.prepare_map_sidecars
    python -m api.prepare_map_sidecars --artifact /data/map_projection_3d.json
    python -m api.prepare_map_sidecars --check

`generate_map_projection` already does this as part of writing the artifact, so
this command exists for the cases where that did not run here: an artifact
copied onto a server, one produced before the sidecar existed, or one whose
`.gz` was lost in transfer.

Serving instances never do this work. Turning 63,891 nodes back into bytes
costs a 12 MB parse into ~37.5 MB of Python dicts plus a re-serialisation and a
gzip — 87 MB of transient, measured — and that is the largest peak in a cold
start. It is deterministic output of the projection, so it belongs to the
release, not to the request path.

`--check` validates without writing, which is what a deployment script wants
before it declares an artifact ready to ship.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .map_projection import (
    DEFAULT_ARTIFACT_PATH,
    gzip_path_for,
    meta_path_for,
    read_artifact,
    verify_map_sidecars,
    write_map_sidecars,
)


def prepare(artifact_path: Path) -> dict:
    """Build the sidecars from the artifact on disk."""
    # Validates the schema on the way through: publishing a response for an
    # artifact the server would reject helps nobody.
    artifact = read_artifact(artifact_path)
    fingerprint = str(artifact.get("projection", {}).get("dataset_fingerprint", ""))
    node_count = len(artifact.get("nodes", []))
    del artifact

    # The bytes on disk, not a re-serialisation of the parsed form: the
    # artifact *is* the identity response, and the checksum has to be of what
    # will actually be served.
    raw = artifact_path.read_bytes()
    return write_map_sidecars(artifact_path, raw, fingerprint, node_count)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT_PATH)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the prepared response without writing anything.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even when the prepared response is already valid.",
    )
    args = parser.parse_args(argv)

    artifact_path: Path = args.artifact
    if not artifact_path.exists():
        print(f"ERROR: no projection artifact at {artifact_path}")
        print("Run `python -m api.generate_map_projection` first.")
        return 1

    meta, reason = verify_map_sidecars(artifact_path)

    if args.check:
        if meta is None:
            print(f"INVALID: {reason}")
            return 1
        print(f"artifact    : {artifact_path}")
        print(f"fingerprint : {meta['fingerprint'][:16]}")
        print(f"nodes       : {int(meta.get('node_count', 0)):,}")
        print(f"raw         : {meta['raw_size'] / 1048576:.1f} MB")
        print(f"gzip        : {meta['gzip_size'] / 1048576:.1f} MB "
              f"({meta['gzip_size'] / max(meta['raw_size'], 1):.0%})")
        print("RESULT: OK")
        return 0

    if meta is not None and not args.force:
        print(f"Already prepared and valid (fingerprint {meta['fingerprint'][:16]}).")
        print("Pass --force to rebuild anyway.")
        return 0

    if meta is None:
        print(f"rebuilding: {reason}")

    written = prepare(artifact_path)

    print(f"artifact    : {artifact_path}")
    print(f"fingerprint : {written['fingerprint'][:16]}")
    print(f"nodes       : {written['node_count']:,}")
    print(f"raw         : {written['raw_size'] / 1048576:.1f} MB")
    print(f"gzip        : {gzip_path_for(artifact_path).name}, "
          f"{written['gzip_size'] / 1048576:.1f} MB")
    print(f"metadata    : {meta_path_for(artifact_path).name}")

    confirmed, reason = verify_map_sidecars(artifact_path)
    if confirmed is None:
        print(f"RESULT: FAILED — {reason}")
        return 1
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
