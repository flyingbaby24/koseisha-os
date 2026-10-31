// @vitest-environment happy-dom
/**
 * Touch gestures on the thought space, and the mouse behaviour they must not
 * change. Findings from docs/mobile-ux-audit/README.md:
 *
 *   M-01  a two-finger gesture must never end as a tap
 *   M-02  a finger that wobbles a little still taps — the node it touched
 *   M-03  a finger tap on empty space does not clear the selection
 *   M-14  the tap that stops a camera glide only stops it
 *
 * Each touch rule is paired with the mouse behaviour it leaves alone.
 */
import { Vector3 } from "three";
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

/** happy-dom canvases measure 0 wide, so picking falls back to 300 x 150. */
const CANVAS_W = 300;
const CANVAS_H = 150;

function fixture() {
  const canvas = document.createElement("canvas");
  const nodes = new NodeRenderer();
  nodes.setNodes(NODES);
  const camera = new CameraController(canvas, CANVAS_W / CANVAS_H);
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

  const pointer = (
    type: string,
    pointerId: number,
    x: number,
    y: number,
    pointerType: "touch" | "mouse" = "touch",
  ) =>
    canvas.dispatchEvent(
      new PointerEvent(type, { pointerId, pointerType, clientX: x, clientY: y, button: 0, bubbles: true }),
    );

  /** Where a node is on the canvas right now. */
  const screenOf = (docId: string): { x: number; y: number } => {
    const index = nodes.nodeIndex.docIdToNodeIndex.get(docId)!;
    const screen = nodes.projectToScreen(camera.camera, CANVAS_W, CANVAS_H);
    return { x: screen[index * 3]!, y: screen[index * 3 + 1]! };
  };

  /** A point with no node within any pick radius. */
  const emptyPoint = { x: 2, y: 2 };

  const dispose = () => {
    interaction.dispose();
    camera.dispose();
    nodes.dispose();
  };
  return { state, camera, nodes, pointer, screenOf, emptyPoint, dispose };
}

let cleanup: (() => void) | null = null;
afterEach(() => {
  cleanup?.();
  cleanup = null;
});

function setup() {
  const f = fixture();
  cleanup = f.dispose;
  return f;
}

describe("M-01: two-finger gestures never end as a tap", () => {
  it("keeps the selection when the still finger lifts first after a pinch", () => {
    const { state, pointer } = setup();

    pointer("pointerdown", 1, 100, 200);
    pointer("pointerdown", 2, 220, 120); // second finger lands and stays still
    for (let step = 1; step <= 8; step += 1) {
      pointer("pointermove", 1, 100 - step * 9, 200 + step * 9); // first finger pinches
    }
    pointer("pointerup", 2, 220, 120);
    pointer("pointerup", 1, 28, 272);

    expect(state.getState().selectedDocId).toBe("a");
  });

  it("keeps the selection when the moving finger lifts first", () => {
    const { state, pointer } = setup();

    pointer("pointerdown", 1, 100, 200);
    pointer("pointerdown", 2, 220, 120);
    for (let step = 1; step <= 8; step += 1) {
      pointer("pointermove", 1, 100 - step * 9, 200 + step * 9);
    }
    pointer("pointerup", 1, 28, 272);
    pointer("pointerup", 2, 220, 120);

    expect(state.getState().selectedDocId).toBe("a");
  });

  it("keeps the selection when the last finger placed is the one that moves", () => {
    const { state, pointer } = setup();

    pointer("pointerdown", 1, 220, 120);
    pointer("pointerdown", 2, 100, 200);
    for (let step = 1; step <= 8; step += 1) {
      pointer("pointermove", 2, 100 - step * 9, 200 + step * 9);
    }
    pointer("pointerup", 1, 220, 120);
    pointer("pointerup", 2, 28, 272);

    expect(state.getState().selectedDocId).toBe("a");
  });

  it("keeps the selection for a two-finger tap with no movement at all", () => {
    const { state, pointer, screenOf } = setup();
    const b = screenOf("b");

    pointer("pointerdown", 1, b.x, b.y);
    pointer("pointerdown", 2, b.x + 40, b.y);
    pointer("pointerup", 1, b.x, b.y);
    pointer("pointerup", 2, b.x + 40, b.y);

    expect(state.getState().selectedDocId).toBe("a");
  });

  it("ignores a release from a pointer it never saw go down", () => {
    const { state, pointer, emptyPoint } = setup();
    pointer("pointerup", 7, emptyPoint.x, emptyPoint.y, "mouse");
    expect(state.getState().selectedDocId).toBe("a");
  });

  it("recovers after a cancelled pointer, so the next tap still selects", () => {
    const { state, pointer, screenOf } = setup();
    pointer("pointerdown", 1, 50, 50);
    pointer("pointercancel", 1, 50, 50);

    const b = screenOf("b");
    pointer("pointerdown", 2, b.x, b.y);
    pointer("pointerup", 2, b.x, b.y);

    expect(state.getState().selectedDocId).toBe("b");
  });
});

describe("M-02: a wobbling finger still taps", () => {
  it("selects the node the finger touched, despite 8 px of wobble", () => {
    const { state, pointer, screenOf } = setup();
    const b = screenOf("b");

    pointer("pointerdown", 1, b.x, b.y);
    pointer("pointermove", 1, b.x + 6, b.y + 5);
    pointer("pointerup", 1, b.x + 6, b.y + 5);

    expect(state.getState().selectedDocId).toBe("b");
  });

  it("treats a longer finger movement as an orbit, not a tap", () => {
    const { state, pointer, screenOf } = setup();
    const b = screenOf("b");

    pointer("pointerdown", 1, b.x, b.y);
    pointer("pointermove", 1, b.x + 14, b.y);
    pointer("pointerup", 1, b.x + 14, b.y);

    expect(state.getState().selectedDocId).toBe("a");
  });

  it("keeps the mouse's tighter 5 px threshold (mouse unchanged)", () => {
    const { state, pointer, screenOf } = setup();
    const b = screenOf("b");

    pointer("pointerdown", 1, b.x, b.y, "mouse");
    pointer("pointermove", 1, b.x + 6, b.y + 5, "mouse");
    pointer("pointerup", 1, b.x + 6, b.y + 5, "mouse");

    expect(state.getState().selectedDocId).toBe("a");
  });

  it("still selects with a plain mouse click (mouse unchanged)", () => {
    const { state, pointer, screenOf } = setup();
    const b = screenOf("b");

    pointer("pointerdown", 1, b.x, b.y, "mouse");
    pointer("pointerup", 1, b.x, b.y, "mouse");

    expect(state.getState().selectedDocId).toBe("b");
  });
});

describe("M-03: an empty-space tap does not drop the document on touch", () => {
  it("keeps the selection when a finger taps empty space", () => {
    const { state, pointer, emptyPoint } = setup();

    pointer("pointerdown", 1, emptyPoint.x, emptyPoint.y);
    pointer("pointerup", 1, emptyPoint.x, emptyPoint.y);

    expect(state.getState().selectedDocId).toBe("a");
  });

  it("still clears the selection on a mouse click in empty space (mouse unchanged)", () => {
    const { state, pointer, emptyPoint } = setup();

    pointer("pointerdown", 1, emptyPoint.x, emptyPoint.y, "mouse");
    pointer("pointerup", 1, emptyPoint.x, emptyPoint.y, "mouse");

    expect(state.getState().selectedDocId).toBeNull();
  });
});

describe("M-14: the tap that stops a glide only stops it", () => {
  function startGlide(camera: CameraController) {
    camera.focusPoint(new Vector3(40, -30, 20), 100, undefined, { animate: true });
    expect(camera.isTransitioning).toBe(true);
  }

  it("does not select with the finger that interrupts a glide", () => {
    const { state, camera, pointer, screenOf } = setup();
    startGlide(camera);
    const b = screenOf("b");

    pointer("pointerdown", 1, b.x, b.y);
    pointer("pointerup", 1, b.x, b.y);

    expect(camera.isTransitioning).toBe(false);
    expect(state.getState().selectedDocId).toBe("a");
  });

  it("selects with the next tap once the camera has stopped", () => {
    const { state, camera, pointer, screenOf } = setup();
    startGlide(camera);
    let b = screenOf("b");
    pointer("pointerdown", 1, b.x, b.y);
    pointer("pointerup", 1, b.x, b.y);

    b = screenOf("b");
    pointer("pointerdown", 2, b.x, b.y);
    pointer("pointerup", 2, b.x, b.y);

    expect(state.getState().selectedDocId).toBe("b");
  });

  it("still selects with a mouse click during a glide (mouse unchanged)", () => {
    const { state, camera, pointer, screenOf } = setup();
    startGlide(camera);
    const b = screenOf("b");

    pointer("pointerdown", 1, b.x, b.y, "mouse");
    pointer("pointerup", 1, b.x, b.y, "mouse");

    expect(state.getState().selectedDocId).toBe("b");
  });
});
