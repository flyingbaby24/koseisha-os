// @vitest-environment happy-dom
// OrbitControls attaches listeners to a real element, so CameraController
// needs a DOM. No WebGL context is required.
import { Vector3 } from "three";
import { describe, expect, it } from "vitest";

import type { MapNode, MapProjectionMetadata } from "../src/api/mapTypes";
import type { SearchResult } from "../src/api/types";
import { AppState } from "../src/app/AppState";
import {
  DocumentSelectionResolver,
  fromMapNode,
  fromSearchResult,
} from "../src/app/DocumentSelectionResolver";
import { SelectionController } from "../src/app/SelectionController";
import { CameraController } from "../src/scene/CameraController";
import { computeFocusDistance } from "../src/scene/cameraFraming";
import { buildNodeIndex, docIdAt, indexOfDocId } from "../src/scene/nodeIndex";

function node(docId: string, x = 0, y = 0, z = 0): MapNode {
  return {
    doc_id: docId,
    title: `Map ${docId}`,
    author: "Map Author",
    source: "gutendex",
    x,
    y,
    z,
    cluster: 1,
  };
}

function result(docId: string, similarity = 0.5): SearchResult {
  return {
    doc_id: docId,
    title: `Result ${docId}`,
    author: "Result Author",
    source: "gutendex",
    similarity,
    url: "https://example.org/x",
    parameters: [{ key: "philosophy", value: 0.2 }],
  };
}

const METADATA: MapProjectionMetadata = {
  generated_at: "",
  dataset_fingerprint: "fp",
  document_count: 3,
  embedding_dimension: 384,
  dimensions: 3,
  algorithm: "umap",
  metric: "cosine",
  n_neighbors: 10,
  min_dist: 0.2,
  random_seed: 42,
};

function stateWithMapAndResults(): AppState {
  const state = new AppState();
  state.mapLoaded([node("a", 1, 1, 1), node("b", 2, 2, 2), node("c", 3, 3, 3)], METADATA);
  const id = state.startSearch();
  state.searchSucceeded(id, {
    query: "Plato",
    results: [result("b", 0.9), result("c", 0.7)],
    queryParameters: null,
  });
  return state;
}

describe("doc_id is the only cross-layer identity", () => {
  const nodes = [node("alpha"), node("beta"), node("gamma")];
  const index = buildNodeIndex(nodes);

  it("resolves doc_id to a buffer index", () => {
    expect(indexOfDocId(index, "beta")).toBe(1);
  });

  it("resolves a buffer index back to doc_id", () => {
    expect(docIdAt(index, 2)).toBe("gamma");
  });

  it("round-trips every node", () => {
    for (let i = 0; i < nodes.length; i += 1) {
      expect(indexOfDocId(index, docIdAt(index, i)!)).toBe(i);
    }
  });

  it("does not match on title, author or source", () => {
    // Same title and author, different documents: only doc_id may distinguish.
    const duplicated = buildNodeIndex([node("one"), node("two")]);
    expect(indexOfDocId(duplicated, "Map one")).toBeNull();
    expect(indexOfDocId(duplicated, "Map Author")).toBeNull();
    expect(indexOfDocId(duplicated, "gutendex")).toBeNull();
  });
});

describe("one selection state", () => {
  it("a result click and a node click take the same path", () => {
    const fromResultList = stateWithMapAndResults();
    new SelectionController(fromResultList).select("b");

    const fromMapClick = stateWithMapAndResults();
    new SelectionController(fromMapClick).select("b");

    expect(fromResultList.getState().selectedDocId).toBe("b");
    expect(fromMapClick.getState().selectedDocId).toBe("b");
    expect(fromResultList.getState().selectedDocId).toBe(fromMapClick.getState().selectedDocId);
  });

  it("selecting a node not in the results still selects it", () => {
    const state = stateWithMapAndResults();
    new SelectionController(state).select("a");
    expect(state.getState().selectedDocId).toBe("a");
  });

  it("clearing selection empties it", () => {
    const state = stateWithMapAndResults();
    const selection = new SelectionController(state);
    selection.select("b");
    selection.clear();
    expect(state.getState().selectedDocId).toBeNull();
  });
});

describe("hover is not selection", () => {
  it("hovering leaves selection untouched", () => {
    const state = stateWithMapAndResults();
    state.select("b");
    state.setHovered("c");

    expect(state.getState().hoveredDocId).toBe("c");
    expect(state.getState().selectedDocId).toBe("b");
  });

  it("hovering does not change what the DetailPanel resolves", () => {
    const state = stateWithMapAndResults();
    const resolver = new DocumentSelectionResolver();
    state.select("b");

    const before = resolver.resolve(state.getState());
    state.setHovered("c");
    const after = resolver.resolve(state.getState());

    expect(after?.doc_id).toBe(before?.doc_id);
    expect(after?.doc_id).toBe("b");
  });

  it("clears hover without touching selection", () => {
    const state = stateWithMapAndResults();
    state.select("b");
    state.setHovered("a");
    state.setHovered(null);

    expect(state.getState().hoveredDocId).toBeNull();
    expect(state.getState().selectedDocId).toBe("b");
  });
});

describe("DocumentSelectionResolver", () => {
  const resolver = new DocumentSelectionResolver();

  it("prefers the search result, which carries more information", () => {
    const state = stateWithMapAndResults();
    state.select("b");

    const view = resolver.resolve(state.getState());
    expect(view?.origin).toBe("search");
    expect(view?.title).toBe("Result b");
    expect(view?.similarity).toBe(0.9);
    expect(view?.parameters).toHaveLength(1);
  });

  it("falls back to the map node when the document is not a result", () => {
    const state = stateWithMapAndResults();
    state.select("a");

    const view = resolver.resolve(state.getState());
    expect(view?.origin).toBe("map");
    expect(view?.title).toBe("Map a");
    expect(view?.author).toBe("Map Author");
  });

  it("never fabricates a similarity for a map-only document", () => {
    const view = fromMapNode(node("z"));
    // null, not 0 — zero would assert maximal dissimilarity.
    expect(view.similarity).toBeNull();
    expect(view.similarity).not.toBe(0);
    expect(view.parameters).toBeNull();
    expect(view.url).toBeNull();
  });

  it("returns null when nothing is selected", () => {
    expect(resolver.resolve(stateWithMapAndResults().getState())).toBeNull();
  });

  it("returns null for a doc_id in neither store", () => {
    const state = stateWithMapAndResults();
    state.select("ghost");
    expect(resolver.resolve(state.getState())).toBeNull();
  });

  it("keeps resolving after a search that excludes the selection", () => {
    const state = stateWithMapAndResults();
    state.select("b");

    const id = state.startSearch();
    state.searchSucceeded(id, { query: "Kant", results: [result("c")], queryParameters: null });

    // Selection survives, and now resolves through the map instead.
    const view = resolver.resolve(state.getState());
    expect(view?.doc_id).toBe("b");
    expect(view?.origin).toBe("map");
    expect(view?.similarity).toBeNull();
  });

  it("treats a non-finite similarity as unavailable", () => {
    const view = fromSearchResult({ ...result("a"), similarity: Number.NaN });
    expect(view.similarity).toBeNull();
  });

  it("treats a blank url as absent", () => {
    const view = fromSearchResult({ ...result("a"), url: "   " });
    expect(view.url).toBeNull();
  });

  it("treats an empty parameter list as absent", () => {
    const view = fromSearchResult({ ...result("a"), parameters: [] });
    expect(view.parameters).toBeNull();
  });
});

describe("camera focus", () => {
  function controller(): CameraController {
    // OrbitControls only needs an element with event listeners.
    const element = document.createElement("div");
    return new CameraController(element, 16 / 9);
  }

  it("derives focus distance from the map extent, not a constant", () => {
    expect(computeFocusDistance(100)).toBeCloseTo(12, 6);
    expect(computeFocusDistance(400)).toBeCloseTo(48, 6);
    expect(computeFocusDistance(100)).toBeLessThan(computeFocusDistance(400));
  });

  it("stays positive for a degenerate map", () => {
    expect(computeFocusDistance(0)).toBeGreaterThan(0);
    expect(computeFocusDistance(Number.NaN)).toBeGreaterThan(0);
  });

  it("puts the camera at the focus distance from the target", () => {
    const camera = controller();
    const target = new Vector3(10, 20, 30);
    camera.focusPoint(target, 100);

    expect(camera.camera.position.distanceTo(target)).toBeCloseTo(computeFocusDistance(100), 4);
    camera.dispose();
  });

  it("preserves the viewing direction rather than spinning the space", () => {
    const camera = controller();
    camera.camera.position.set(0, 0, 90);

    const before = camera.camera.position.clone().normalize();
    camera.focusPoint(new Vector3(5, 0, 0), 100);
    const after = camera.camera.position.clone().sub(new Vector3(5, 0, 0)).normalize();

    expect(after.dot(before)).toBeCloseTo(1, 4);
    camera.dispose();
  });

  it("keeps the focused point in front of the near plane", () => {
    const camera = controller();
    camera.focusPoint(new Vector3(0, 0, 0), 100);
    expect(camera.camera.near).toBeGreaterThan(0);
    expect(camera.camera.near).toBeLessThan(camera.camera.position.length());
    camera.dispose();
  });

  it("survives an extreme close zoom without collapsing", () => {
    const camera = controller();
    camera.focusPoint(new Vector3(0, 0, 0), 0.0001);
    expect(Number.isFinite(camera.camera.position.length())).toBe(true);
    expect(camera.camera.near).toBeGreaterThan(0);
    camera.dispose();
  });
});

describe("fit results", () => {
  function controller(): CameraController {
    return new CameraController(document.createElement("div"), 16 / 9);
  }

  it("reports failure with no nodes so the control can disable", () => {
    const camera = controller();
    expect(camera.fitPoints([], 100)).toBe(false);
    camera.dispose();
  });

  it("focuses a single node rather than fitting a zero-sized box", () => {
    const camera = controller();
    const point = new Vector3(4, 5, 6);

    expect(camera.fitPoints([point], 100)).toBe(true);
    // Degenerating to a focus keeps the camera outside the node.
    expect(camera.camera.position.distanceTo(point)).toBeCloseTo(computeFocusDistance(100), 4);
    camera.dispose();
  });

  it("frames multiple nodes around their centre", () => {
    const camera = controller();
    const points = [new Vector3(-10, -10, -10), new Vector3(10, 10, 10)];

    expect(camera.fitPoints(points, 100)).toBe(true);
    // Camera pulls back far enough to contain the spread.
    expect(camera.camera.position.length()).toBeGreaterThan(10);
    camera.dispose();
  });

  it("frames a tight cluster closer than a wide one", () => {
    const tight = controller();
    tight.fitPoints([new Vector3(-8, -8, -8), new Vector3(8, 8, 8)], 100);
    const tightDistance = tight.camera.position.length();
    tight.dispose();

    const wide = controller();
    wide.fitPoints([new Vector3(-40, -40, -40), new Vector3(40, 40, 40)], 100);
    const wideDistance = wide.camera.position.length();
    wide.dispose();

    expect(wideDistance).toBeGreaterThan(tightDistance);
  });

  it("does not dive inside a nearly coincident result set", () => {
    // Ten works by one author can sit almost on top of each other. A literal
    // fit would put the camera within a unit of them; the floor keeps the view
    // readable at single-node focus distance instead.
    const camera = controller();
    const cluster = [
      new Vector3(10, -20, 6),
      new Vector3(10.2, -20.1, 6.3),
      new Vector3(9.9, -20.2, 6.1),
    ];

    expect(camera.fitPoints(cluster, 100)).toBe(true);

    const centre = new Vector3(10.05, -20.1, 6.15);
    expect(camera.camera.position.distanceTo(centre)).toBeCloseTo(computeFocusDistance(100), 0);
    camera.dispose();
  });

  it("does not move the points it frames", () => {
    const camera = controller();
    const points = [new Vector3(1, 2, 3), new Vector3(4, 5, 6)];
    const before = points.map((p) => p.toArray());

    camera.fitPoints(points, 100);

    expect(points.map((p) => p.toArray())).toEqual(before);
    camera.dispose();
  });
});

describe("camera operations remain distinct after focus", () => {
  function controller(): CameraController {
    return new CameraController(document.createElement("div"), 16 / 9);
  }

  it("Reset returns home after a focus", () => {
    const camera = controller();
    const home = camera.camera.position.clone();

    camera.focusPoint(new Vector3(30, 30, 30), 100);
    expect(camera.camera.position.distanceTo(home)).toBeGreaterThan(1);

    camera.reset();
    expect(camera.camera.position.distanceTo(home)).toBeCloseTo(0, 4);
    camera.dispose();
  });

  it("Fit All reframes everything after a focus", () => {
    const camera = controller();
    camera.focusPoint(new Vector3(30, 30, 30), 100);

    const points = [new Vector3(-50, -50, -50), new Vector3(50, 50, 50)];
    expect(camera.fitPoints(points, 100)).toBe(true);
    expect(camera.camera.position.length()).toBeGreaterThan(50);
    camera.dispose();
  });
});
