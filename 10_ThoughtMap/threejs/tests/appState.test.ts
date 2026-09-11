import { describe, expect, it, vi } from "vitest";

import { AppState } from "../src/app/AppState";
import type { SearchResult } from "../src/api/types";

function result(docId: string, similarity = 0.5): SearchResult {
  return {
    doc_id: docId,
    title: `Title ${docId}`,
    author: "Author",
    source: "gutendex",
    similarity,
  };
}

describe("AppState initial state", () => {
  it("starts idle with the documented defaults", () => {
    const state = new AppState().getState();

    expect(state.status).toBe("idle");
    expect(state.query).toBe("");
    expect(state.mode).toBe("semantic");
    expect(state.source).toBe("");
    expect(state.filter).toBe("");
    expect(state.top).toBe(10);
    expect(state.results).toEqual([]);
    expect(state.queryParameters).toBeNull();
    expect(state.selectedDocId).toBeNull();
    expect(state.error).toBeNull();
  });

  it("notifies a new subscriber immediately with the current state", () => {
    const state = new AppState();
    const listener = vi.fn();
    state.subscribe(listener);
    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener.mock.calls[0]?.[0].status).toBe("idle");
  });

  it("stops notifying after unsubscribe", () => {
    const state = new AppState();
    const listener = vi.fn();
    const unsubscribe = state.subscribe(listener);
    unsubscribe();
    state.setQuery("Plato");
    expect(listener).toHaveBeenCalledTimes(1);
  });
});

describe("AppState search lifecycle", () => {
  it("enters the searching state and clears a previous error", () => {
    const state = new AppState();
    state.searchFailed(state.startSearch(), "boom");
    expect(state.getState().status).toBe("error");

    state.startSearch();
    expect(state.getState().status).toBe("searching");
    expect(state.getState().error).toBeNull();
  });

  it("applies a successful search", () => {
    const state = new AppState();
    const id = state.startSearch();

    state.searchSucceeded(id, {
      query: "Plato",
      results: [result("a"), result("b")],
      queryParameters: [{ key: "philosophy", value: 0.14 }],
    });

    const snapshot = state.getState();
    expect(snapshot.status).toBe("success");
    expect(snapshot.results).toHaveLength(2);
    expect(snapshot.queryParameters?.[0]?.key).toBe("philosophy");
    expect(snapshot.lastQuery).toBe("Plato");
    expect(snapshot.error).toBeNull();
  });

  it("preserves the API result order exactly", () => {
    const state = new AppState();
    const id = state.startSearch();
    // Deliberately not sorted by similarity: the backend's order wins.
    state.searchSucceeded(id, {
      query: "Plato",
      results: [result("a", 0.2), result("b", 0.9), result("c", 0.5)],
      queryParameters: null,
    });

    expect(state.getState().results.map((r) => r.doc_id)).toEqual(["a", "b", "c"]);
  });

  it("records a failed search and drops stale results", () => {
    const state = new AppState();
    const first = state.startSearch();
    state.searchSucceeded(first, { query: "Plato", results: [result("a")], queryParameters: null });

    const second = state.startSearch();
    state.searchFailed(second, "The ThoughtMap API failed to complete the search.");

    const snapshot = state.getState();
    expect(snapshot.status).toBe("error");
    expect(snapshot.error).toContain("failed to complete");
    expect(snapshot.results).toEqual([]);
    expect(snapshot.queryParameters).toBeNull();
    expect(snapshot.selectedDocId).toBeNull();
  });

  it("replaces the previous results on a new search", () => {
    const state = new AppState();
    const first = state.startSearch();
    state.searchSucceeded(first, { query: "Plato", results: [result("a")], queryParameters: null });

    const second = state.startSearch();
    state.searchSucceeded(second, { query: "Kant", results: [result("z")], queryParameters: null });

    expect(state.getState().results.map((r) => r.doc_id)).toEqual(["z"]);
    expect(state.getState().lastQuery).toBe("Kant");
  });

  it("reports a successful search with no matches as empty, not an error", () => {
    const state = new AppState();
    const id = state.startSearch();
    state.searchSucceeded(id, { query: "zzz", results: [], queryParameters: null });

    expect(state.getState().status).toBe("success");
    expect(state.getState().error).toBeNull();
    expect(state.hasEmptyResults()).toBe(true);
  });
});

describe("AppState race protection", () => {
  it("ignores a stale response that lands after a newer search started", () => {
    const state = new AppState();

    const requestA = state.startSearch();
    const requestB = state.startSearch();

    // B completes first.
    expect(
      state.searchSucceeded(requestB, {
        query: "B",
        results: [result("from-b")],
        queryParameters: null,
      }),
    ).toBe(true);

    // A completes later and must not overwrite B.
    expect(
      state.searchSucceeded(requestA, {
        query: "A",
        results: [result("from-a")],
        queryParameters: null,
      }),
    ).toBe(false);

    const snapshot = state.getState();
    expect(snapshot.lastQuery).toBe("B");
    expect(snapshot.results.map((r) => r.doc_id)).toEqual(["from-b"]);
  });

  it("ignores a stale failure that lands after a newer search started", () => {
    const state = new AppState();
    const requestA = state.startSearch();
    const requestB = state.startSearch();

    state.searchSucceeded(requestB, { query: "B", results: [result("b")], queryParameters: null });
    expect(state.searchFailed(requestA, "old failure")).toBe(false);

    expect(state.getState().status).toBe("success");
    expect(state.getState().error).toBeNull();
  });

  it("tracks the newest request id", () => {
    const state = new AppState();
    const first = state.startSearch();
    const second = state.startSearch();

    expect(state.isCurrent(first)).toBe(false);
    expect(state.isCurrent(second)).toBe(true);
    expect(state.currentRequestId).toBe(second);
  });
});

describe("AppState selection", () => {
  function withResults(): AppState {
    const state = new AppState();
    const id = state.startSearch();
    state.searchSucceeded(id, {
      query: "Plato",
      results: [result("a"), result("b")],
      queryParameters: null,
    });
    return state;
  }

  it("selects a result present in the current set", () => {
    const state = withResults();
    state.select("b");
    expect(state.getState().selectedDocId).toBe("b");
    expect(state.getSelectedResult()?.doc_id).toBe("b");
  });

  it("ignores a selection that is not in the current results", () => {
    const state = withResults();
    state.select("missing");
    expect(state.getState().selectedDocId).toBeNull();
  });

  it("clears the selection on null", () => {
    const state = withResults();
    state.select("a");
    state.select(null);
    expect(state.getState().selectedDocId).toBeNull();
    expect(state.getSelectedResult()).toBeNull();
  });

  it("keeps the selection when the next search still contains that document", () => {
    const state = withResults();
    state.select("a");

    const id = state.startSearch();
    state.searchSucceeded(id, {
      query: "Plato again",
      results: [result("a"), result("c")],
      queryParameters: null,
    });

    expect(state.getState().selectedDocId).toBe("a");
  });

  it("keeps the selection when the next search excludes that document", () => {
    // Semantics changed in T4. Before the thought space existed, "selected"
    // could only mean a row in the current result list, so a search that
    // dropped that row had to clear it. Now a document can be selected by
    // clicking its node with no search involved, so selection belongs to the
    // map, not to the result set. The DetailPanel falls back to map metadata.
    const state = withResults();
    state.select("a");

    const id = state.startSearch();
    state.searchSucceeded(id, {
      query: "Kant",
      results: [result("x"), result("y")],
      queryParameters: null,
    });

    expect(state.getState().selectedDocId).toBe("a");
    // It is no longer a *search result*, which is what this accessor reports.
    expect(state.getSelectedResult()).toBeNull();
  });

  it("keeps the selection when a search fails", () => {
    const state = withResults();
    state.select("a");

    state.searchFailed(state.startSearch(), "The ThoughtMap API failed to complete the search.");

    expect(state.getState().selectedDocId).toBe("a");
  });

  it("allows selecting a map node that no search returned", () => {
    const state = new AppState();
    state.mapLoaded(
      [{ doc_id: "map-only", title: "T", author: "", source: "zip", x: 0, y: 0, z: 0, cluster: 0 }],
      {
        generated_at: "",
        dataset_fingerprint: "",
        document_count: 1,
        embedding_dimension: 384,
        dimensions: 3,
        algorithm: "umap",
        metric: "cosine",
        n_neighbors: 10,
        min_dist: 0.2,
        random_seed: 42,
      },
    );

    state.select("map-only");
    expect(state.getState().selectedDocId).toBe("map-only");
  });
});
