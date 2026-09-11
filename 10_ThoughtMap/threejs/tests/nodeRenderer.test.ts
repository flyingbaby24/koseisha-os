import { Mesh, Points, Scene } from "three";
import { describe, expect, it } from "vitest";

import type { MapNode } from "../src/api/mapTypes";
import { FALLBACK_SOURCE_STYLE, sourceStyle } from "../src/config/sourceStyles";
import { NodeRenderer, REFERENCE_NODE_COUNT, pointSizeForCount } from "../src/scene/NodeRenderer";
import { TARGET_WORLD_EXTENT } from "../src/scene/projectionBounds";

/**
 * Geometry-level checks. Three.js objects can be built without a WebGL
 * context, so these run headless; nothing here needs a real GPU.
 */

function node(docId: string, x: number, y: number, z: number, source = "gutendex"): MapNode {
  return { doc_id: docId, title: docId, author: "", source, x, y, z, cluster: 0 };
}

function corpus(count: number): MapNode[] {
  return Array.from({ length: count }, (_, i) =>
    node(`doc_${i}`, Math.sin(i) * 10, Math.cos(i) * 10, (i / count) * 20 - 10),
  );
}

describe("NodeRenderer geometry", () => {
  it("renders the whole corpus as a single Points object", () => {
    const renderer = new NodeRenderer();
    renderer.setNodes(corpus(500));

    expect(renderer.object).toBeInstanceOf(Points);
    expect(renderer.object.children).toHaveLength(0);
    renderer.dispose();
  });

  it("creates no per-document Mesh", () => {
    // The rule this phase must not break: 4915 documents is one object, not
    // 4915 objects.
    const scene = new Scene();
    const renderer = new NodeRenderer();
    renderer.addTo(scene);
    renderer.setNodes(corpus(1000));

    let meshes = 0;
    let objects = 0;
    scene.traverse((child) => {
      objects += 1;
      if (child instanceof Mesh) {
        meshes += 1;
      }
    });

    expect(meshes).toBe(0);
    // Scene + the single Points object; nothing that scales with node count.
    expect(objects).toBeLessThan(10);
    renderer.dispose();
  });

  it("writes three position floats per node", () => {
    const renderer = new NodeRenderer();
    const nodes = corpus(250);
    renderer.setNodes(nodes);

    const position = renderer.object.geometry.getAttribute("position");
    expect(position.count).toBe(250);
    expect(position.array).toHaveLength(750);
    expect(renderer.count).toBe(250);
    renderer.dispose();
  });

  it("stores raw projection coordinates in the buffer", () => {
    const renderer = new NodeRenderer();
    renderer.setNodes([node("a", 1.5, -2.25, 3.75)]);

    const position = renderer.object.geometry.getAttribute("position");
    // Semantic geometry stays in the data; scaling lives on the transform.
    expect(position.getX(0)).toBeCloseTo(1.5, 5);
    expect(position.getY(0)).toBeCloseTo(-2.25, 5);
    expect(position.getZ(0)).toBeCloseTo(3.75, 5);
    renderer.dispose();
  });

  it("puts the uniform scale and centre offset on the object transform", () => {
    const renderer = new NodeRenderer();
    renderer.setNodes([node("a", 0, 0, 0), node("b", 20, 4, 2)]);

    const { scale } = renderer.object;
    // One scalar for all three axes.
    expect(scale.x).toBeCloseTo(scale.y, 12);
    expect(scale.y).toBeCloseTo(scale.z, 12);
    expect(renderer.bounds.maxExtent * scale.x).toBeCloseTo(TARGET_WORLD_EXTENT, 6);
    renderer.dispose();
  });

  it("colours each node from its source", () => {
    const renderer = new NodeRenderer();
    renderer.setNodes([node("a", 0, 0, 0, "gutendex"), node("b", 1, 1, 1, "zip")]);

    const color = renderer.object.geometry.getAttribute("color");
    const gutendex = sourceStyle("gutendex").color;
    const zip = sourceStyle("zip").color;

    expect(color.getX(0)).toBeCloseTo(gutendex[0], 5);
    expect(color.getX(1)).toBeCloseTo(zip[0], 5);
    renderer.dispose();
  });

  it("renders an unknown source with the fallback colour instead of failing", () => {
    const renderer = new NodeRenderer();
    expect(() => renderer.setNodes([node("a", 0, 0, 0, "future_source")])).not.toThrow();

    const color = renderer.object.geometry.getAttribute("color");
    expect(color.getX(0)).toBeCloseTo(FALLBACK_SOURCE_STYLE.color[0], 5);
    renderer.dispose();
  });

  it("exposes the doc_id mapping needed for picking", () => {
    const renderer = new NodeRenderer();
    renderer.setNodes([node("alpha", 0, 0, 0), node("beta", 1, 1, 1)]);

    expect(renderer.nodeIndex.nodeIndexToDocId).toEqual(["alpha", "beta"]);
    expect(renderer.nodeIndex.docIdToNodeIndex.get("beta")).toBe(1);
    renderer.dispose();
  });

  it("replaces rather than accumulates geometry on reload", () => {
    const renderer = new NodeRenderer();
    renderer.setNodes(corpus(300));
    renderer.setNodes(corpus(120));

    expect(renderer.object.geometry.getAttribute("position").count).toBe(120);
    expect(renderer.count).toBe(120);
    expect(renderer.nodeIndex.nodeIndexToDocId).toHaveLength(120);
    renderer.dispose();
  });

  it("hides itself and stays safe with no nodes", () => {
    const renderer = new NodeRenderer();
    renderer.setNodes(corpus(10));
    renderer.clear();

    expect(renderer.object.visible).toBe(false);
    expect(renderer.count).toBe(0);
    expect(renderer.bounds.maxExtent).toBe(0);
    renderer.dispose();
  });

  it("builds a large cloud without per-node objects", () => {
    // Renderer scalability: 50k nodes must still be one object.
    const renderer = new NodeRenderer();
    const started = performance.now();
    renderer.setNodes(corpus(50_000));
    const elapsed = performance.now() - started;

    expect(renderer.object.geometry.getAttribute("position").count).toBe(50_000);
    expect(renderer.object.children).toHaveLength(0);
    expect(elapsed).toBeLessThan(2000);
    renderer.dispose();
  });

  it("shrinks point size as the corpus grows", () => {
    // The map is always fitted to the same world extent, so a bigger corpus
    // packs more documents into the same volume. Holding size fixed made
    // 63,891 nodes overlap into blobs.
    const small = pointSizeForCount(REFERENCE_NODE_COUNT);
    const full = pointSizeForCount(63_891);

    expect(full).toBeLessThan(small);
    // Roughly 1/sqrt(count): 13x the documents, about 3.6x smaller.
    expect(small / full).toBeGreaterThan(3);
    expect(small / full).toBeLessThan(4.5);
  });

  it("clamps point size at both ends", () => {
    // Never larger than the reference, however tiny the corpus...
    expect(pointSizeForCount(1)).toBeLessThanOrEqual(pointSizeForCount(REFERENCE_NODE_COUNT));
    // ...and never so small it vanishes, however large.
    expect(pointSizeForCount(10_000_000)).toBeGreaterThan(0.1);
  });

  it("degrades safely for a nonsense count", () => {
    expect(pointSizeForCount(0)).toBeGreaterThan(0);
    expect(pointSizeForCount(-5)).toBeGreaterThan(0);
    expect(pointSizeForCount(Number.NaN)).toBeGreaterThan(0);
  });

  it("applies the density-aware size when nodes are loaded", () => {
    const renderer = new NodeRenderer();
    renderer.setNodes(corpus(20_000));

    const uniform = renderer.object.material as unknown as {
      uniforms: { uPointWorldSize: { value: number } };
    };
    expect(uniform.uniforms.uPointWorldSize.value).toBeCloseTo(pointSizeForCount(20_000), 6);
    renderer.dispose();
  });

  it("does not resolve raycasts until T4 installs picking", () => {
    const renderer = new NodeRenderer();
    renderer.setNodes(corpus(10));

    const hits: unknown[] = [];
    renderer.object.raycast({} as never, hits as never);
    expect(hits).toHaveLength(0);
    renderer.dispose();
  });
});
