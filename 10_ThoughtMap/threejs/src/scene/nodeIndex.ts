import type { MapNode } from "../api/mapTypes";

/**
 * The identity bridge between GPU buffers and documents.
 *
 * Every node lives at one index in the position/color buffers. T4's picking
 * resolves a hit to a buffer index and needs to get from there to a `doc_id`,
 * and from a search result's `doc_id` back to an index. Object names are not
 * usable for this — the whole cloud is a single object — so the mapping is
 * kept explicitly here and stays valid for as long as the buffers do.
 */
export interface NodeIndex {
  /** Buffer index -> doc_id. */
  readonly nodeIndexToDocId: readonly string[];
  /** doc_id -> buffer index. */
  readonly docIdToNodeIndex: ReadonlyMap<string, number>;
  /** Buffer index -> the node it came from. */
  readonly nodes: readonly MapNode[];
}

export function buildNodeIndex(nodes: readonly MapNode[]): NodeIndex {
  const nodeIndexToDocId: string[] = new Array(nodes.length);
  const docIdToNodeIndex = new Map<string, number>();

  for (let index = 0; index < nodes.length; index += 1) {
    const docId = nodes[index]!.doc_id;
    nodeIndexToDocId[index] = docId;
    // First occurrence wins. The generator rejects duplicate doc_ids, so this
    // only matters if a hand-edited artifact slips through.
    if (!docIdToNodeIndex.has(docId)) {
      docIdToNodeIndex.set(docId, index);
    }
  }

  return { nodeIndexToDocId, docIdToNodeIndex, nodes };
}

export function docIdAt(index: NodeIndex, bufferIndex: number): string | null {
  return index.nodeIndexToDocId[bufferIndex] ?? null;
}

export function indexOfDocId(index: NodeIndex, docId: string): number | null {
  const found = index.docIdToNodeIndex.get(docId);
  return found === undefined ? null : found;
}
