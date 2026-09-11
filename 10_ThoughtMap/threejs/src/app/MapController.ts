import { ApiError } from "../api/errors";
import type { ThoughtMapApiClient } from "../api/ThoughtMapApiClient";
import { isMapNode } from "../api/mapTypes";
import type { AppState } from "./AppState";

/**
 * Loads the thought space once and puts it into shared state.
 *
 * Kept apart from SearchController on purpose: the two failure modes are
 * independent. A 503 from `/map` leaves text search fully usable, and a failed
 * search leaves a loaded map on screen.
 */
export class MapController {
  private inFlight: AbortController | null = null;

  constructor(
    private readonly state: AppState,
    private readonly client: ThoughtMapApiClient,
  ) {}

  /** Fetch the projection. Never rejects. */
  async load(): Promise<void> {
    this.inFlight?.abort();
    const controller = new AbortController();
    this.inFlight = controller;

    this.state.mapLoading();

    try {
      const response = await this.client.map({ signal: controller.signal });

      // Drop anything malformed rather than letting a NaN coordinate poison
      // the bounding box and blank the whole cloud.
      const nodes = response.nodes.filter(isMapNode);
      const dropped = response.nodes.length - nodes.length;
      if (dropped > 0) {
        console.warn(`[ThoughtMap] ignored ${dropped} malformed map node(s)`);
      }

      this.state.mapLoaded(nodes, response.projection);
    } catch (error) {
      if (error instanceof ApiError && error.isAborted) {
        return;
      }

      console.error("[ThoughtMap] map load failed", error);
      const message =
        error instanceof ApiError
          ? error.message
          : "The thought space could not be loaded.";
      this.state.mapFailed(message);
    } finally {
      if (this.inFlight === controller) {
        this.inFlight = null;
      }
    }
  }

  cancel(): void {
    this.inFlight?.abort();
    this.inFlight = null;
  }
}
