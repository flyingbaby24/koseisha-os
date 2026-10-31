// @vitest-environment happy-dom
import { Vector3 } from "three";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { MapNode } from "../src/api/mapTypes";
import type { SearchResult } from "../src/api/types";
import { AppState } from "../src/app/AppState";
import { fromSearchResult } from "../src/app/DocumentSelectionResolver";
import { SearchScreen } from "../src/app/SearchScreen";
import { mapMembership } from "../src/app/mapMembership";
import { DEFAULT_FEATURES } from "../src/config/runtime";
import { describeFilter } from "../src/config/searchOptions";
import { CameraController } from "../src/scene/CameraController";
import { computeFocusDistance } from "../src/scene/cameraFraming";
import { NodeRenderer } from "../src/scene/NodeRenderer";
import { computeNodeVisualState } from "../src/scene/nodeVisualState";
import { DetailPanel } from "../src/ui/DetailPanel";
import { SearchPanel } from "../src/ui/SearchPanel";

function node(docId: string, x = 0, y = 0, z = 0): MapNode {
  return { doc_id: docId, title: `Map ${docId}`, author: "", source: "gutendex", x, y, z, cluster: 0 };
}

function result(docId: string): SearchResult {
  return { doc_id: docId, title: `Result ${docId}`, author: "Plato", source: "gutendex", similarity: 0.5 };
}

describe("camera glide", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("glides to a focus when asked to animate, and arrives exactly", () => {
    const camera = new CameraController(document.createElement("div"), 16 / 9);
    const start = camera.camera.position.clone();
    const target = new Vector3(10, 20, 30);

    camera.focusPoint(target, 100, undefined, { animate: true });

    // Nothing jumps: the move is in flight, and the camera has not teleported.
    expect(camera.isTransitioning).toBe(true);
    expect(camera.camera.position.distanceTo(start)).toBeCloseTo(0, 6);

    expect(camera.update(performance.now() + 10_000)).toBe(true);
    expect(camera.isTransitioning).toBe(false);
    expect(camera.camera.position.distanceTo(target)).toBeCloseTo(computeFocusDistance(100), 4);
    camera.dispose();
  });

  it("still jumps when not asked to animate (Reset, Fit and tests rely on it)", () => {
    const camera = new CameraController(document.createElement("div"), 16 / 9);
    camera.focusPoint(new Vector3(5, 5, 5), 100);
    expect(camera.isTransitioning).toBe(false);
    camera.dispose();
  });

  it("never glides for someone who asked for reduced motion", () => {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: query.includes("reduce"),
      addEventListener: () => {},
      removeEventListener: () => {},
    }));
    const camera = new CameraController(document.createElement("div"), 16 / 9);
    const target = new Vector3(10, 0, 0);
    camera.focusPoint(target, 100, undefined, { animate: true });

    expect(camera.isTransitioning).toBe(false);
    expect(camera.camera.position.distanceTo(target)).toBeCloseTo(computeFocusDistance(100), 4);
    camera.dispose();
  });

  it("centres on the visible map window without changing pixel scale", () => {
    const camera = new CameraController(document.createElement("div"), 1440 / 900);
    camera.setViewport(1440, 900, { top: 80, right: 380, bottom: 0, left: 350 });

    expect(camera.camera.view?.enabled).toBe(true);
    // A point straight ahead projects to the map window centre, not the canvas centre.
    camera.camera.updateMatrixWorld();
    const ahead = camera.camera.position.clone().add(new Vector3(0, 0, -10));
    ahead.project(camera.camera);
    const x = ((ahead.x + 1) / 2) * 1440;
    const y = ((1 - ahead.y) / 2) * 900;
    expect(x).toBeCloseTo(350 + (1440 - 350 - 380) / 2, 3);
    expect(y).toBeCloseTo(80 + (900 - 80) / 2, 3);

    camera.setViewport(1440, 900);
    expect(camera.camera.view?.enabled ?? false).toBe(false);
    expect(camera.camera.fov).toBeCloseTo(camera.baseFov, 9);
    camera.dispose();
  });
});

describe("emphasis layer", () => {
  it("draws only the emphasised nodes, in state order, as a second object", () => {
    const renderer = new NodeRenderer();
    const nodes = ["a", "b", "c", "d", "e"].map((id, i) => node(id, i, i, i));
    renderer.setNodes(nodes);

    const visual = computeNodeVisualState({
      nodeCount: nodes.length,
      docIdToNodeIndex: renderer.nodeIndex.docIdToNodeIndex,
      resultDocIds: ["b", "c"],
      hasSearchEmphasis: true,
      selectedDocId: "b",
      hoveredDocId: null,
      savedDocIds: new Set(["e", "c"]),
    });
    renderer.applyVisualState(visual);

    expect(renderer.emphasisObject).not.toBe(renderer.object);
    expect(renderer.emphasisCount).toBe(3);
    const states = renderer.emphasisObject.geometry.getAttribute("aState");
    const saved = renderer.emphasisObject.geometry.getAttribute("aSaved");
    // Saved (e), result (c, also saved), selected (b) — selection painted last.
    expect([states.getX(0), states.getX(1), states.getX(2)]).toEqual([2, 3, 6]);
    expect([saved.getX(0), saved.getX(1), saved.getX(2)]).toEqual([1, 1, 0]);
    // Same raw coordinates as the cloud, same transform.
    const position = renderer.emphasisObject.geometry.getAttribute("position");
    expect(position.getX(2)).toBeCloseTo(1, 6);
    expect(renderer.emphasisObject.scale.x).toBeCloseTo(renderer.object.scale.x, 9);
    renderer.dispose();
  });

  it("empties the layer when nothing is emphasised", () => {
    const renderer = new NodeRenderer();
    renderer.setNodes([node("a"), node("b")]);
    renderer.applyVisualState(
      computeNodeVisualState({
        nodeCount: 2,
        docIdToNodeIndex: renderer.nodeIndex.docIdToNodeIndex,
        resultDocIds: [],
        hasSearchEmphasis: false,
        selectedDocId: null,
        hoveredDocId: null,
      }),
    );
    expect(renderer.emphasisCount).toBe(0);
    expect(renderer.emphasisObject.visible).toBe(false);
    renderer.dispose();
  });
});

describe("map membership", () => {
  it("is unknown before a map loads and cached per loaded map", () => {
    const state = new AppState();
    expect(mapMembership(state.getState())).toBeNull();

    state.mapLoaded([node("a")], {} as never);
    const first = mapMembership(state.getState());
    expect(first?.has("a")).toBe(true);
    expect(mapMembership(state.getState())).toBe(first);
  });
});

describe("search options", () => {
  it("keeps every option and value, collapsed behind a summary that says what is in effect", () => {
    const state = new AppState();
    const panel = new SearchPanel(state, { onSearch: () => {} });
    panel.render(state.getState());

    const toggle = panel.element.querySelector<HTMLButtonElement>(".tm-options-toggle")!;
    const controls = panel.element.querySelector<HTMLElement>(".tm-search-controls")!;
    expect(controls.hidden).toBe(true);
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(panel.element.querySelectorAll("select")).toHaveLength(4);
    expect(panel.element.querySelector(".tm-options-summary")?.textContent).toBe("Semantic · Top 10");

    toggle.click();
    expect(controls.hidden).toBe(false);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");

    state.setFilter("philosophy");
    state.setSource("zip");
    panel.render(state.getState());
    expect(panel.element.querySelector(".tm-options-summary")?.textContent).toBe(
      "Semantic · Zip import · Philosophy · Top 10",
    );
    expect(panel.element.querySelector(".tm-options-badge")?.textContent).toBe("2");
  });

  it("explains each choice with the backend's meaning", () => {
    expect(describeFilter("")).toContain("No narrowing");
    expect(describeFilter("general")).toContain("no narrowing");
    expect(describeFilter("karma")).toBe("Only works whose strongest axis is Karma.");

    const state = new AppState();
    const panel = new SearchPanel(state, { onSearch: () => {} });
    state.setMode("keyword");
    panel.render(state.getState());
    const mode = panel.element.querySelector<HTMLSelectElement>('select[aria-label="Mode"]')!;
    const hint = document.getElementById(mode.getAttribute("aria-describedby")!) ??
      panel.element.querySelector(`#${mode.getAttribute("aria-describedby")}`);
    expect(hint?.textContent).toContain("Matches your words");
  });
});

describe("document panel actions", () => {
  it("offers Show in map only for a document that has a map position", () => {
    const onLocate = vi.fn();
    const panel = new DetailPanel({ onLocate });
    const state = new AppState();
    state.searchSucceeded(state.startSearch(), {
      query: "q",
      results: [result("in"), result("out")],
      queryParameters: null,
    });
    state.mapLoaded([node("in")], {} as never);

    panel.render(state.getState(), fromSearchResult(result("out")));
    const locate = panel.element.querySelector<HTMLButtonElement>(".tm-locate-button")!;
    expect(locate.disabled).toBe(true);
    expect(panel.element.querySelector(".tm-badge.is-map")?.textContent).toBe("Not in map");

    panel.render(state.getState(), fromSearchResult(result("in")));
    expect(locate.disabled).toBe(false);
    locate.click();
    expect(onLocate).toHaveBeenCalledWith("in");
  });

  it("confirms a finished save in words", () => {
    const panel = new DetailPanel();
    const state = new AppState();
    state.setFeatures({ ...DEFAULT_FEATURES, library_enabled: true });
    state.setLibraryIdentity("reader@example.com");
    state.searchSucceeded(state.startSearch(), { query: "q", results: [result("a")], queryParameters: null });
    const view = fromSearchResult(result("a"));

    panel.render(state.getState(), view);
    state.setSavePhase("saving", "a");
    panel.render(state.getState(), view);
    state.documentSaved({ doc_id: "a", title: "T", author: "", source: "gutendex" });
    panel.render(state.getState(), view);

    const note = panel.element.querySelector<HTMLElement>(".tm-save-note")!;
    expect(note.hidden).toBe(false);
    expect(note.textContent).toContain("Saved to your Library");
    expect(panel.element.querySelector(".tm-save-button")?.textContent).toBe("Saved");
    expect(panel.element.querySelector<HTMLElement>(".tm-badge.is-saved")?.hidden).toBe(false);
  });
});

describe("screen composition", () => {
  function screenWith(results: SearchResult[]): SearchScreen {
    const screen = new SearchScreen(document.createElement("div"));
    screen.state.searchSucceeded(screen.state.startSearch(), {
      query: "q",
      results,
      queryParameters: null,
    });
    return screen;
  }

  it("switches narrow layouts between list and document with the selection", () => {
    const screen = screenWith([result("a")]);
    const root = screen.mapWindow.closest(".tm-layout") as HTMLElement;

    expect(root.dataset["view"]).toBe("list");
    screen.selection.select("a");
    expect(root.dataset["view"]).toBe("detail");
    screen.selection.clear();
    expect(root.dataset["view"]).toBe("list");
    screen.dispose();
  });

  it("re-centres the map when the selected document is chosen again", () => {
    const screen = screenWith([result("a")]);
    const locate = vi.fn();
    screen.onLocateRequest(locate);
    const row = () =>
      screen.mapWindow.closest(".tm-layout")!.querySelector<HTMLElement>('.tm-result[data-doc-id="a"]')!;

    row().click();
    expect(locate).not.toHaveBeenCalled();
    row().click();
    expect(locate).toHaveBeenCalledWith("a");
    screen.dispose();
  });

  it("lights the node when a result row is pointed at", () => {
    const screen = screenWith([result("a")]);
    screen.mapWindow
      .closest(".tm-layout")!
      .querySelector('.tm-result[data-doc-id="a"]')!
      .dispatchEvent(new Event("mouseenter"));
    expect(screen.state.getState().hoveredDocId).toBe("a");
    screen.dispose();
  });

  it("clears the selection with Escape, but not while typing", () => {
    const screen = screenWith([result("a")]);
    screen.selection.select("a");

    const input = document.createElement("input");
    document.body.append(input);
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(screen.state.getState().selectedDocId).toBe("a");

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(screen.state.getState().selectedDocId).toBeNull();
    input.remove();
    screen.dispose();
  });

  it("adopts the camera controls into the map window", () => {
    const screen = screenWith([]);
    const controls = document.createElement("div");
    screen.adoptMapControls(controls, null);
    expect(screen.mapWindow.contains(controls)).toBe(true);
    screen.dispose();
  });
});
