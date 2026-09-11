"""The loaded corpus, with its embedding matrix held once.

Before T7 every search rebuilt the embedding matrix. `work_similarity_by_vector`
received a DataFrame, called `frame["_embedding_vec"].to_list()`, and
`np.stack`ed 63,891 separate arrays into a fresh 93.6 MB block — about 60 ms of
pure copying per request, to reproduce something that had not changed since
startup.

`SearchCorpus` owns that block instead: one contiguous matrix, one row-norm
vector, built once per corpus version and read by every search (T7 §10-§11).

Two properties this type exists to guarantee:

- **Row `i` of `matrix` is row `i` of `frame`.** Everything else depends on
  that, so it is asserted at construction rather than assumed.
- **Nothing mutates it.** Searches filter the frame and index into the matrix;
  no search path writes to either. There is no global mutable state and no
  lazy re-derivation — the object is built in one place and replaced only when
  the corpus version changes.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from search_utils import MATRIX_ROW_COLUMN


@dataclass(frozen=True)
class SearchCorpus:
    """A corpus version's documents and their embeddings, ready to rank."""

    frame: pd.DataFrame
    matrix: np.ndarray
    norms: np.ndarray
    corpus_version: str = ""

    def __post_init__(self) -> None:
        # An empty matrix is the explicit "no prepared matrix" state, used when
        # the frame is empty or its vectors are ragged. Ranking then falls back
        # to stacking per request, which is slower and always correct. It is a
        # distinct case from a matrix that exists but does not line up, which is
        # a bug and must not be constructible.
        if self.matrix.size == 0:
            if len(self.norms):
                raise ValueError("A corpus with no matrix must have no norms.")
            return

        if self.matrix.ndim != 2:
            raise ValueError("SearchCorpus matrix must be two-dimensional.")
        if len(self.frame) != len(self.matrix):
            raise ValueError(
                f"SearchCorpus frame has {len(self.frame):,} rows but the matrix has "
                f"{len(self.matrix):,}. Row alignment is what every ranking result "
                "depends on."
            )
        if len(self.norms) != len(self.matrix):
            raise ValueError("SearchCorpus norms must have one entry per row.")

    @property
    def has_matrix(self) -> bool:
        """Whether a prepared matrix is available for ranking."""
        return bool(self.matrix.size)

    @property
    def document_count(self) -> int:
        return len(self.frame)

    @property
    def dimension(self) -> int:
        return int(self.matrix.shape[1]) if self.matrix.ndim == 2 else 0

    @property
    def matrix_bytes(self) -> int:
        return int(self.matrix.nbytes)


def build_search_corpus(frame: pd.DataFrame, corpus_version: str = "") -> SearchCorpus:
    """Stack the per-row vectors into one matrix, once.

    Returns a corpus with an empty matrix when the frame is empty or its
    vectors are ragged. Ragged vectors are a data defect, and the ranking path
    still has its per-row fallback for them; silently stacking a partial set
    would be worse than not stacking at all.
    """
    if frame is None or frame.empty or "_embedding_vec" not in frame.columns:
        return SearchCorpus(
            frame=frame if frame is not None else pd.DataFrame(),
            matrix=np.zeros((0, 0), dtype=np.float32),
            norms=np.zeros((0,), dtype=np.float64),
            corpus_version=corpus_version,
        )

    vectors = frame["_embedding_vec"].to_list()
    lengths = {len(vector) for vector in vectors}
    if len(lengths) != 1:
        return SearchCorpus(
            frame=frame,
            matrix=np.zeros((0, 0), dtype=np.float32),
            norms=np.zeros((0,), dtype=np.float64),
            corpus_version=corpus_version,
        )

    # float32 and C-contiguous, exactly what np.stack produced per request, so
    # the arithmetic downstream sees an identical array.
    matrix = np.ascontiguousarray(np.stack(vectors), dtype=np.float32)

    # Norms over the full matrix. Identical to what the per-request path
    # computed when no filter was applied, which is the common case; a filtered
    # search recomputes over its subset so that path stays identical too.
    norms = np.linalg.norm(matrix, axis=1)

    # Stamp each row with its matrix position. This is what makes a *filtered*
    # frame usable: the filters reset the index, so nothing else in the frame
    # still says where a row came from.
    stamped = frame.copy()
    stamped[MATRIX_ROW_COLUMN] = np.arange(len(stamped), dtype=np.int64)

    # Re-point the per-row vectors at the matrix instead of leaving 63,891
    # independently allocated arrays beside it. `list(matrix)` yields row
    # *views*, so the column and the matrix are one 93.6 MB block rather than
    # two, and every value is the same object in memory — identical by
    # construction, not merely equal.
    #
    # Safe because nothing in the search path writes to a vector: ranking reads
    # the matrix, and the ragged fallback copies before it stacks.
    stamped["_embedding_vec"] = list(matrix)

    return SearchCorpus(
        frame=stamped, matrix=matrix, norms=norms, corpus_version=corpus_version
    )


def positions_within(frame: pd.DataFrame, corpus: SearchCorpus) -> np.ndarray | None:
    """Row positions of `frame` within `corpus.matrix`, or None.

    A thin wrapper so callers can ask the question of a corpus rather than of a
    row count. The rule itself lives in `search_utils`, which is shared with
    the Streamlit and Unity paths and must not import this package.
    """
    from search_utils import subset_positions

    return subset_positions(frame, len(corpus.matrix))


def strip_internal_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Drop corpus bookkeeping columns. For callers that hand a frame outward."""
    from search_utils import INTERNAL_COLUMNS

    present = [column for column in INTERNAL_COLUMNS if column in frame.columns]
    return frame.drop(columns=present) if present else frame
