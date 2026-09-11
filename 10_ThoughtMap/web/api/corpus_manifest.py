"""Read and enforce the canonical corpus manifest.

The embedding artifact is ~542 MB and lives outside version control, while a
*stale* 41 MB `embeddings_master.csv` remains tracked in the repository from
before the T4.6 recovery. That file covers 4,584 of the 63,891 canonical
documents — 7% of the corpus — and joins cleanly, so nothing would look broken
if it were used by mistake. Search would simply be missing 93% of everything.

The manifest exists so that cannot happen quietly.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger("thoughtmap.manifest")

MANIFEST_FILENAME = "corpus_manifest.json"


class CorpusMismatchError(RuntimeError):
    """The resolved embedding artifact is not the one the manifest describes."""


@dataclass(frozen=True)
class CorpusManifest:
    corpus_version: str
    document_count: int
    embedding_count: int
    embedding_dimension: int
    embedding_model: str
    embedding_artifact_sha256: str
    embedding_artifact_bytes: int
    embedding_artifact_filename: str
    documents_sha256: str
    sources: dict[str, int]
    path: Path

    @classmethod
    def load(cls, directory: Path) -> "CorpusManifest | None":
        """Read the manifest beside the documents, or None if absent.

        Absent is legitimate: a corpus predating T4.6 has no manifest, and the
        historical behaviour still applies to it.
        """
        path = Path(directory) / MANIFEST_FILENAME
        if not path.exists():
            return None

        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CorpusMismatchError(f"Corpus manifest is not valid JSON: {path}") from exc

        return cls(
            corpus_version=str(data.get("corpus_version", "")),
            document_count=int(data.get("document_count", 0)),
            embedding_count=int(data.get("embedding_count", 0)),
            embedding_dimension=int(data.get("embedding_dimension", 0)),
            embedding_model=str(data.get("embedding_model", "")),
            embedding_artifact_sha256=str(data.get("embedding_artifact_sha256", "")),
            embedding_artifact_bytes=int(data.get("embedding_artifact_bytes", 0)),
            embedding_artifact_filename=str(data.get("embedding_artifact_filename", "")),
            documents_sha256=str(data.get("documents_sha256", "")),
            sources={str(k): int(v) for k, v in (data.get("sources") or {}).items()},
            path=path,
        )

    def check_artifact_file(self, artifact: Path) -> None:
        """Cheap pre-read check: the file must be the size the manifest recorded.

        Instant, and enough to catch the stale tracked snapshot (41 MB against
        an expected 542 MB) before spending a minute reading the wrong file.
        """
        if not self.embedding_artifact_bytes:
            return

        actual = artifact.stat().st_size
        if actual == self.embedding_artifact_bytes:
            return

        raise CorpusMismatchError(
            f"Embedding artifact does not match the corpus manifest.\n"
            f"  artifact : {artifact}\n"
            f"  size     : {actual:,} bytes\n"
            f"  expected : {self.embedding_artifact_bytes:,} bytes "
            f"({self.embedding_artifact_filename})\n"
            f"  manifest : {self.path}\n"
            f"Set THOUGHTMAP_EMBEDDINGS_PATH to the canonical artifact. The "
            f"embeddings_master.csv tracked in the repository is a legacy "
            f"snapshot covering only part of the corpus."
        )

    def check_loaded_corpus(self, searchable: int, documents: int) -> None:
        """Post-join check: every loaded document must have an embedding.

        Two different problems, treated differently:

        - The documents master disagreeing with the manifest means the manifest
          is stale. That is a bookkeeping issue and only warns, because the
          corpus may have grown on purpose.
        - Documents without embeddings means the wrong artifact is loaded.
          Coverage is measured against the documents actually present, not the
          recorded count, so this stays correct for a corpus of any size.
        """
        if not self.document_count:
            return

        if documents != self.document_count:
            logger.warning(
                "Documents master has %d rows but the manifest records %d. "
                "Regenerate the manifest if the corpus changed deliberately.",
                documents,
                self.document_count,
            )

        if not documents or searchable == documents:
            return

        raise CorpusMismatchError(
            f"Only {searchable:,} of {documents:,} documents have an embedding, so "
            f"search would silently cover {100 * searchable / documents:.1f}% of the "
            f"corpus.\n"
            f"Set THOUGHTMAP_EMBEDDINGS_PATH to the artifact named in "
            f"{self.path} ({self.embedding_artifact_filename})."
        )

    def check_model(self, models: set[str]) -> None:
        """Every vector must come from the model the manifest names."""
        found = {m.split("/")[-1] for m in models if m}
        expected = self.embedding_model.split("/")[-1]

        if not found or not expected:
            return

        if found != {expected}:
            raise CorpusMismatchError(
                f"Embedding artifact uses model(s) {sorted(found)} but the manifest "
                f"records {expected!r}. Mixing embedding models in one cosine space "
                f"produces meaningless similarity."
            )

    def verify_artifact_hash(self, artifact: Path) -> bool:
        """Full content check. Seconds on a 542 MB file, so opt-in only."""
        if not self.embedding_artifact_sha256:
            return True

        digest = hashlib.sha256()
        with artifact.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)

        return digest.hexdigest() == self.embedding_artifact_sha256
