import { ApiError } from "../api/errors";
import type { ThoughtMapApiClient } from "../api/ThoughtMapApiClient";
import type { SearchRequest } from "../api/types";
import { TOP_MAX, TOP_MIN } from "../config/searchOptions";
import type { AppState } from "./AppState";

/**
 * Turns "the user asked to search" into one API call and one state transition.
 *
 * Owns cancellation. A new search aborts the in-flight request *and* the state
 * layer discards any stale response that still arrives, so the newest search
 * always wins even if an older one resolves later.
 */
export class SearchController {
  private inFlight: AbortController | null = null;

  constructor(
    private readonly state: AppState,
    private readonly client: ThoughtMapApiClient,
  ) {}

  /** Run a search from the current form state. Never rejects. */
  async search(): Promise<void> {
    const snapshot = this.state.getState();
    const query = snapshot.query.trim();

    if (!query) {
      // The API rejects an empty q with 422; no point spending a round trip.
      this.state.searchFailed(this.state.startSearch(), "Enter a search query first.");
      return;
    }

    this.inFlight?.abort();
    const controller = new AbortController();
    this.inFlight = controller;

    const requestId = this.state.startSearch();

    const request: SearchRequest = {
      q: query,
      top: clampTop(snapshot.top),
      mode: snapshot.mode,
      source: snapshot.source,
      filter: snapshot.filter,
    };

    try {
      const response = await this.client.search(request, { signal: controller.signal });

      this.state.searchSucceeded(requestId, {
        query,
        // Order is the API's ranking. Never re-sorted here.
        results: response.results,
        queryParameters: response.query_parameters ?? null,
      });
    } catch (error) {
      if (error instanceof ApiError && error.isAborted) {
        // Superseded by a newer search; that search owns the state now.
        return;
      }

      // Full detail to the console, a readable sentence to the screen.
      console.error("[ThoughtMap] search failed", error);
      const message =
        error instanceof ApiError ? error.message : "The search failed unexpectedly.";
      this.state.searchFailed(requestId, message);
    } finally {
      if (this.inFlight === controller) {
        this.inFlight = null;
      }
    }
  }

  /** Abort any in-flight search, e.g. on teardown. */
  cancel(): void {
    this.inFlight?.abort();
    this.inFlight = null;
  }
}

export function clampTop(value: number): number {
  if (!Number.isFinite(value)) {
    return TOP_MIN;
  }
  return Math.min(TOP_MAX, Math.max(TOP_MIN, Math.round(value)));
}
