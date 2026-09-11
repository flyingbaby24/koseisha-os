// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PersonalLibraryClient } from "../src/api/PersonalLibraryClient";
import type { SavedDocument } from "../src/api/libraryTypes";
import type { MapNode, MapProjectionMetadata } from "../src/api/mapTypes";
import type { SearchResult } from "../src/api/types";
import { AppState } from "../src/app/AppState";
import { LibraryController } from "../src/app/LibraryController";
import { SelectionController } from "../src/app/SelectionController";
import { fromMapNode, fromSearchResult } from "../src/app/DocumentSelectionResolver";
import { NodeState, computeNodeVisualState } from "../src/scene/nodeVisualState";
import { buildNodeIndex } from "../src/scene/nodeIndex";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function saved(docId: string): SavedDocument {
  return {
    doc_id: docId,
    title: `Title ${docId}`,
    author: "Author",
    source: "gutendex",
    saved_at: "2026-09-10T09:00:00+00:00",
  };
}

function result(docId: string): SearchResult {
  return {
    doc_id: docId,
    title: `Title ${docId}`,
    author: "Author",
    source: "gutendex",
    similarity: 0.7,
    url: "https://example.org/x",
    parameters: [{ key: "philosophy", value: 0.13 }],
  };
}

function node(docId: string): MapNode {
  return { doc_id: docId, title: `Map ${docId}`, author: "A", source: "zip", x: 1, y: 2, z: 3, cluster: 0 };
}

const METADATA: MapProjectionMetadata = {
  generated_at: "", dataset_fingerprint: "fp", document_count: 2, embedding_dimension: 384,
  dimensions: 3, algorithm: "umap", metric: "cosine", n_neighbors: 10, min_dist: 0.2, random_seed: 42,
};

function clientWith(handler: (url: string, init?: RequestInit) => Response): PersonalLibraryClient {
  const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) =>
    handler(String(input), init),
  ) as unknown as typeof fetch;
  return new PersonalLibraryClient({ fetchImpl });
}

describe("PersonalLibraryClient", () => {
  it("requests the saved list with the identity as a query parameter", async () => {
    const urls: string[] = [];
    const client = clientWith((url) => {
      urls.push(url);
      return json({ works: [saved("a")] });
    });

    const works = await client.loadSaved("reader@example.com");

    expect(urls[0]).toContain("/users/by-email/saved?email=reader%40example.com");
    expect(works).toHaveLength(1);
  });

  it("accepts the legacy items key as well as works", async () => {
    const client = clientWith(() => json({ items: [saved("a")] }));
    await expect(client.loadSaved("x@y.z")).resolves.toHaveLength(1);
  });

  it("drops malformed entries rather than showing a broken row", async () => {
    const client = clientWith(() => json({ works: [saved("a"), { title: "no id" }] }));
    await expect(client.loadSaved("x@y.z")).resolves.toHaveLength(1);
  });

  it("posts the canonical doc_id unchanged", async () => {
    let body: Record<string, unknown> = {};
    const client = clientWith((_url, init) => {
      body = JSON.parse(String(init?.body));
      return json({ saved: true, item: saved("gutendex:doc_000446") });
    });

    await client.saveDocument({
      email: "x@y.z",
      doc_id: "gutendex:doc_000446",
      title: "The Republic of Plato",
      author: "Plato",
      source: "gutendex",
      parameters: [{ key: "philosophy", value: 0.13 }],
    });

    expect(body["doc_id"]).toBe("gutendex:doc_000446");
    expect(body["email"]).toBe("x@y.z");
    expect(body["title"]).toBe("The Republic of Plato");
    expect(body["parameters"]).toHaveLength(1);
  });

  it("percent-encodes the doc_id in the delete path", async () => {
    const urls: string[] = [];
    const client = clientWith((url) => {
      urls.push(url);
      return json({ deleted: true, doc_id: "gutendex:doc_000446" });
    });

    await client.deleteSaved("x@y.z", "gutendex:doc_000446");

    // The colon must be encoded or the route will not match.
    expect(urls[0]).toContain("/users/by-email/saved/gutendex%3Adoc_000446");
    expect(urls[0]).toContain("email=x%40y.z");
  });

  it("refuses an empty identity before making a request", async () => {
    const fetchImpl = vi.fn() as unknown as typeof fetch;
    const client = new PersonalLibraryClient({ fetchImpl });

    await expect(client.loadSaved("   ")).rejects.toMatchObject({ kind: "validation" });
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it("reports a library 503 in library terms, not search terms", async () => {
    const client = clientWith(() => json({ detail: "down" }, 503));
    await expect(client.loadSaved("x@y.z")).rejects.toMatchObject({
      message: expect.stringContaining("Personal Library"),
    });
  });

  it("translates a transport failure", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }) as unknown as typeof fetch;

    await expect(new PersonalLibraryClient({ fetchImpl }).loadSaved("x@y.z")).rejects.toMatchObject({
      kind: "network",
    });
  });

  it("rejects a malformed save response", async () => {
    const client = clientWith(() => json({ nonsense: true }));
    await expect(
      client.saveDocument({ email: "x@y.z", doc_id: "a", title: "", author: "", source: "" }),
    ).rejects.toMatchObject({ kind: "parse" });
  });
});

describe("library state", () => {
  let state: AppState;
  beforeEach(() => {
    state = new AppState();
    try {
      window.localStorage.clear();
    } catch {
      /* storage may be unavailable */
    }
  });

  it("starts empty", () => {
    const snapshot = state.getState();
    expect(snapshot.libraryStatus).toBe("idle");
    expect(snapshot.libraryIdentity).toBe("");
    expect(snapshot.savedWorks).toEqual([]);
    expect(snapshot.savedDocIds.size).toBe(0);
    expect(snapshot.libraryError).toBeNull();
  });

  it("clears loaded works when the identity changes", () => {
    state.setLibraryIdentity("a@b.c");
    state.libraryLoaded([saved("a")]);
    expect(state.getState().savedDocIds.size).toBe(1);

    state.setLibraryIdentity("other@b.c");
    expect(state.getState().savedWorks).toEqual([]);
    expect(state.getState().savedDocIds.size).toBe(0);
  });

  it("builds a lookup set from the loaded works", () => {
    state.libraryLoaded([saved("a"), saved("b")]);
    expect(state.isSaved("a")).toBe(true);
    expect(state.isSaved("zzz")).toBe(false);
    expect(state.isSaved(null)).toBe(false);
  });

  it("keeps the loaded list when a refresh fails", () => {
    state.libraryLoaded([saved("a")]);
    state.libraryFailed("down");

    expect(state.getState().libraryStatus).toBe("error");
    expect(state.getState().savedWorks).toHaveLength(1);
  });

  it("adds a saved work without duplicating it", () => {
    state.documentSaved(saved("a"));
    state.documentSaved(saved("a"));
    expect(state.getState().savedWorks).toHaveLength(1);
    expect(state.getState().savedDocIds.size).toBe(1);
  });

  it("removes a work", () => {
    state.libraryLoaded([saved("a"), saved("b")]);
    state.documentRemoved("a");
    expect(state.getState().savedWorks.map((w) => w.doc_id)).toEqual(["b"]);
    expect(state.isSaved("a")).toBe(false);
  });
});

describe("LibraryController", () => {
  let state: AppState;
  beforeEach(() => {
    state = new AppState();
    try {
      window.localStorage.clear();
    } catch {
      /* ignore */
    }
  });

  it("loads saved works", async () => {
    const controller = new LibraryController(state, clientWith(() => json({ works: [saved("a")] })));
    controller.setIdentity("x@y.z");
    await controller.load();

    expect(state.getState().libraryStatus).toBe("ready");
    expect(state.getState().savedDocIds.has("a")).toBe(true);
  });

  it("records a load failure without disturbing search or map", async () => {
    // Give the state a search and a map first.
    const id = state.startSearch();
    state.searchSucceeded(id, { query: "Plato", results: [result("a")], queryParameters: null });
    state.mapLoaded([node("a")], METADATA);

    const controller = new LibraryController(state, clientWith(() => json({ detail: "x" }, 500)));
    controller.setIdentity("x@y.z");
    await controller.load();

    expect(state.getState().libraryStatus).toBe("error");
    expect(state.getState().libraryError).toBeTruthy();
    // Search and map are untouched.
    expect(state.getState().status).toBe("success");
    expect(state.getState().results).toHaveLength(1);
    expect(state.getState().mapStatus).toBe("ready");
    expect(state.getState().mapNodes).toHaveLength(1);
  });

  it("saves a search result and marks it saved only after the server confirms", async () => {
    const controller = new LibraryController(
      state,
      clientWith(() => json({ saved: true, item: saved("a") })),
    );
    controller.setIdentity("x@y.z");

    expect(state.isSaved("a")).toBe(false);
    await controller.save(fromSearchResult(result("a")));
    expect(state.isSaved("a")).toBe(true);
  });

  it("treats a duplicate save as success", async () => {
    const controller = new LibraryController(
      state,
      clientWith(() => json({ saved: false, duplicate: true, item: saved("a") })),
    );
    controller.setIdentity("x@y.z");

    await expect(controller.save(fromSearchResult(result("a")))).resolves.toBe(true);
    expect(state.isSaved("a")).toBe(true);
    // A duplicate is not an error condition.
    expect(state.getState().libraryError).toBeNull();
  });

  it("saves a map-only document without requiring a search", async () => {
    let body: Record<string, unknown> = {};
    const controller = new LibraryController(
      state,
      clientWith((_url, init) => {
        body = JSON.parse(String(init?.body));
        return json({ saved: true, item: saved("map-only") });
      }),
    );
    controller.setIdentity("x@y.z");

    await controller.save(fromMapNode(node("map-only")));

    expect(state.isSaved("map-only")).toBe(true);
    expect(body["doc_id"]).toBe("map-only");
    expect(body["title"]).toBe("Map map-only");
    expect(body["source"]).toBe("zip");
  });

  it("does not mark a document saved when the save fails", async () => {
    const controller = new LibraryController(state, clientWith(() => json({ detail: "no" }, 500)));
    controller.setIdentity("x@y.z");

    await expect(controller.save(fromSearchResult(result("a")))).resolves.toBe(false);
    expect(state.isSaved("a")).toBe(false);
    expect(state.getState().savePhase).toBe("idle");
    expect(state.getState().libraryError).toBeTruthy();
  });

  it("refuses to save without an identity", async () => {
    const fetchImpl = vi.fn() as unknown as typeof fetch;
    const controller = new LibraryController(state, new PersonalLibraryClient({ fetchImpl }));

    await expect(controller.save(fromSearchResult(result("a")))).resolves.toBe(false);
    expect(fetchImpl).not.toHaveBeenCalled();
    expect(state.getState().libraryError).toContain("Library ID");
  });

  it("removes a work and preserves the selection", async () => {
    state.mapLoaded([node("a")], METADATA);
    const selection = new SelectionController(state);
    selection.select("a");

    const controller = new LibraryController(
      state,
      clientWith(() => json({ deleted: true, doc_id: "a" })),
    );
    controller.setIdentity("x@y.z");
    state.libraryLoaded([saved("a")]);

    await controller.remove("a");

    expect(state.isSaved("a")).toBe(false);
    // Removing library membership must not deselect or delete the document.
    expect(state.getState().selectedDocId).toBe("a");
    expect(state.getState().mapNodes).toHaveLength(1);
  });

  it("keeps the work when a delete fails", async () => {
    const controller = new LibraryController(state, clientWith(() => json({ detail: "no" }, 500)));
    controller.setIdentity("x@y.z");
    state.libraryLoaded([saved("a")]);

    await expect(controller.remove("a")).resolves.toBe(false);
    expect(state.isSaved("a")).toBe(true);
    expect(state.getState().libraryError).toBeTruthy();
  });

  it("remembers and restores the identity", () => {
    const controller = new LibraryController(state, clientWith(() => json({ works: [] })));
    controller.setIdentity("remembered@example.com");

    const fresh = new AppState();
    const restored = new LibraryController(fresh, clientWith(() => json({ works: [] })));
    expect(restored.restoreIdentity()).toBe("remembered@example.com");
    expect(fresh.getState().libraryIdentity).toBe("remembered@example.com");
  });

  it("clears the remembered identity", () => {
    const controller = new LibraryController(state, clientWith(() => json({ works: [] })));
    controller.setIdentity("x@y.z");
    controller.clearIdentity();

    const fresh = new AppState();
    const restored = new LibraryController(fresh, clientWith(() => json({ works: [] })));
    expect(restored.restoreIdentity()).toBe("");
  });
});

describe("saved visual state", () => {
  const nodes = ["a", "b", "c", "d"].map(node);
  const index = buildNodeIndex(nodes);

  function visual(overrides: Partial<Parameters<typeof computeNodeVisualState>[0]> = {}) {
    return computeNodeVisualState({
      nodeCount: nodes.length,
      docIdToNodeIndex: index.docIdToNodeIndex,
      resultDocIds: [],
      hasSearchEmphasis: false,
      selectedDocId: null,
      hoveredDocId: null,
      ...overrides,
    });
  }

  const at = (v: { state: Float32Array }, docId: string) =>
    v.state[index.docIdToNodeIndex.get(docId)!]!;

  it("marks saved nodes", () => {
    const v = visual({ savedDocIds: new Set(["b"]) });
    expect(at(v, "b")).toBe(NodeState.Saved);
    expect(at(v, "a")).toBe(NodeState.Normal);
  });

  it("lets search results outrank saved state", () => {
    // A large library must never drown out the handful of results.
    const v = visual({
      savedDocIds: new Set(["a", "b", "c", "d"]),
      resultDocIds: ["b"],
      hasSearchEmphasis: true,
    });
    expect(at(v, "b")).toBe(NodeState.TopResult);
    expect(at(v, "a")).toBe(NodeState.Saved);
  });

  it("lets selection and hover outrank saved state", () => {
    const v = visual({ savedDocIds: new Set(["a", "b"]), selectedDocId: "a", hoveredDocId: "b" });
    expect(at(v, "a")).toBe(NodeState.Selected);
    expect(at(v, "b")).toBe(NodeState.Hovered);
  });

  it("ignores saved ids that are not in the map", () => {
    const v = visual({ savedDocIds: new Set(["ghost"]) });
    expect(Array.from(v.state)).toEqual(new Array(4).fill(NodeState.Normal));
  });

  it("is cheap for a large library", () => {
    const many = new Set(Array.from({ length: 10_000 }, (_, i) => `s${i}`));
    const started = performance.now();
    visual({ savedDocIds: many });
    expect(performance.now() - started).toBeLessThan(50);
  });
});
