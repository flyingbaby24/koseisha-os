/**
 * Mirrors `web/api/schemas.py`. Nothing here is shaped for the UI's
 * convenience — derived or display values belong in view models outside
 * `src/api/`.
 */

/** One Thought Composition axis. See PARAMETER_AXIS_ORDER for the canonical order. */
export interface ParameterScore {
  /** Axis name, e.g. "philosophy". */
  key: string;
  /**
   * Canonical scale: 0.0-1.0, and a document's or query's ten axes sum to 1.0.
   * This is a share of total affinity, not a 0-100 score. Never rescale it in
   * state; format it for display only.
   */
  value: number;
}

export interface SearchResult {
  doc_id: string;
  title: string;
  author: string;
  source: string;
  /** Ranking score from the active mode. Results arrive already sorted. */
  similarity: number;
  /** Omitted by the API when no URL could be resolved. */
  url?: string;
  /** Omitted when the document has no parameter scores. */
  parameters?: ParameterScore[];
}

export interface SearchResponse {
  results: SearchResult[];
  /** Profile of the query text itself. Null/absent when the API cannot compute it. */
  query_parameters?: ParameterScore[];
}

export interface HealthResponse {
  status: string;
  backend: string;
}

/** One startup condition reported by `GET /ready`. */
export interface ReadinessCheck {
  name: string;
  /** "ok" | "failed" | "pending" | "deferred". Kept as a string: the set is the server's to grow. */
  status: string;
  detail?: string;
}

/**
 * Mirrors `web/api/readiness.py`.
 *
 * Served with 200 when ready and 503 when not; both carry this body, because
 * "not ready" needs to say which condition is missing.
 */
export interface ReadinessResponse {
  ready: boolean;
  deployment_mode?: string;
  corpus_version?: string;
  document_count?: number;
  warmup?: string;
  checks?: ReadinessCheck[];
  blocked_by?: string[];
}

/**
 * Public search modes. The service calls its vector mode `embedding`
 * internally; that name is deliberately not exposed here.
 */
export type SearchMode = "semantic" | "keyword" | "hybrid";

export const SEARCH_MODES: readonly SearchMode[] = ["semantic", "keyword", "hybrid"] as const;

export function isSearchMode(value: string): value is SearchMode {
  return (SEARCH_MODES as readonly string[]).includes(value);
}

export interface SearchRequest {
  q: string;
  top?: number;
  mode?: SearchMode;
  /** Empty string means "all sources" and is omitted from the query string. */
  source?: string;
  /** Empty string means "no filter" and is omitted from the query string. */
  filter?: string;
  /** Optional document-origin similarity search. */
  target_doc_id?: string;
  /** Required by the API only when target_doc_id names a personal document. */
  user_email?: string;
}
