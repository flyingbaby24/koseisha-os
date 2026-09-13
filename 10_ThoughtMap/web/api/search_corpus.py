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
    #: (N, K) float64 Thought Composition values, row-aligned with `frame`.
    #:
    #: Replaces a `parameter_scores` column of 63,891 ten-key Python dicts.
    #: The same numbers cost 17.1 MB as dicts and 4.9 MB here, and only the
    #: handful of rows a search returns ever need to become dicts again.
    parameter_matrix: np.ndarray | None = None
    #: Axis names, in the order of `parameter_matrix`'s columns.
    parameter_axes: tuple[str, ...] = ()
    #: How many rows arrived with a non-empty profile.
    #:
    #: Counted while the dicts still exist, because afterwards they do not: a
    #: document with no profile and a document whose every axis is genuinely
    #: 0.0 are the same row of zeros in the matrix, and integrity checks need
    #: to tell them apart.
    parameter_coverage: int = 0

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

    def parameters_for(self, position: int) -> list[dict] | None:
        """The Thought Composition of one row, in canonical axis order.

        Built on demand: a search returns at most 50 rows, so this runs 50
        times per request instead of 63,891 times per load.
        """
        if self.parameter_matrix is None or not self.parameter_axes:
            return None
        if position < 0 or position >= len(self.parameter_matrix):
            return None

        values = self.parameter_matrix[position]
        return [
            {"key": axis, "value": float(value)}
            for axis, value in zip(self.parameter_axes, values)
        ]

    def dominant_axis(self) -> np.ndarray | None:
        """Index of each row's highest-scoring axis.

        Ties resolve to the lowest index, which is what `max(dict, key=...)`
        did over an insertion-ordered dict built in this same axis order.
        """
        if self.parameter_matrix is None or not len(self.parameter_matrix):
            return None
        return self.parameter_matrix.argmax(axis=1)

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


def build_search_corpus(
    frame: pd.DataFrame,
    corpus_version: str = "",
    matrix: np.ndarray | None = None,
) -> SearchCorpus:
    """Stack the per-row vectors into one matrix, once.

    Returns a corpus with an empty matrix when the frame is empty or its
    vectors are ragged. Ragged vectors are a data defect, and the ranking path
    still has its per-row fallback for them; silently stacking a partial set
    would be worse than not stacking at all.

    `matrix` lets a caller that already holds a contiguous, row-aligned float32
    matrix hand it over instead — which the repository does when the vector
    cache was already in corpus order. Stacking it again would produce an array
    equal to the one already in hand, at the cost of holding both: +93.6 MB of
    transient for no change in value. It is validated, not trusted: row count,
    dimensionality and dtype are all checked, because a matrix that does not
    line up with the frame produces confident, plausible, wrong rankings.
    """
    if frame is None or frame.empty:
        return SearchCorpus(
            frame=frame if frame is not None else pd.DataFrame(),
            matrix=np.zeros((0, 0), dtype=np.float32),
            norms=np.zeros((0,), dtype=np.float64),
            corpus_version=corpus_version,
        )

    if matrix is None:
        if "_embedding_vec" not in frame.columns:
            return SearchCorpus(
                frame=frame,
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

        # float32 and C-contiguous, exactly what np.stack produced per request,
        # so the arithmetic downstream sees an identical array.
        matrix = np.ascontiguousarray(np.stack(vectors), dtype=np.float32)
    else:
        if matrix.ndim != 2:
            raise ValueError(
                f"A prepared corpus matrix must be two-dimensional, got {matrix.ndim}."
            )
        if len(matrix) != len(frame):
            raise ValueError(
                f"A prepared corpus matrix has {len(matrix):,} rows but the frame "
                f"has {len(frame):,}. Row alignment is what every ranking result "
                "depends on."
            )
        if matrix.dtype != np.float32:
            raise ValueError(
                f"A prepared corpus matrix must be float32, got {matrix.dtype}. "
                "Converting here would change the values ranking depends on."
            )
        # Contiguity is a performance property, not a correctness one, and the
        # cache always supplies a contiguous array. Normalising costs nothing
        # when it is already contiguous and keeps BLAS off the slow path if a
        # future caller is careless.
        matrix = np.ascontiguousarray(matrix)

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

    axes, parameters, coverage = _parameter_matrix(stamped)
    if parameters is not None:
        # The dicts have been distilled into the matrix; keeping both would
        # defeat the point.
        stamped = stamped.drop(columns=["parameter_scores"])

    return SearchCorpus(
        frame=stamped,
        matrix=matrix,
        norms=norms,
        corpus_version=corpus_version,
        parameter_matrix=parameters,
        parameter_axes=axes,
        parameter_coverage=coverage,
    )


def _parameter_matrix(
    frame: pd.DataFrame,
) -> tuple[tuple[str, ...], np.ndarray | None, int]:
    """Fold the per-row parameter dicts into one array, and count them.

    Axis order is taken from the first row that has a profile and then applied
    to every row, so column *j* means the same axis for all documents - which
    is what makes `dominant_axis` equivalent to the old per-row `max()`.

    A missing axis becomes 0.0. In this corpus every one of the 63,891 rows
    carries all ten finite values, so that fill is unreachable here; it exists
    so a partial profile degrades to a low score rather than an exception.
    """
    if "parameter_scores" not in frame.columns:
        return (), None, 0

    values = frame["parameter_scores"]
    axes: tuple[str, ...] = ()
    for entry in values:
        if isinstance(entry, dict) and entry:
            axes = tuple(entry.keys())
            break
    if not axes:
        return (), None, 0

    # float64, not float32: the dicts held Python floats, and the radar is a
    # user-visible number. 2.4 MB more buys bit-identical values instead of a
    # ~2.5e-08 drift, which is a poor trade to make on someone's behalf.
    matrix = np.zeros((len(frame), len(axes)), dtype=np.float64)
    index = {axis: position for position, axis in enumerate(axes)}
    coverage = 0
    for row, entry in enumerate(values):
        if not isinstance(entry, dict) or not entry:
            continue
        coverage += 1
        for axis, value in entry.items():
            position = index.get(axis)
            if position is not None:
                matrix[row, position] = value

    return axes, matrix, coverage


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
