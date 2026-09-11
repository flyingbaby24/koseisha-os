import type { MapNode } from "../api/mapTypes";
import type { ParameterScore, SearchResult } from "../api/types";
import type { AppStateSnapshot } from "./AppState";

/**
 * What the DetailPanel renders for the selected document.
 *
 * A document can be selected from the result list or straight from the map, and
 * those two sources carry different information. Rather than pretending a map
 * node is a search result, unavailable fields are explicitly `null` — the panel
 * then says so instead of showing a fabricated `0.0000` similarity.
 */
export interface SelectedDocumentView {
  doc_id: string;
  title: string;
  author: string;
  source: string;
  /** null when the document is not in the current result set. */
  similarity: number | null;
  /** null when no URL is known. Map nodes never carry one. */
  url: string | null;
  /** null when no parameter scores are available for this document. */
  parameters: readonly ParameterScore[] | null;
  /** Which store answered. Drives the "not in the current results" note. */
  origin: "search" | "map";
}

/**
 * Resolves a doc_id to something renderable, preferring the richer source.
 *
 * The DetailPanel asks this one object rather than searching several stores
 * itself, so there is a single place that decides what "the selected document"
 * means.
 */
export class DocumentSelectionResolver {
  /** Resolve the currently selected document, or null if nothing is selected. */
  resolve(snapshot: AppStateSnapshot): SelectedDocumentView | null {
    const docId = snapshot.selectedDocId;
    if (docId === null) {
      return null;
    }

    // A search result carries similarity, parameters and a URL, so it wins
    // whenever the selected document happens to be in the current results.
    const result = snapshot.results.find((candidate) => candidate.doc_id === docId);
    if (result) {
      return fromSearchResult(result);
    }

    const node = snapshot.mapNodes.find((candidate) => candidate.doc_id === docId);
    if (node) {
      return fromMapNode(node);
    }

    return null;
  }
}

export function fromSearchResult(result: SearchResult): SelectedDocumentView {
  return {
    doc_id: result.doc_id,
    title: result.title,
    author: result.author,
    source: result.source,
    similarity: Number.isFinite(result.similarity) ? result.similarity : null,
    url: result.url?.trim() ? result.url : null,
    parameters: result.parameters && result.parameters.length > 0 ? result.parameters : null,
    origin: "search",
  };
}

export function fromMapNode(node: MapNode): SelectedDocumentView {
  return {
    doc_id: node.doc_id,
    title: node.title,
    author: node.author,
    source: node.source,
    // Not a search result: there is no similarity to report, and inventing 0
    // would read as "completely dissimilar", which is a different claim.
    similarity: null,
    url: null,
    parameters: null,
    origin: "map",
  };
}
