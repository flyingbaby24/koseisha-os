import { describe, expect, it, vi } from "vitest";

import type { ApiError } from "../src/api/errors";
import { ThoughtMapApiClient } from "../src/api/ThoughtMapApiClient";
import type { MapNode, MapProjectionMetadata, MapResponse } from "../src/api/mapTypes";
import { isMapNode } from "../src/api/mapTypes";
import { AppState } from "../src/app/AppState";
import { MapController } from "../src/app/MapController";
import type { SearchResult } from "../src/api/types";

function metadata(overrides: Partial<MapProjectionMetadata> = {}): MapProjectionMetadata {
  return {
    generated_at: "2026-09-09T00:00:00+00:00",
    dataset_fingerprint: "8fbea924",
    document_count: 3,
    embedding_dimension: 384,
    dimensions: 3,
    algorithm: "umap",
    metric: "cosine",
    n_neighbors: 10,
    min_dist: 0.2,
    random_seed: 42,
    cluster_algorithm: "kmeans",
    cluster_count: 8,
    ...overrides,
  };
}

function node(docId: string, x = 0, y = 0, z = 0, source = "gutendex"): MapNode {
  return { doc_id: docId, title: `Title ${docId}`, author: "Author", source, x, y, z, cluster: 0 };
}

function mapResponse(nodes: MapNode[], schemaVersion = 1): MapResponse {
  return { schema_version: schemaVersion, projection: metadata(), nodes };
}

function ok(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function clientReturning(response: Response | (() => Response)): ThoughtMapApiClient {
  const fetchImpl = vi.fn(async () =>
    typeof response === "function" ? response() : response.clone(),
  ) as unknown as typeof fetch;
  return new ThoughtMapApiClient({ fetchImpl });
}

describe("map response parsing", () => {
  it("requests /map", async () => {
    const urls: string[] = [];
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      urls.push(String(input));
      return ok(mapResponse([node("a")]));
    }) as unknown as typeof fetch;

    await new ThoughtMapApiClient({ fetchImpl }).map();
    expect(urls[0]).toBe("/api/map");
  });

  it("returns metadata and nodes", async () => {
    const client = clientReturning(ok(mapResponse([node("a", 1, 2, 3)])));
    const response = await client.map();

    expect(response.projection.algorithm).toBe("umap");
    expect(response.projection.random_seed).toBe(42);
    expect(response.nodes[0]).toMatchObject({ doc_id: "a", x: 1, y: 2, z: 3 });
  });

  it("rejects an unsupported schema version rather than mis-reading it", async () => {
    const client = clientReturning(ok(mapResponse([node("a")], 2)));
    await expect(client.map()).rejects.toMatchObject({ kind: "parse" });
  });

  it("rejects a payload with no nodes array", async () => {
    const client = clientReturning(ok({ schema_version: 1, projection: metadata() }));
    await expect(client.map()).rejects.toMatchObject({ kind: "parse" });
  });

  it("translates 503 into a thought-space message, not the search one", async () => {
    const fetchImpl = vi.fn(async () =>
      new Response(JSON.stringify({ detail: "The 3D projection has not been generated yet." }), {
        status: 503,
      }),
    ) as unknown as typeof fetch;

    const error = (await new ThoughtMapApiClient({ fetchImpl })
      .map()
      .then(() => null)
      .catch((caught: unknown) => caught)) as ApiError;

    expect(error.kind).toBe("unavailable");
    expect(error.message).toContain("thought space");
    // A missing projection has nothing to do with the embedding model.
    expect(error.message).not.toContain("embedding model");
  });

  it("keeps the search-specific 503 message on /search", async () => {
    const fetchImpl = vi.fn(async () =>
      new Response(JSON.stringify({ detail: "sentence-transformers is not installed" }), {
        status: 503,
      }),
    ) as unknown as typeof fetch;

    const error = (await new ThoughtMapApiClient({ fetchImpl })
      .search({ q: "Plato", mode: "semantic" })
      .then(() => null)
      .catch((caught: unknown) => caught)) as ApiError;

    expect(error.message).toContain("embedding model");
  });
});

describe("isMapNode", () => {
  it("accepts a well formed node", () => {
    expect(isMapNode(node("a", 1, 2, 3))).toBe(true);
  });

  it("rejects non-finite coordinates", () => {
    expect(isMapNode({ ...node("a"), x: Number.NaN })).toBe(false);
    expect(isMapNode({ ...node("a"), y: Number.POSITIVE_INFINITY })).toBe(false);
  });

  it("rejects a missing doc_id", () => {
    expect(isMapNode({ ...node("a"), doc_id: "" })).toBe(false);
    expect(isMapNode(null)).toBe(false);
  });
});

describe("map state lifecycle", () => {
  it("starts idle with no map data", () => {
    const state = new AppState().getState();
    expect(state.mapStatus).toBe("idle");
    expect(state.mapNodes).toEqual([]);
    expect(state.mapMetadata).toBeNull();
    expect(state.mapError).toBeNull();
  });

  it("moves through loading to ready", async () => {
    const state = new AppState();
    const controller = new MapController(state, clientReturning(ok(mapResponse([node("a"), node("b")]))));

    const seen: string[] = [];
    state.subscribe((snapshot) => seen.push(snapshot.mapStatus));

    await controller.load();

    expect(seen).toContain("loading");
    expect(state.getState().mapStatus).toBe("ready");
    expect(state.getState().mapNodes).toHaveLength(2);
    expect(state.getState().mapMetadata?.dataset_fingerprint).toBe("8fbea924");
  });

  it("records a map error", async () => {
    const fetchImpl = vi.fn(async () => new Response("nope", { status: 503 })) as unknown as typeof fetch;
    const state = new AppState();
    await new MapController(state, new ThoughtMapApiClient({ fetchImpl })).load();

    expect(state.getState().mapStatus).toBe("error");
    expect(state.getState().mapError).toContain("thought space");
  });

  it("drops malformed nodes instead of poisoning the whole cloud", async () => {
    const nodes = [node("a", 1, 1, 1), { ...node("b"), x: Number.NaN }, node("c", 2, 2, 2)];
    const state = new AppState();
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});

    await new MapController(state, clientReturning(ok(mapResponse(nodes as MapNode[])))).load();

    expect(state.getState().mapNodes.map((n) => n.doc_id)).toEqual(["a", "c"]);
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });

  it("keeps an already loaded map when a later refresh fails", async () => {
    const state = new AppState();
    await new MapController(state, clientReturning(ok(mapResponse([node("a")])))).load();
    expect(state.getState().mapNodes).toHaveLength(1);

    const failing = vi.fn(async () => new Response("down", { status: 500 })) as unknown as typeof fetch;
    await new MapController(state, new ThoughtMapApiClient({ fetchImpl: failing })).load();

    expect(state.getState().mapStatus).toBe("error");
    // Losing the connection must not empty a space the user is looking at.
    expect(state.getState().mapNodes).toHaveLength(1);
  });
});

describe("map and search state are independent", () => {
  const result: SearchResult = {
    doc_id: "a",
    title: "A",
    author: "Author",
    source: "gutendex",
    similarity: 0.5,
  };

  it("a search failure leaves the loaded map intact", async () => {
    const state = new AppState();
    await new MapController(state, clientReturning(ok(mapResponse([node("a"), node("b")])))).load();

    state.searchFailed(state.startSearch(), "The ThoughtMap API failed to complete the search.");

    expect(state.getState().status).toBe("error");
    expect(state.getState().mapStatus).toBe("ready");
    expect(state.getState().mapNodes).toHaveLength(2);
  });

  it("a map failure leaves search fully usable", async () => {
    const state = new AppState();
    const failing = vi.fn(async () => new Response("down", { status: 503 })) as unknown as typeof fetch;
    await new MapController(state, new ThoughtMapApiClient({ fetchImpl: failing })).load();

    const id = state.startSearch();
    state.searchSucceeded(id, { query: "Plato", results: [result], queryParameters: null });

    expect(state.getState().mapStatus).toBe("error");
    expect(state.getState().status).toBe("success");
    expect(state.getState().results).toHaveLength(1);
  });

  it("a successful search does not disturb map state", async () => {
    const state = new AppState();
    await new MapController(state, clientReturning(ok(mapResponse([node("a")])))).load();
    const before = state.getState().mapNodes;

    const id = state.startSearch();
    state.searchSucceeded(id, { query: "Plato", results: [result], queryParameters: null });

    expect(state.getState().mapNodes).toBe(before);
    expect(state.getState().mapStatus).toBe("ready");
  });
});
