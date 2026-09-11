// @vitest-environment happy-dom
import { describe, expect, it, vi } from "vitest";

import { ThoughtMapApiClient } from "../src/api/ThoughtMapApiClient";
import type { ReadinessResponse, SearchResult } from "../src/api/types";
import { AppState } from "../src/app/AppState";
import {
  DeploymentController,
  describeBlockers,
  isWarming,
} from "../src/app/DeploymentController";
import { fromSearchResult } from "../src/app/DocumentSelectionResolver";
import { SearchScreen } from "../src/app/SearchScreen";
import { DEFAULT_FEATURES, parseFeatures } from "../src/config/runtime";
import { messageFor } from "../src/ui/BackendStatusBanner";
import { DetailPanel } from "../src/ui/DetailPanel";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function result(doc_id: string): SearchResult {
  return { doc_id, title: "The Republic", author: "Plato", source: "gutendex", similarity: 0.7 };
}

function stateWithResult(): AppState {
  const state = new AppState();
  const id = state.startSearch();
  state.searchSucceeded(id, {
    query: "Plato",
    results: [result("gutendex:doc_1")],
    queryParameters: null,
  });
  state.select("gutendex:doc_1");
  return state;
}

describe("parseFeatures", () => {
  it("reads a well-formed payload", () => {
    const features = parseFeatures({
      deployment_mode: "public-demo",
      library_enabled: false,
      diagnostics_enabled: false,
      semantic_search_enabled: true,
      corpus_version: "20260909",
    });
    expect(features.deployment_mode).toBe("public-demo");
    expect(features.library_enabled).toBe(false);
    expect(features.corpus_version).toBe("20260909");
  });

  it("falls back to the safe defaults for junk", () => {
    expect(parseFeatures(null)).toEqual(DEFAULT_FEATURES);
    expect(parseFeatures("nonsense")).toEqual(DEFAULT_FEATURES);
    expect(parseFeatures({ deployment_mode: "banana" }).deployment_mode).toBe("production");
  });

  it("never enables the library on an ambiguous payload", () => {
    // The safe direction is off: offering a Save button that 404s is worse
    // than not offering one.
    expect(parseFeatures({}).library_enabled).toBe(false);
    expect(parseFeatures({ library_enabled: "yes" }).library_enabled).toBe(false);
    expect(parseFeatures({ library_enabled: 1 }).library_enabled).toBe(false);
  });

  it("treats an absent semantic flag as available, for an older API", () => {
    expect(parseFeatures({}).semantic_search_enabled).toBe(true);
    expect(parseFeatures({ semantic_search_enabled: false }).semantic_search_enabled).toBe(false);
  });
});

describe("readiness interpretation", () => {
  it("calls a pending check warming", () => {
    const snapshot: ReadinessResponse = {
      ready: false,
      checks: [
        { name: "configuration", status: "ok" },
        { name: "search_engine", status: "pending" },
      ],
    };
    expect(isWarming(snapshot)).toBe(true);
  });

  it("does not call a failed check warming, even alongside a pending one", () => {
    // Waiting will not fix a failure, so the UI must not promise it will.
    const snapshot: ReadinessResponse = {
      ready: false,
      checks: [
        { name: "embedding_artifact", status: "failed" },
        { name: "search_engine", status: "pending" },
      ],
    };
    expect(isWarming(snapshot)).toBe(false);
  });

  it("treats a bodyless answer as warming, since the process replied", () => {
    expect(isWarming({ ready: false })).toBe(true);
  });

  it("names blockers in plain language and never leaks internals", () => {
    expect(describeBlockers({ ready: false, blocked_by: ["embedding_model"] })).toBe(
      "Waiting for the semantic model.",
    );
    expect(
      describeBlockers({ ready: false, blocked_by: ["search_engine", "map_projection"] }),
    ).toBe("Waiting for the search index, the thought space.");
    expect(describeBlockers({ ready: false })).toBeNull();
  });
});

describe("DeploymentController", () => {
  function controller(state: AppState, fetchImpl: typeof fetch) {
    const client = new ThoughtMapApiClient({ fetchImpl });
    const timers: Array<() => void> = [];
    const deployment = new DeploymentController(state, client, {
      setTimeoutImpl: (handler) => {
        timers.push(handler);
        return timers.length;
      },
      clearTimeoutImpl: () => undefined,
      now: () => 0,
    });
    return { deployment, timers };
  }

  it("adopts the server's feature list", async () => {
    const state = new AppState();
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse({ deployment_mode: "public-demo", library_enabled: false }),
    ) as unknown as typeof fetch;

    const { deployment } = controller(state, fetchImpl);
    await deployment.loadFeatures();

    expect(state.getState().features.deployment_mode).toBe("public-demo");
    expect(state.getState().features.library_enabled).toBe(false);
  });

  it("keeps the library hidden when /config cannot be reached", async () => {
    const state = new AppState();
    const fetchImpl = vi.fn().mockRejectedValue(new Error("offline")) as unknown as typeof fetch;

    const { deployment } = controller(state, fetchImpl);
    await deployment.loadFeatures();

    expect(state.getState().features.library_enabled).toBe(false);
  });

  it("marks the backend ready", async () => {
    const state = new AppState();
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse({ ready: true, checks: [{ name: "search_engine", status: "ok" }] }),
    ) as unknown as typeof fetch;

    const { deployment } = controller(state, fetchImpl);
    await deployment.start();

    expect(state.getState().backendStatus).toBe("ready");
  });

  it("reports warming and schedules another poll while a check is pending", async () => {
    const state = new AppState();
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse(
        {
          ready: false,
          blocked_by: ["embedding_model"],
          checks: [{ name: "embedding_model", status: "pending" }],
        },
        503,
      ),
    ) as unknown as typeof fetch;

    const { deployment, timers } = controller(state, fetchImpl);
    await deployment.start();

    expect(state.getState().backendStatus).toBe("warming");
    expect(state.getState().backendDetail).toBe("Waiting for the semantic model.");
    expect(timers).toHaveLength(1);
  });

  it("reports unavailable, and stops polling, on a failed check", async () => {
    const state = new AppState();
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse(
        {
          ready: false,
          blocked_by: ["embedding_artifact"],
          checks: [{ name: "embedding_artifact", status: "failed" }],
        },
        503,
      ),
    ) as unknown as typeof fetch;

    const { deployment, timers } = controller(state, fetchImpl);
    await deployment.start();

    expect(state.getState().backendStatus).toBe("unavailable");
    expect(timers).toHaveLength(0);
  });

  it("reports unavailable when the API cannot be reached at all", async () => {
    const state = new AppState();
    const fetchImpl = vi.fn().mockRejectedValue(new Error("offline")) as unknown as typeof fetch;

    const { deployment } = controller(state, fetchImpl);
    await deployment.start();

    expect(state.getState().backendStatus).toBe("unavailable");
  });

  it("keeps watching an unreachable API, because a restart looks like this", async () => {
    // The alternative is telling someone the service is down until they
    // reload, for the one failure that routinely fixes itself.
    const state = new AppState();
    const fetchImpl = vi.fn().mockRejectedValue(new Error("offline")) as unknown as typeof fetch;

    const { deployment, timers } = controller(state, fetchImpl);
    await deployment.start();

    expect(timers).toHaveLength(1);
  });

  it("recovers when the API comes back", async () => {
    const state = new AppState();
    const fetchImpl = vi
      .fn()
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(jsonResponse({ ready: true, checks: [] })) as unknown as typeof fetch;

    const { deployment, timers } = controller(state, fetchImpl);
    await deployment.start();
    expect(state.getState().backendStatus).toBe("unavailable");

    // Fire the retry the controller queued.
    timers[0]!();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(state.getState().backendStatus).toBe("ready");
  });

  it("stops polling once a check has actually failed", async () => {
    const state = new AppState();
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse(
        { ready: false, checks: [{ name: "embedding_artifact", status: "failed" }] },
        503,
      ),
    ) as unknown as typeof fetch;

    const { deployment, timers } = controller(state, fetchImpl);
    await deployment.start();

    expect(state.getState().backendStatus).toBe("unavailable");
    expect(timers).toHaveLength(0);
  });
});

describe("BackendStatusBanner messages", () => {
  it("says nothing when everything is normal", () => {
    const state = new AppState();
    state.setFeatures({ ...DEFAULT_FEATURES, deployment_mode: "development", library_enabled: true });
    state.setBackendStatus("ready");
    expect(messageFor(state.getState())).toBeNull();
  });

  it("distinguishes warming from unavailable", () => {
    const state = new AppState();
    state.setBackendStatus("warming", "Waiting for the semantic model.");
    expect(messageFor(state.getState())?.tone).toBe("info");
    expect(messageFor(state.getState())?.text).toContain("starting up");

    state.setBackendStatus("unavailable", "Waiting for the embedding data.");
    expect(messageFor(state.getState())?.tone).toBe("warning");
    expect(messageFor(state.getState())?.text).not.toContain("starting up");
  });

  it("never invents a progress percentage", () => {
    const state = new AppState();
    state.setBackendStatus("warming", "Waiting for the search index.");
    expect(messageFor(state.getState())?.text).not.toMatch(/\d+\s*%/);
  });

  it("explains a public demo without the library", () => {
    const state = new AppState();
    state.setFeatures({ ...DEFAULT_FEATURES, deployment_mode: "public-demo", library_enabled: false });
    state.setBackendStatus("ready");
    const message = messageFor(state.getState());
    expect(message?.text).toContain("Public demo");
    expect(message?.text.toLowerCase()).not.toContain("sign in");
  });
});

describe("Personal Library feature gate", () => {
  it("removes the Save control entirely when the deployment has no library", () => {
    const panel = new DetailPanel();
    const state = stateWithResult();
    state.setFeatures({ ...DEFAULT_FEATURES, library_enabled: false });

    const snapshot = state.getState();
    panel.render(snapshot, fromSearchResult(snapshot.results[0]!));

    const button = panel.element.querySelector<HTMLButtonElement>(".tm-save-button");
    expect(button).not.toBeNull();
    expect(button!.hidden).toBe(true);
  });

  it("shows the Save control when the deployment has one", () => {
    const panel = new DetailPanel();
    const state = stateWithResult();
    state.setFeatures({ ...DEFAULT_FEATURES, library_enabled: true });

    const snapshot = state.getState();
    panel.render(snapshot, fromSearchResult(snapshot.results[0]!));

    const button = panel.element.querySelector<HTMLButtonElement>(".tm-save-button");
    expect(button!.hidden).toBe(false);
    expect(button!.textContent).toBe("Save");
  });

  it("hides the Library tab and drops saved state when the feature goes away", () => {
    const mount = document.createElement("div");
    const screen = new SearchScreen(mount);

    screen.state.setFeatures({ ...DEFAULT_FEATURES, library_enabled: true });
    screen.state.setLibraryIdentity("someone@example.com");
    screen.state.documentSaved({
      doc_id: "gutendex:doc_1",
      title: "The Republic",
      author: "Plato",
      source: "gutendex",
      saved_at: "2026-09-10T00:00:00Z",
    });
    expect(screen.state.getState().savedWorks).toHaveLength(1);

    const tabs = Array.from(mount.querySelectorAll<HTMLButtonElement>(".tm-tab"));
    const libraryTab = tabs.find((tab) => tab.textContent?.startsWith("Library"));
    expect(libraryTab?.hidden).toBe(false);

    screen.state.setFeatures({ ...DEFAULT_FEATURES, library_enabled: false });

    expect(libraryTab?.hidden).toBe(true);
    // Saved rows must not linger for a feature the server says is not there.
    expect(screen.state.getState().savedWorks).toHaveLength(0);
    expect(screen.state.getState().libraryIdentity).toBe("");

    screen.dispose();
  });

  it("does not touch the Personal Library when the deployment has none", () => {
    const mount = document.createElement("div");
    const libraryFetch = vi.fn();
    const screen = new SearchScreen(mount);

    screen.state.setFeatures({ ...DEFAULT_FEATURES, library_enabled: false });
    screen.enableLibraryIfAvailable();

    expect(libraryFetch).not.toHaveBeenCalled();
    expect(screen.state.getState().libraryStatus).toBe("idle");

    screen.dispose();
  });
});
