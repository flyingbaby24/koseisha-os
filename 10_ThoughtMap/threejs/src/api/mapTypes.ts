/**
 * Mirrors the `/map` half of `web/api/schemas.py`.
 *
 * Deliberately separate from SearchResult. A document has two different
 * representations — its place in the thought space, and its standing in one
 * search — and they join on `doc_id`, not by being the same object. T4 relies
 * on that join.
 */

export interface MapProjectionMetadata {
  generated_at: string;
  dataset_fingerprint: string;
  document_count: number;
  embedding_dimension: number;
  dimensions: number;
  algorithm: string;
  metric: string;
  n_neighbors: number;
  min_dist: number;
  random_seed: number;
  n_components?: number | null;
  cluster_algorithm?: string | null;
  cluster_count?: number | null;
}

export interface MapNode {
  doc_id: string;
  title: string;
  author: string;
  source: string;
  /** Projection-space coordinates. Never rescaled in state. */
  x: number;
  y: number;
  z: number;
  cluster?: number | null;
}

export interface MapResponse {
  schema_version: number;
  projection: MapProjectionMetadata;
  nodes: MapNode[];
}

/** Schema version this client understands. */
export const SUPPORTED_MAP_SCHEMA_VERSION = 1;

export function isMapNode(value: unknown): value is MapNode {
  if (!value || typeof value !== "object") {
    return false;
  }
  const node = value as Partial<MapNode>;
  return (
    typeof node.doc_id === "string" &&
    node.doc_id.length > 0 &&
    Number.isFinite(node.x) &&
    Number.isFinite(node.y) &&
    Number.isFinite(node.z)
  );
}
