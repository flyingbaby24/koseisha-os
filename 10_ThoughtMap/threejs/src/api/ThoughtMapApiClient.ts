import { API_BASE_URL, parseFeatures, type DeploymentFeatures } from "../config/runtime";
import { ApiError, extractDetail, messageForStatus, type ApiContext } from "./errors";
import { SUPPORTED_MAP_SCHEMA_VERSION, type MapResponse } from "./mapTypes";
import type { HealthResponse, ReadinessResponse, SearchRequest, SearchResponse } from "./types";

/**
 * Where the API lives.
 *
 * `/api` same-origin by default: proxied by Vite in dev, by the reverse proxy
 * in a same-origin deployment. A separately hosted API overrides it with
 * VITE_THOUGHTMAP_API_BASE_URL at build time (T6 #32).
 */
export const DEFAULT_API_BASE_URL = API_BASE_URL;

export interface ApiClientOptions {
  baseUrl?: string;
  /** Injectable for tests. Defaults to the global fetch. */
  fetchImpl?: typeof fetch;
}

export interface RequestOptions {
  signal?: AbortSignal;
}

/**
 * The only place in the frontend that talks HTTP.
 *
 * Search itself stays in Python: this sends the query and reads the ranked
 * response back. It never reorders, rescales, or recomputes anything.
 */
export class ThoughtMapApiClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = stripTrailingSlash(options.baseUrl ?? DEFAULT_API_BASE_URL);
    this.fetchImpl = options.fetchImpl ?? globalThis.fetch.bind(globalThis);
  }

  async health(options: RequestOptions = {}): Promise<HealthResponse> {
    return this.getJson<HealthResponse>("/health", new URLSearchParams(), options);
  }

  /**
   * What this deployment offers.
   *
   * Asked once at startup so the UI reflects the server it is actually talking
   * to rather than what this build assumed (T6 #45).
   */
  async config(options: RequestOptions = {}): Promise<DeploymentFeatures> {
    const payload = await this.getJson<unknown>("/config", new URLSearchParams(), options);
    return parseFeatures(payload);
  }

  /**
   * Readiness, including the corpus and model state.
   *
   * Answers 503 with a body while warming, which is the useful case: the body
   * says *why* it is not ready, so the UI can distinguish "still starting" from
   * "broken" (T6 #37).
   */
  async ready(options: RequestOptions = {}): Promise<ReadinessResponse> {
    const url = this.buildUrl("/ready", new URLSearchParams());
    let response: Response;
    try {
      const init: RequestInit = { method: "GET", headers: { Accept: "application/json" } };
      if (options.signal) {
        init.signal = options.signal;
      }
      response = await this.fetchImpl(url, init);
    } catch (cause) {
      throw new ApiError("network", "Could not reach the ThoughtMap API.", undefined, String(cause));
    }

    const text = await safeText(response);
    try {
      // A 503 body is the point of this endpoint, so it is parsed rather than
      // thrown away.
      return JSON.parse(text) as ReadinessResponse;
    } catch {
      throw new ApiError("parse", "The readiness response could not be read.", response.status);
    }
  }

  async search(request: SearchRequest, options: RequestOptions = {}): Promise<SearchResponse> {
    const response = await this.getJson<SearchResponse>(
      "/search",
      buildSearchParams(request),
      options,
    );

    // A response without a results array would break every consumer downstream,
    // so reject it here rather than letting it reach the UI half-formed.
    if (!response || !Array.isArray(response.results)) {
      throw new ApiError(
        "parse",
        "The API returned a response in an unexpected shape.",
        undefined,
        JSON.stringify(response)?.slice(0, 500),
      );
    }

    return response;
  }

  /**
   * Fetch the cached 3D projection.
   *
   * The server reads a pre-generated artifact; it never runs UMAP for this, so
   * the only slow part is transferring and parsing ~1 MB of JSON.
   */
  async map(options: RequestOptions = {}): Promise<MapResponse> {
    const response = await this.getJson<MapResponse>(
      "/map",
      new URLSearchParams(),
      options,
      "map",
    );

    if (!response || !Array.isArray(response.nodes) || !response.projection) {
      throw new ApiError(
        "parse",
        "The thought space data was in an unexpected shape.",
        undefined,
        JSON.stringify(response)?.slice(0, 500),
      );
    }

    if (response.schema_version !== SUPPORTED_MAP_SCHEMA_VERSION) {
      throw new ApiError(
        "parse",
        `This client cannot read thought space format v${response.schema_version}. ` +
          `It expects v${SUPPORTED_MAP_SCHEMA_VERSION}.`,
        undefined,
        `schema_version=${response.schema_version}`,
      );
    }

    return response;
  }

  /** Absolute URL for a request, exposed for logging and tests. */
  buildUrl(path: string, params: URLSearchParams): string {
    const query = params.toString();
    return query ? `${this.baseUrl}${path}?${query}` : `${this.baseUrl}${path}`;
  }

  private async getJson<T>(
    path: string,
    params: URLSearchParams,
    options: RequestOptions,
    context: ApiContext = "search",
  ): Promise<T> {
    const url = this.buildUrl(path, params);

    let response: Response;
    try {
      const init: RequestInit = { method: "GET", headers: { Accept: "application/json" } };
      if (options.signal) {
        init.signal = options.signal;
      }
      response = await this.fetchImpl(url, init);
    } catch (cause) {
      if (isAbortError(cause, options.signal)) {
        throw new ApiError("aborted", "The request was cancelled.");
      }
      throw new ApiError(
        "network",
        "Could not reach the ThoughtMap API. Check that the backend is running.",
        undefined,
        String(cause),
      );
    }

    if (!response.ok) {
      const body = await safeText(response);
      const detail = extractDetail(body);
      const { kind, message } = messageForStatus(response.status, detail, context);
      throw new ApiError(kind, message, response.status, detail);
    }

    const text = await safeText(response);
    try {
      return JSON.parse(text) as T;
    } catch (cause) {
      throw new ApiError(
        "parse",
        "The API returned a response that could not be read.",
        response.status,
        `${String(cause)} :: ${text.slice(0, 500)}`,
      );
    }
  }
}

/**
 * Build the `/search` query string.
 *
 * Empty `source` and `filter` are omitted rather than sent as "all", matching
 * what the Unity client does and what the backend treats as "no filter".
 */
export function buildSearchParams(request: SearchRequest): URLSearchParams {
  const params = new URLSearchParams();
  params.set("q", request.q);

  if (request.top !== undefined) {
    params.set("top", String(request.top));
  }
  if (request.mode) {
    params.set("mode", request.mode);
  }

  appendIfMeaningful(params, "source", request.source);
  appendIfMeaningful(params, "filter", request.filter);
  appendIfMeaningful(params, "target_doc_id", request.target_doc_id);
  appendIfMeaningful(params, "user_email", request.user_email);

  return params;
}

function appendIfMeaningful(params: URLSearchParams, key: string, value: string | undefined): void {
  const text = (value ?? "").trim();
  if (!text || text.toLowerCase() === "all") {
    return;
  }
  params.set(key, text);
}

function isAbortError(cause: unknown, signal: AbortSignal | undefined): boolean {
  if (signal?.aborted) {
    return true;
  }
  return Boolean(cause && typeof cause === "object" && (cause as { name?: string }).name === "AbortError");
}

async function safeText(response: Response): Promise<string> {
  try {
    return await response.text();
  } catch {
    return "";
  }
}

function stripTrailingSlash(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}
