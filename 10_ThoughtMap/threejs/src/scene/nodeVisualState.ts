/**
 * How each document node should look, derived from application state.
 *
 * Pure: no three.js, no DOM, no GPU. The result is two typed arrays the
 * renderer uploads as attributes, so changing search results never rebuilds
 * geometry — only these values change.
 */

/**
 * Visual states in ascending precedence. A node gets exactly one, and higher
 * always wins, so the outcome never depends on evaluation order.
 */
export const NodeState = {
  /** Not a search result, while a search is active. Still visible. */
  Dimmed: 0,
  /** No search active — the resting appearance of the whole map. */
  Normal: 1,
  /**
   * In the user's Personal Library. Sits *below* result emphasis on purpose:
   * a large library must never drown out the handful of search results.
   */
  Saved: 2,
  /** In the current result set. */
  Result: 3,
  /** Rank 1 of the current result set. */
  TopResult: 4,
  /** Under the pointer. Transient, never selection. */
  Hovered: 5,
  /** The selected document. Highest priority, and stable across searches. */
  Selected: 6,
} as const;

export type NodeStateValue = (typeof NodeState)[keyof typeof NodeState];

export interface VisualStateInput {
  nodeCount: number;
  docIdToNodeIndex: ReadonlyMap<string, number>;
  /** Result doc_ids in the API's rank order. Empty when no search is active. */
  resultDocIds: readonly string[];
  /**
   * Whether a search currently defines emphasis. False leaves every node at
   * Normal; true dims non-results. Kept separate from `resultDocIds.length`
   * so a zero-result search can dim everything uniformly.
   */
  hasSearchEmphasis: boolean;
  selectedDocId: string | null;
  hoveredDocId: string | null;
  /** doc_ids in the Personal Library. Marked below result emphasis. */
  savedDocIds?: ReadonlySet<string>;
}

export interface VisualState {
  /** One NodeState per node. */
  state: Float32Array;
  /**
   * Rank emphasis in 0..1 for result nodes; 0 otherwise. Restrained: it
   * scales brightness and size slightly, and never moves anything.
   */
  emphasis: Float32Array;
  /** Result doc_ids that exist in the current projection. */
  joinedCount: number;
  /** Result doc_ids with no node in the current projection. */
  missingDocIds: string[];
}

/** Weakest emphasis given to the last-ranked result. */
const MIN_RESULT_EMPHASIS = 0.55;

/**
 * Build the per-node visual state.
 *
 * O(nodes + results): one pass to set the base state, then one pass over the
 * results. No per-frame work and no string lookups beyond the result list.
 */
export function computeNodeVisualState(input: VisualStateInput): VisualState {
  const {
    nodeCount,
    docIdToNodeIndex,
    resultDocIds,
    hasSearchEmphasis,
    selectedDocId,
    hoveredDocId,
    savedDocIds,
  } = input;

  const state = new Float32Array(nodeCount);
  const emphasis = new Float32Array(nodeCount);

  // Base layer: everything dims under an active search, otherwise rests.
  state.fill(hasSearchEmphasis ? NodeState.Dimmed : NodeState.Normal);

  // Saved documents are marked first so result emphasis, hover and selection
  // all overwrite them. O(saved), and only for saved works that are in the map.
  if (savedDocIds && savedDocIds.size > 0) {
    for (const docId of savedDocIds) {
      const index = docIdToNodeIndex.get(docId);
      if (index !== undefined) {
        state[index] = NodeState.Saved;
      }
    }
  }

  const missingDocIds: string[] = [];
  let joinedCount = 0;

  const resultCount = resultDocIds.length;
  for (let rank = 0; rank < resultCount; rank += 1) {
    const docId = resultDocIds[rank]!;
    const index = docIdToNodeIndex.get(docId);

    if (index === undefined) {
      // A result with no node in this projection. Not an error: the artifact
      // may predate the document. It stays fully usable in the result list.
      missingDocIds.push(docId);
      continue;
    }

    joinedCount += 1;
    state[index] = rank === 0 ? NodeState.TopResult : NodeState.Result;
    emphasis[index] =
      resultCount === 1
        ? 1
        : 1 - (rank / (resultCount - 1)) * (1 - MIN_RESULT_EMPHASIS);
  }

  // Hover and selection sit above result state, selection highest, so a
  // selected document stays unmistakable even outside the result set.
  if (hoveredDocId !== null) {
    const index = docIdToNodeIndex.get(hoveredDocId);
    if (index !== undefined) {
      state[index] = NodeState.Hovered;
    }
  }

  if (selectedDocId !== null) {
    const index = docIdToNodeIndex.get(selectedDocId);
    if (index !== undefined) {
      state[index] = NodeState.Selected;
    }
  }

  return { state, emphasis, joinedCount, missingDocIds };
}

/** Diagnostics for the search ↔ map join, reported in development. */
export interface JoinMetrics {
  resultsReturned: number;
  mapJoins: number;
  missingJoins: number;
  missingDocIds: string[];
}

export function joinMetrics(
  resultDocIds: readonly string[],
  docIdToNodeIndex: ReadonlyMap<string, number>,
): JoinMetrics {
  const missingDocIds = resultDocIds.filter((docId) => !docIdToNodeIndex.has(docId));
  return {
    resultsReturned: resultDocIds.length,
    mapJoins: resultDocIds.length - missingDocIds.length,
    missingJoins: missingDocIds.length,
    missingDocIds,
  };
}
