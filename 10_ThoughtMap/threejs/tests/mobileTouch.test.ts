// @vitest-environment happy-dom
/**
 * Mobile touch: two-finger gestures must never end as a tap.
 *
 * Reproduces the defect recorded in docs/mobile-ux-audit/README.md (M-01):
 * ThoughtMapInteractionController tracks only the most recently pressed
 * pointer, and its pointerup does not check which pointer was released. After
 * a pinch in which that last finger stayed still, lifting a finger is treated
 * as a tap: the selection is cleared (or another node is picked), and on a
 * phone the document sheet drops back to the result list.
 *
 * `it.fails` marks the known defect: the test passes while the bug exists and
 * turns red once it is fixed, at which point change `it.fails` to `it`.
 */
import { afterEach, describe, expect, it } from "vitest";

import type { MapNode } from "../src/api/mapTypes";
import { AppState } from "../src/app/AppState";
import { SelectionController } from "../src/app/SelectionController";
import { ThoughtMapInteractionController } from "../src/app/ThoughtMapInteractionController";
import { CameraController } from "../src/scene/CameraController";
import { NodeRenderer } from "../src/scene/NodeRenderer";

function node(docId: string, x: number, y: number, z: number): MapNode {
  return { doc_id: docId, title: docId, author: "", source: "gutendex", x, y, z, cluster: 0 };
}

const NODES = [node("a", 0, 0, 0), node("b", 10, 10, 10), node("c", -10, 5, 0)];

function fixture() {
  const canvas = document.createElement("canvas");
  const nodes = new NodeRenderer();
  nodes.setNodes(NODES);
  const camera = new CameraController(canvas, 9 / 16);
  const scene = { renderer: { domElement: canvas }, nodes, camera, requestRender: () => {} };
  const state = new AppState();
  state.mapLoaded(NODES, {} as never);
  const interaction = new ThoughtMapInteractionController(
    scene as never,
    state,
    new SelectionController(state),
    { onHover: () => {} },
  );
  state.subscribe((snapshot) => interaction.syncFromState(snapshot));
  state.select("a");

  const finger = (type: string, pointerId: number, x: number, y: number) =>
    canvas.dispatchEvent(
      new PointerEvent(type, { pointerId, pointerType: "touch", clientX: x, clientY: y, bubbles: true }),
    );
  const dispose = () => {
    interaction.dispose();
    camera.dispose();
    nodes.dispose();
  };
  return { state, finger, dispose };
}

describe("two-finger touch gestures", () => {
  let cleanup: (() => void) | null = null;
  afterEach(() => {
    cleanup?.();
    cleanup = null;
  });

  it.fails(
    "KNOWN DEFECT M-01: lifting the still finger after a pinch does not change the selection",
    () => {
      const { state, finger, dispose } = fixture();
      cleanup = dispose;

      finger("pointerdown", 1, 100, 200);
      finger("pointerdown", 2, 220, 120); // second finger lands and stays still
      for (let step = 1; step <= 8; step += 1) {
        finger("pointermove", 1, 100 - step * 9, 200 + step * 9); // first finger pinches
      }
      finger("pointerup", 2, 220, 120); // the still finger lifts first
      finger("pointerup", 1, 28, 272);

      expect(state.getState().selectedDocId).toBe("a");
    },
  );

  it.fails(
    "KNOWN DEFECT M-01: lifting the moving finger first does not change the selection either",
    () => {
      const { state, finger, dispose } = fixture();
      cleanup = dispose;

      finger("pointerdown", 1, 100, 200);
      finger("pointerdown", 2, 220, 120);
      for (let step = 1; step <= 8; step += 1) {
        finger("pointermove", 1, 100 - step * 9, 200 + step * 9);
      }
      finger("pointerup", 1, 28, 272); // the moving finger lifts first
      finger("pointerup", 2, 220, 120);

      expect(state.getState().selectedDocId).toBe("a");
    },
  );

  it("keeps the selection when the last finger placed is the one that moves", () => {
    // Works today, because the controller happens to watch that finger.
    const { state, finger, dispose } = fixture();
    cleanup = dispose;

    finger("pointerdown", 1, 220, 120);
    finger("pointerdown", 2, 100, 200);
    for (let step = 1; step <= 8; step += 1) {
      finger("pointermove", 2, 100 - step * 9, 200 + step * 9);
    }
    finger("pointerup", 1, 220, 120);
    finger("pointerup", 2, 28, 272);

    expect(state.getState().selectedDocId).toBe("a");
  });
});
