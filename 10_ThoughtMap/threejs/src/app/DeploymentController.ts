import type { ThoughtMapApiClient } from "../api/ThoughtMapApiClient";
import type { ReadinessResponse } from "../api/types";
import { DEFAULT_FEATURES } from "../config/runtime";
import type { AppState } from "./AppState";

/** How long to wait between readiness polls while the backend warms. */
export const READY_POLL_INTERVAL_MS = 2_000;
/**
 * Stop polling after this long.
 *
 * A backend that has not warmed in two minutes is not warming, it is broken,
 * and an indefinite "starting up" message would be a lie told forever.
 */
export const READY_POLL_TIMEOUT_MS = 120_000;

export interface DeploymentControllerOptions {
  /** Injectable for tests; defaults to the real timers. */
  setTimeoutImpl?: (handler: () => void, timeout: number) => number;
  clearTimeoutImpl?: (handle: number) => void;
  now?: () => number;
}

/**
 * Learns what the backend is and whether it is ready.
 *
 * Kept apart from search and map deliberately: whether the Personal Library
 * exists is a property of the deployment, not of any request, and asking once
 * at startup is cheaper and clearer than inferring it from a 404 later.
 *
 * Nothing here blocks anything. If `/config` and `/ready` both fail the app
 * still runs — search, map and selection are unaffected, and the UI simply
 * shows the conservative defaults.
 */
export class DeploymentController {
  private readonly state: AppState;
  private readonly client: ThoughtMapApiClient;
  private readonly setTimeoutImpl: (handler: () => void, timeout: number) => number;
  private readonly clearTimeoutImpl: (handle: number) => void;
  private readonly now: () => number;

  private pollHandle: number | null = null;
  private startedAt = 0;
  private stopped = false;

  constructor(
    state: AppState,
    client: ThoughtMapApiClient,
    options: DeploymentControllerOptions = {},
  ) {
    this.state = state;
    this.client = client;
    this.setTimeoutImpl =
      options.setTimeoutImpl ??
      ((handler, timeout) => globalThis.setTimeout(handler, timeout) as unknown as number);
    this.clearTimeoutImpl =
      options.clearTimeoutImpl ?? ((handle) => globalThis.clearTimeout(handle));
    this.now = options.now ?? (() => Date.now());
  }

  /**
   * Read the deployment's feature list.
   *
   * On failure the conservative defaults stand: the Personal Library stays
   * hidden rather than being offered by an app that could not confirm it
   * exists.
   */
  async loadFeatures(): Promise<void> {
    try {
      this.state.setFeatures(await this.client.config());
    } catch {
      this.state.setFeatures(DEFAULT_FEATURES);
    }
  }

  /**
   * Watch readiness until the backend is ready, broken, or the timeout passes.
   *
   * The distinction this exists to draw: a 503 whose body says a check is
   * *pending* means "warming, wait"; anything else means "unavailable". Only
   * the server can tell those apart, so only the server is asked (T6 #37).
   */
  async start(): Promise<void> {
    this.startedAt = this.now();
    await this.poll();
  }

  private async poll(): Promise<void> {
    if (this.stopped) {
      return;
    }

    let snapshot: ReadinessResponse;
    try {
      snapshot = await this.client.ready();
    } catch {
      // Unreachable is the one failure that routinely fixes itself: it is what
      // a deploy or a restart looks like from here. Report it, but keep
      // watching, so the page recovers when the API returns instead of telling
      // someone it is down until they reload.
      this.state.setBackendStatus("unavailable", "Could not reach the ThoughtMap API.");
      this.scheduleRetry();
      return;
    }

    if (snapshot.ready) {
      this.state.setBackendStatus("ready");
      return;
    }

    const detail = describeBlockers(snapshot);

    if (isWarming(snapshot)) {
      this.state.setBackendStatus("warming", detail);
      if (this.scheduleRetry()) {
        return;
      }
      this.state.setBackendStatus(
        "unavailable",
        "The ThoughtMap API did not finish starting up.",
      );
      return;
    }

    // A reported failure will not resolve by waiting — an operator has to act —
    // so this is where polling genuinely stops.
    this.state.setBackendStatus("unavailable", detail);
  }

  /** Queue the next poll if there is still time. Returns whether it did. */
  private scheduleRetry(): boolean {
    if (this.stopped || this.now() - this.startedAt >= READY_POLL_TIMEOUT_MS) {
      return false;
    }
    this.pollHandle = this.setTimeoutImpl(() => {
      this.pollHandle = null;
      void this.poll();
    }, READY_POLL_INTERVAL_MS);
    return true;
  }

  dispose(): void {
    this.stopped = true;
    if (this.pollHandle !== null) {
      this.clearTimeoutImpl(this.pollHandle);
      this.pollHandle = null;
    }
  }
}

/**
 * Still starting, as opposed to failed.
 *
 * "pending" is the only status that means work is still in progress. A failed
 * check will not become ready by waiting, so polling through it would show a
 * reassuring message about a service that is not coming back.
 */
export function isWarming(snapshot: ReadinessResponse): boolean {
  const checks = snapshot.checks ?? [];
  if (checks.length === 0) {
    // No detail to go on. Treat as warming: the process answered, which a
    // genuinely dead one would not have.
    return true;
  }
  const pending = checks.some((check) => check.status === "pending");
  const failed = checks.some((check) => check.status === "failed");
  return pending && !failed;
}

/** A short, non-technical reason, or null. Never a stack trace (T6 #36). */
export function describeBlockers(snapshot: ReadinessResponse): string | null {
  const blocked = snapshot.blocked_by ?? [];
  if (blocked.length === 0) {
    return null;
  }

  const readable: Record<string, string> = {
    configuration: "server configuration",
    corpus_manifest: "corpus manifest",
    embedding_artifact: "the embedding data",
    search_engine: "the search index",
    embedding_model: "the semantic model",
    map_projection: "the thought space",
  };

  const names = blocked.map((name) => readable[name] ?? name);
  return names.length === 1 ? `Waiting for ${names[0]}.` : `Waiting for ${names.join(", ")}.`;
}
