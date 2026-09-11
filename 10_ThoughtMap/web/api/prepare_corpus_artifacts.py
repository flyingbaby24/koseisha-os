"""Put the heavy corpus artifacts in place, verifiably.

The embedding artifact is ~542 MB and the parsed-vector cache ~108 MB. Neither
belongs in Git (T6 #3, #5). This script is the one supported way to get them
onto a machine, and it refuses to leave anything unverified in place.

    # verify what is already there
    python -m api.prepare_corpus_artifacts

    # copy from a mounted volume or a local path
    python -m api.prepare_corpus_artifacts --source D:/ThoughtMap/master/thoughtmap_canonical_embeddings.csv

    # fetch from object storage over HTTPS
    python -m api.prepare_corpus_artifacts --source https://example/thoughtmap_canonical_embeddings.csv

    # build the vector cache now, so the first start is fast
    python -m api.prepare_corpus_artifacts --build-cache

    # the ONNX query encoder, verified the same way
    python -m api.prepare_corpus_artifacts --encoder-source https://example/encoder
    python -m api.prepare_corpus_artifacts --encoder          # verify what is there

Properties this guarantees:

- **Content-addressed.** The manifest's SHA-256 is checked after every fetch or
  copy. A truncated download is detected here, not by a search that quietly
  returns fewer results.
- **Reproducible.** The same manifest and the same source always produce the
  same bytes at the same path.
- **No machine-specific path.** The destination comes from
  THOUGHTMAP_EMBEDDINGS_PATH; nothing is hard-coded and nothing is guessed.
- **Never silently stale.** A file that does not match the manifest is reported
  and, unless --force is given, left alone rather than half-replaced.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import time
import urllib.request
from pathlib import Path


CHUNK = 4 * 1024 * 1024


def _mb(value: float) -> str:
    return f"{value / (1024 * 1024):,.1f} MB"


def _sha256(path: Path, label: str = "hashing") -> str:
    digest = hashlib.sha256()
    total = path.stat().st_size
    read = 0
    started = time.perf_counter()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK)
            if not chunk:
                break
            digest.update(chunk)
            read += len(chunk)
            _progress(label, read, total, started)

    print()
    return digest.hexdigest()


def _progress(label: str, done: int, total: int, started: float) -> None:
    if not total:
        return
    percent = 100.0 * done / total
    elapsed = time.perf_counter() - started
    rate = done / elapsed / (1024 * 1024) if elapsed > 0 else 0.0
    print(f"\r  {label}: {percent:5.1f}%  {_mb(done)} / {_mb(total)}  {rate:5.1f} MB/s", end="")


def _download(url: str, destination: Path) -> None:
    """Fetch to a temporary file, then move into place.

    Never writes the destination incrementally: an interrupted download must
    not leave a partial artifact that looks like the real one.
    """
    temporary = destination.with_suffix(destination.suffix + ".part")
    started = time.perf_counter()

    with urllib.request.urlopen(url) as response:  # noqa: S310 - operator-supplied URL
        total = int(response.headers.get("Content-Length") or 0)
        read = 0
        with temporary.open("wb") as handle:
            while True:
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                handle.write(chunk)
                read += len(chunk)
                _progress("downloading", read, total, started)
    print()
    temporary.replace(destination)


def _copy(source: Path, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".part")
    started = time.perf_counter()
    total = source.stat().st_size
    copied = 0

    with source.open("rb") as reader, temporary.open("wb") as writer:
        while True:
            chunk = reader.read(CHUNK)
            if not chunk:
                break
            writer.write(chunk)
            copied += len(chunk)
            _progress("copying", copied, total, started)
    print()
    temporary.replace(destination)


def prepare_encoder(source: str | None, force: bool, skip_checksum: bool) -> int:
    """Put the ONNX query encoder in place, verified against its manifest.

    The same discipline as the embedding artifact, for the same reason: an
    encoder that is not the one the equivalence suite validated has not been
    validated at all (T7 #5). A directory is fetched as a set of files, each
    checked against the manifest that travels with it.
    """
    from .config import get_settings
    from .query_encoder import (
        MANIFEST_FILENAME,
        QueryEncoderUnavailableError,
        encoder_manifest,
        verify_encoder_artifacts,
    )

    settings = get_settings()
    destination = settings.encoder_dir

    if destination is None:
        print("ERROR: THOUGHTMAP_ENCODER_DIR is not set.")
        print("Set it to where the query encoder should live, for example:")
        print("  export THOUGHTMAP_ENCODER_DIR=/data/encoder")
        return 1

    print(f"encoder directory: {destination}")

    if source:
        if destination.exists() and any(destination.iterdir()) and not force:
            print("Already present; not overwriting. Use --force to replace it.")
        else:
            destination.mkdir(parents=True, exist_ok=True)
            source_path = Path(source)
            if source.startswith(("http://", "https://")):
                # A directory is several files; fetch the manifest first and
                # take the file list from it, so nothing is guessed.
                base = source.rstrip("/")
                print(f"source           : {base}")
                _download(f"{base}/{MANIFEST_FILENAME}", destination / MANIFEST_FILENAME)
                manifest = encoder_manifest(destination) or {}
                for name in (manifest.get("files") or {}):
                    print(f"  fetching {name}")
                    _download(f"{base}/{name}", destination / name)
            else:
                if not source_path.exists():
                    print(f"ERROR: source not found: {source_path}")
                    return 1
                print(f"source           : {source_path}")
                for item in sorted(source_path.iterdir()):
                    if item.is_file():
                        print(f"  copying {item.name}")
                        _copy(item, destination / item.name)

    if not destination.exists() or not any(destination.iterdir()):
        print()
        print("ERROR: the encoder is not present and no --encoder-source was given.")
        print("Export one with `python -m api.prepare_query_encoder --out DIR`,")
        print("publish it, and fetch it here.")
        return 1

    try:
        verify_encoder_artifacts(destination, verify_checksums=not skip_checksum)
    except QueryEncoderUnavailableError as exc:
        print()
        print(f"ERROR: {exc}")
        return 1

    manifest = encoder_manifest(destination) or {}
    total = sum(
        int(entry.get("bytes", 0)) for entry in (manifest.get("files") or {}).values()
    )
    print(f"model_id         : {manifest.get('model_id', '')}")
    print(f"revision         : {manifest.get('revision', '') or '(unrecorded)'}")
    print(f"size             : {_mb(total)}")
    print("checksum         : " + ("SKIPPED" if skip_checksum else "OK"))
    print()
    print("ENCODER READY")
    return 0


def prepare(
    source: str | None,
    build_cache: bool,
    force: bool,
    skip_checksum: bool,
) -> int:
    from .config import get_settings
    from .corpus_manifest import CorpusManifest
    from .repositories import _official_documents_path, _vector_cache_path

    settings = get_settings()
    documents_dir = _official_documents_path(settings.db_dir).parent
    manifest = CorpusManifest.load(documents_dir)

    if manifest is None:
        print(f"ERROR: no corpus_manifest.json in {documents_dir}.")
        print("The manifest is tracked in Git and describes the artifact to fetch.")
        return 1

    print(f"corpus version : {manifest.corpus_version or '(unset)'}")
    print(f"documents      : {manifest.document_count:,}")
    print(f"artifact       : {manifest.embedding_artifact_filename}")
    print(f"expected bytes : {manifest.embedding_artifact_bytes:,}")
    print(f"expected sha256: {manifest.embedding_artifact_sha256}")
    print()

    destination = settings.embeddings_path
    if destination is None:
        print("ERROR: THOUGHTMAP_EMBEDDINGS_PATH is not set.")
        print("Set it to where the artifact should live, for example:")
        print(f"  export THOUGHTMAP_EMBEDDINGS_PATH=/data/{manifest.embedding_artifact_filename}")
        return 1

    print(f"destination    : {destination}")

    if source and destination.exists() and not force:
        print("Already present; not overwriting. Use --force to replace it.")
        source = None

    if source:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.startswith(("http://", "https://")):
            print(f"source         : {source}")
            _download(source, destination)
        else:
            source_path = Path(source)
            if not source_path.exists():
                print(f"ERROR: source not found: {source_path}")
                return 1
            print(f"source         : {source_path}")
            _copy(source_path, destination)

    if not destination.exists():
        print()
        print("ERROR: the artifact is not present and no --source was given.")
        print("Provide --source <path-or-url>, or mount a volume that already has it.")
        return 1

    actual_bytes = destination.stat().st_size
    if actual_bytes != manifest.embedding_artifact_bytes:
        print()
        print(f"ERROR: size mismatch. found {actual_bytes:,}, expected "
              f"{manifest.embedding_artifact_bytes:,}.")
        print("This is the failure mode the manifest exists to catch: a partial or")
        print("superseded artifact would otherwise serve a fraction of the corpus.")
        return 1
    print(f"size           : OK ({actual_bytes:,} bytes)")

    if skip_checksum:
        print("checksum       : SKIPPED (--skip-checksum)")
    else:
        digest = _sha256(destination, "verifying")
        if digest != manifest.embedding_artifact_sha256:
            print(f"ERROR: checksum mismatch.\n  found    {digest}\n  expected "
                  f"{manifest.embedding_artifact_sha256}")
            return 1
        print("checksum       : OK")

    cache = _vector_cache_path(destination)
    if build_cache:
        print()
        print("Building the parsed-vector cache. This reads the artifact once so that")
        print("every later start does not have to.")
        from .repositories import CsvSearchIndexRepository

        if cache.exists():
            cache.unlink()
        started = time.perf_counter()
        repository = CsvSearchIndexRepository(settings.db_dir, settings.embeddings_path)
        index = repository.load_index()
        print(f"  parsed {len(index):,} documents in {time.perf_counter() - started:,.1f}s")

    if cache.exists():
        print(f"vector cache   : present ({_mb(cache.stat().st_size)})")
    else:
        print("vector cache   : absent (the first start will build it)")

    print()
    print("READY")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--source",
        default=None,
        help="Local path or http(s) URL to fetch the embedding artifact from.",
    )
    parser.add_argument(
        "--encoder-source",
        default=None,
        help=(
            "Local directory or http(s) base URL to fetch the ONNX query encoder "
            "from. Implies --encoder."
        ),
    )
    parser.add_argument(
        "--encoder",
        action="store_true",
        help="Prepare and verify the query encoder instead of the embeddings.",
    )
    parser.add_argument(
        "--build-cache",
        action="store_true",
        help="Parse the artifact now and write the vector cache.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an artifact that is already present.",
    )
    parser.add_argument(
        "--skip-checksum",
        action="store_true",
        help="Skip the SHA-256 check. Only for a slow machine with a trusted mount.",
    )
    args = parser.parse_args(argv)

    if args.encoder or args.encoder_source:
        return prepare_encoder(args.encoder_source, args.force, args.skip_checksum)

    return prepare(args.source, args.build_cache, args.force, args.skip_checksum)


if __name__ == "__main__":
    sys.exit(main())
