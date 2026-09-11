import { describe, expect, it } from "vitest";

import type { MapNode } from "../src/api/mapTypes";
import { buildNodeIndex } from "../src/scene/nodeIndex";
import {
  NodeState,
  computeNodeVisualState,
  joinMetrics,
  type VisualStateInput,
} from "../src/scene/nodeVisualState";

function node(docId: string): MapNode {
  return { doc_id: docId, title: docId, author: "", source: "gutendex", x: 0, y: 0, z: 0, cluster: 0 };
}

const NODES = ["a", "b", "c", "d", "e"].map(node);
const INDEX = buildNodeIndex(NODES);

function input(overrides: Partial<VisualStateInput> = {}): VisualStateInput {
  return {
    nodeCount: NODES.length,
    docIdToNodeIndex: INDEX.docIdToNodeIndex,
    resultDocIds: [],
    hasSearchEmphasis: false,
    selectedDocId: null,
    hoveredDocId: null,
    ...overrides,
  };
}

/** State of one node by doc_id. */
function stateOf(visual: { state: Float32Array }, docId: string): number {
  return visual.state[INDEX.docIdToNodeIndex.get(docId)!]!;
}

describe("no search active", () => {
  it("leaves every node at the resting appearance", () => {
    const visual = computeNodeVisualState(input());
    expect(Array.from(visual.state)).toEqual(new Array(5).fill(NodeState.Normal));
  });

  it("assigns no rank emphasis", () => {
    const visual = computeNodeVisualState(input());
    expect(Array.from(visual.emphasis)).toEqual(new Array(5).fill(0));
  });
});

describe("search emphasis", () => {
  const withResults = input({ resultDocIds: ["b", "d"], hasSearchEmphasis: true });

  it("marks the top result distinctly from the rest", () => {
    const visual = computeNodeVisualState(withResults);
    expect(stateOf(visual, "b")).toBe(NodeState.TopResult);
    expect(stateOf(visual, "d")).toBe(NodeState.Result);
  });

  it("dims non-results but keeps them present", () => {
    const visual = computeNodeVisualState(withResults);
    // Dimmed, not removed: the surrounding space still gives context.
    expect(stateOf(visual, "a")).toBe(NodeState.Dimmed);
    expect(stateOf(visual, "c")).toBe(NodeState.Dimmed);
    expect(visual.state).toHaveLength(5);
  });

  it("scales emphasis down by rank", () => {
    const visual = computeNodeVisualState(
      input({ resultDocIds: ["a", "b", "c"], hasSearchEmphasis: true }),
    );
    const first = visual.emphasis[INDEX.docIdToNodeIndex.get("a")!]!;
    const last = visual.emphasis[INDEX.docIdToNodeIndex.get("c")!]!;

    expect(first).toBe(1);
    expect(last).toBeLessThan(first);
    expect(last).toBeGreaterThan(0);
  });

  it("gives a single result full emphasis without dividing by zero", () => {
    const visual = computeNodeVisualState(input({ resultDocIds: ["a"], hasSearchEmphasis: true }));
    expect(visual.emphasis[INDEX.docIdToNodeIndex.get("a")!]).toBe(1);
  });

  it("dims everything uniformly for a zero-result search", () => {
    const visual = computeNodeVisualState(input({ resultDocIds: [], hasSearchEmphasis: true }));
    expect(Array.from(visual.state)).toEqual(new Array(5).fill(NodeState.Dimmed));
  });

  it("replaces the previous emphasis rather than accumulating it", () => {
    const first = computeNodeVisualState(input({ resultDocIds: ["a"], hasSearchEmphasis: true }));
    const second = computeNodeVisualState(input({ resultDocIds: ["e"], hasSearchEmphasis: true }));

    expect(stateOf(first, "a")).toBe(NodeState.TopResult);
    expect(stateOf(second, "a")).toBe(NodeState.Dimmed);
    expect(stateOf(second, "e")).toBe(NodeState.TopResult);
  });
});

describe("state precedence", () => {
  it("selected beats top result", () => {
    const visual = computeNodeVisualState(
      input({ resultDocIds: ["a"], hasSearchEmphasis: true, selectedDocId: "a" }),
    );
    expect(stateOf(visual, "a")).toBe(NodeState.Selected);
  });

  it("selected beats hovered", () => {
    const visual = computeNodeVisualState(input({ selectedDocId: "a", hoveredDocId: "a" }));
    expect(stateOf(visual, "a")).toBe(NodeState.Selected);
  });

  it("hovered beats top result", () => {
    const visual = computeNodeVisualState(
      input({ resultDocIds: ["a"], hasSearchEmphasis: true, hoveredDocId: "a" }),
    );
    expect(stateOf(visual, "a")).toBe(NodeState.Hovered);
  });

  it("hovered beats dimmed", () => {
    const visual = computeNodeVisualState(
      input({ resultDocIds: ["b"], hasSearchEmphasis: true, hoveredDocId: "a" }),
    );
    expect(stateOf(visual, "a")).toBe(NodeState.Hovered);
  });

  it("keeps a selected node unmistakable outside the result set", () => {
    // The case that matters: selection survives a search that excludes it.
    const visual = computeNodeVisualState(
      input({ resultDocIds: ["b", "c"], hasSearchEmphasis: true, selectedDocId: "e" }),
    );
    expect(stateOf(visual, "e")).toBe(NodeState.Selected);
  });

  it("is deterministic regardless of how many states apply", () => {
    const once = computeNodeVisualState(
      input({
        resultDocIds: ["a", "b"],
        hasSearchEmphasis: true,
        selectedDocId: "a",
        hoveredDocId: "b",
      }),
    );
    const twice = computeNodeVisualState(
      input({
        resultDocIds: ["a", "b"],
        hasSearchEmphasis: true,
        selectedDocId: "a",
        hoveredDocId: "b",
      }),
    );
    expect(Array.from(once.state)).toEqual(Array.from(twice.state));
  });
});

describe("missing map joins", () => {
  it("reports results with no node and still marks the rest", () => {
    const visual = computeNodeVisualState(
      input({ resultDocIds: ["a", "ghost", "c"], hasSearchEmphasis: true }),
    );

    expect(visual.joinedCount).toBe(2);
    expect(visual.missingDocIds).toEqual(["ghost"]);
    expect(stateOf(visual, "a")).toBe(NodeState.TopResult);
    expect(stateOf(visual, "c")).toBe(NodeState.Result);
  });

  it("does not throw when nothing joins", () => {
    const visual = computeNodeVisualState(
      input({ resultDocIds: ["x", "y"], hasSearchEmphasis: true }),
    );
    expect(visual.joinedCount).toBe(0);
    expect(visual.missingDocIds).toEqual(["x", "y"]);
  });

  it("ignores a selected or hovered id that has no node", () => {
    const visual = computeNodeVisualState(input({ selectedDocId: "ghost", hoveredDocId: "ghost" }));
    expect(Array.from(visual.state)).toEqual(new Array(5).fill(NodeState.Normal));
  });
});

describe("join metrics", () => {
  it("counts joins and misses", () => {
    const metrics = joinMetrics(["a", "b", "ghost"], INDEX.docIdToNodeIndex);
    expect(metrics).toEqual({
      resultsReturned: 3,
      mapJoins: 2,
      missingJoins: 1,
      missingDocIds: ["ghost"],
    });
  });

  it("reports a fully joined result set", () => {
    const metrics = joinMetrics(["a", "b"], INDEX.docIdToNodeIndex);
    expect(metrics.mapJoins).toBe(2);
    expect(metrics.missingJoins).toBe(0);
  });

  it("handles an empty result set", () => {
    expect(joinMetrics([], INDEX.docIdToNodeIndex).resultsReturned).toBe(0);
  });
});
