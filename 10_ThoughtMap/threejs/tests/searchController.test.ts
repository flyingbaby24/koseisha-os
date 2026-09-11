import { describe, expect, it, vi } from "vitest";

import { ThoughtMapApiClient } from "../src/api/ThoughtMapApiClient";
import type { SearchResponse } from "../src/api/types";
import { AppState } from "../src/app/AppState";
import { clampTop, SearchController } from "../src/app/SearchController";

function response(docIds: string[]): SearchResponse {
  return {
    results: docIds.map((doc_id) => ({
      doc_id,
      title: doc_id,
      author: "Author",
      source: "gutendex",
      similarity: 0.5,
    })),
    query_parameters: [{ key: "philosophy", value: 0.14 }],
  };
}

function jsonFetch(handler: (url: string) => Promise<Response>): typeof fetch {
  return vi.fn(async (input: RequestInfo | URL) => handler(String(input))) as unknown as typeof fetch;
}

function ok(body: SearchResponse): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("clampTop", () => {
  it("keeps values inside the range the API accepts", () => {
    expect(clampTop(10)).toBe(10);
    expect(clampTop(0)).toBe(1);
    expect(clampTop(-5)).toBe(1);
    expect(clampTop(999)).toBe(50);
    expect(clampTop(12.6)).toBe(13);
    expect(clampTop(Number.NaN)).toBe(1);
  });
});

describe("SearchController", () => {
  it("refuses to call the API with an empty query", async () => {
    const fetchImpl = jsonFetch(async () => ok(response([])));
    const state = new AppState();
    const controller = new SearchController(state, new ThoughtMapApiClient({ fetchImpl }));

    state.setQuery("   ");
    await controller.search();

    expect(fetchImpl).not.toHaveBeenCalled();
    expect(state.getState().status).toBe("error");
    expect(state.getState().error).toContain("Enter a search query");
  });

  it("sends the current form state and stores the response", async () => {
    const urls: string[] = [];
    const fetchImpl = jsonFetch(async (url) => {
      urls.push(url);
      return ok(response(["a", "b"]));
    });

    const state = new AppState();
    const controller = new SearchController(state, new ThoughtMapApiClient({ fetchImpl }));

    state.setQuery("  Plato  ");
    state.setMode("hybrid");
    state.setSource("gutendex");
    state.setFilter("philosophy");
    state.setTop(5);
    await controller.search();

    expect(urls[0]).toContain("q=Plato");
    expect(urls[0]).toContain("mode=hybrid");
    expect(urls[0]).toContain("source=gutendex");
    expect(urls[0]).toContain("filter=philosophy");
    expect(urls[0]).toContain("top=5");

    const snapshot = state.getState();
    expect(snapshot.status).toBe("success");
    expect(snapshot.results.map((r) => r.doc_id)).toEqual(["a", "b"]);
    expect(snapshot.queryParameters).toHaveLength(1);
  });

  it("surfaces a readable message when the API fails", async () => {
    const fetchImpl = jsonFetch(async () => new Response("boom", { status: 500 }));
    const state = new AppState();
    const controller = new SearchController(state, new ThoughtMapApiClient({ fetchImpl }));

    state.setQuery("Plato");
    await controller.search();

    expect(state.getState().status).toBe("error");
    expect(state.getState().error).toBe("The ThoughtMap API failed to complete the search.");
    expect(state.getState().error).not.toContain("boom");
  });

  it("keeps the newest search when an older one resolves later", async () => {
    // A is slow, B is fast. B starts second and must win.
    const resolvers: Array<() => void> = [];
    const fetchImpl = jsonFetch(async (url) => {
      const isFirst = url.includes("q=first");
      if (isFirst) {
        await new Promise<void>((resolve) => resolvers.push(resolve));
        return ok(response(["from-a"]));
      }
      return ok(response(["from-b"]));
    });

    const state = new AppState();
    const controller = new SearchController(state, new ThoughtMapApiClient({ fetchImpl }));

    state.setQuery("first");
    const slow = controller.search();

    state.setQuery("second");
    await controller.search();

    expect(state.getState().results.map((r) => r.doc_id)).toEqual(["from-b"]);

    // Now let A finish; it must not overwrite B.
    resolvers.forEach((resolve) => resolve());
    await slow;

    expect(state.getState().status).toBe("success");
    expect(state.getState().results.map((r) => r.doc_id)).toEqual(["from-b"]);
    expect(state.getState().lastQuery).toBe("second");
  });

  it("aborts a still-pending request when a new search starts", async () => {
    const signals: AbortSignal[] = [];
    const release: Array<() => void> = [];

    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.signal) {
        signals.push(init.signal);
      }
      // Hold the first request open so it is genuinely in flight when the
      // second starts; the second resolves immediately.
      if (String(input).includes("q=first")) {
        await new Promise<void>((resolve) => release.push(resolve));
      }
      return ok(response(["x"]));
    }) as unknown as typeof fetch;

    const state = new AppState();
    const controller = new SearchController(state, new ThoughtMapApiClient({ fetchImpl }));

    state.setQuery("first");
    const pending = controller.search();
    // Let the first call reach fetch before starting the second.
    await Promise.resolve();

    state.setQuery("second");
    await controller.search();

    expect(signals).toHaveLength(2);
    expect(signals[0]?.aborted).toBe(true);
    expect(signals[1]?.aborted).toBe(false);

    release.forEach((resolve) => resolve());
    await pending;
  });

  it("does not abort a request that already completed", async () => {
    const signals: AbortSignal[] = [];
    const fetchImpl = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.signal) {
        signals.push(init.signal);
      }
      return ok(response(["x"]));
    }) as unknown as typeof fetch;

    const state = new AppState();
    const controller = new SearchController(state, new ThoughtMapApiClient({ fetchImpl }));

    state.setQuery("first");
    await controller.search();
    state.setQuery("second");
    await controller.search();

    expect(signals[0]?.aborted).toBe(false);
    expect(signals[1]?.aborted).toBe(false);
  });

  it("does not report an aborted request as an error", async () => {
    const fetchImpl = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      return await new Promise<Response>((resolve, reject) => {
        init?.signal?.addEventListener("abort", () =>
          reject(new DOMException("aborted", "AbortError")),
        );
        setTimeout(() => resolve(ok(response(["late"]))), 50);
      });
    }) as unknown as typeof fetch;

    const state = new AppState();
    const controller = new SearchController(state, new ThoughtMapApiClient({ fetchImpl }));

    state.setQuery("first");
    const first = controller.search();
    state.setQuery("second");
    const second = controller.search();

    await Promise.all([first, second]);

    expect(state.getState().status).toBe("success");
    expect(state.getState().error).toBeNull();
  });

  it("keeps the selection when the new results exclude the selected document", async () => {
    // T4 semantics: selection belongs to the thought space, not to the current
    // result list, so re-searching re-ranks the list without discarding what
    // the user is looking at.
    let payload = response(["a", "b"]);
    const fetchImpl = jsonFetch(async () => ok(payload));

    const state = new AppState();
    const controller = new SearchController(state, new ThoughtMapApiClient({ fetchImpl }));

    state.setQuery("Plato");
    await controller.search();
    state.select("a");
    expect(state.getState().selectedDocId).toBe("a");

    payload = response(["x", "y"]);
    state.setQuery("Kant");
    await controller.search();

    expect(state.getState().selectedDocId).toBe("a");
    expect(state.getState().results.map((r) => r.doc_id)).toEqual(["x", "y"]);
  });

  it("replaces map emphasis on each successful search", async () => {
    let payload = response(["a", "b"]);
    const fetchImpl = jsonFetch(async () => ok(payload));

    const state = new AppState();
    const controller = new SearchController(state, new ThoughtMapApiClient({ fetchImpl }));

    state.setQuery("Plato");
    await controller.search();
    expect(state.getState().emphasisDocIds).toEqual(["a", "b"]);
    expect(state.getState().hasSearchEmphasis).toBe(true);

    payload = response(["x"]);
    state.setQuery("Kant");
    await controller.search();
    expect(state.getState().emphasisDocIds).toEqual(["x"]);
  });

  it("keeps the last successful map emphasis when a search fails", async () => {
    let payload = response(["a", "b"]);
    let fail = false;
    const fetchImpl = jsonFetch(async () =>
      fail ? new Response("boom", { status: 500 }) : ok(payload),
    );

    const state = new AppState();
    const controller = new SearchController(state, new ThoughtMapApiClient({ fetchImpl }));

    state.setQuery("Plato");
    await controller.search();

    fail = true;
    state.setQuery("Kant");
    await controller.search();

    // The stale rows go, but the thought space keeps its context.
    expect(state.getState().status).toBe("error");
    expect(state.getState().results).toEqual([]);
    expect(state.getState().emphasisDocIds).toEqual(["a", "b"]);
    expect(state.getState().hasSearchEmphasis).toBe(true);
  });
});
