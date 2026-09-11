import { Vector3 } from "three";

import type { ThoughtMapScene } from "../scene/ThoughtMapScene";
import { computeNodeVisualState, joinMetrics } from "../scene/nodeVisualState";
import {
  exceedsDragThreshold,
  pickNearestNode,
  pickRadiusForPointer,
  type PointerOrigin,
} from "../scene/picking";
import type { AppState, AppStateSnapshot } from "./AppState";
import type { SelectionController } from "./SelectionController";

export interface HoverInfo {
  docId: string;
  title: string;
  author: string;
  source: string;
  /** Present only when the hovered node is in the current result set. */
  similarity: number | null;
  /** Pointer position in CSS pixels, for tooltip placement. */
  x: number;
  y: number;
}

export interface InteractionCallbacks {
  onHover: (info: HoverInfo | null) => void;
}

/**
 * How long to trust a booked animation frame before assuming it will never
 * arrive. Comfortably longer than a frame at any real refresh rate, short
 * enough that hover recovers immediately when painting resumes.
 */
const STALE_HOVER_FRAME_MS = 250;

/**
 * Turns pointer input on the canvas into application state, and application
 * state into renderer commands.
 *
 * This is the only place the two directions meet, which keeps
 * `ThoughtMapScene` a renderer and `NodeRenderer` a GPU concern. Neither of
 * them calls the API, owns AppState, or decides what selection means.
 */
export class ThoughtMapInteractionController {
  private readonly scratchPoint = new Vector3();

  private pointerOrigin: PointerOrigin | null = null;
  private pointerId: number | null = null;
  private pointerType = "mouse";
  private dragging = false;

  /** Hover picking is deferred to a frame so a fast drag cannot flood it. */
  private hoverFrame = 0;
  private hoverRequestedAt = 0;
  private pendingHover: { x: number; y: number } | null = null;

  private lastVisualKey = "";
  private lastNodesRef: unknown = null;
  private lastSavedRef: unknown = null;
  private disposed = false;

  constructor(
    private readonly scene: ThoughtMapScene,
    private readonly state: AppState,
    private readonly selection: SelectionController,
    private readonly callbacks: InteractionCallbacks,
  ) {
    const canvas = this.canvas;
    canvas.addEventListener("pointerdown", this.handlePointerDown);
    canvas.addEventListener("pointermove", this.handlePointerMove);
    canvas.addEventListener("pointerup", this.handlePointerUp);
    canvas.addEventListener("pointercancel", this.handlePointerCancel);
    canvas.addEventListener("pointerleave", this.handlePointerLeave);
  }

  private get canvas(): HTMLCanvasElement {
    return this.scene.renderer.domElement;
  }

  /**
   * Push application state into the renderer.
   *
   * Called on every state change, but the expensive part is skipped unless
   * something that actually affects appearance moved.
   */
  syncFromState(snapshot: AppStateSnapshot): void {
    const nodeIndex = this.scene.nodes.nodeIndex;
    const nodeCount = this.scene.nodes.count;

    if (nodeCount === 0) {
      return;
    }

    // Cheap identity of everything the visual state depends on.
    const key = [
      snapshot.hasSearchEmphasis ? "1" : "0",
      snapshot.emphasisDocIds.length,
      snapshot.emphasisDocIds[0] ?? "",
      snapshot.emphasisDocIds[snapshot.emphasisDocIds.length - 1] ?? "",
      snapshot.selectedDocId ?? "",
      snapshot.hoveredDocId ?? "",
      // Saved membership changes appearance, so it belongs in the key. Size
      // plus a cheap fingerprint avoids hashing the whole set every render.
      snapshot.savedDocIds.size,
      nodeCount,
    ].join("|");

    if (
      key === this.lastVisualKey &&
      snapshot.mapNodes === this.lastNodesRef &&
      snapshot.savedDocIds === this.lastSavedRef
    ) {
      return;
    }
    this.lastVisualKey = key;
    this.lastNodesRef = snapshot.mapNodes;
    this.lastSavedRef = snapshot.savedDocIds;

    const visual = computeNodeVisualState({
      nodeCount,
      docIdToNodeIndex: nodeIndex.docIdToNodeIndex,
      resultDocIds: snapshot.emphasisDocIds,
      hasSearchEmphasis: snapshot.hasSearchEmphasis,
      selectedDocId: snapshot.selectedDocId,
      hoveredDocId: snapshot.hoveredDocId,
      savedDocIds: snapshot.savedDocIds,
    });

    if (import.meta.env.DEV && visual.missingDocIds.length > 0) {
      // Not an error: the projection may simply predate these documents.
      console.warn(
        `[ThoughtMap] ${visual.missingDocIds.length} search result(s) have no node ` +
          `in the current projection`,
        visual.missingDocIds.slice(0, 5),
      );
    }

    this.scene.nodes.applyVisualState(visual);
    this.scene.requestRender();
  }

  /** Search ↔ map join diagnostics for the current results. */
  joinDiagnostics(snapshot: AppStateSnapshot) {
    return joinMetrics(
      snapshot.results.map((result) => result.doc_id),
      this.scene.nodes.nodeIndex.docIdToNodeIndex,
    );
  }

  /** Move the camera to one document. No-op when it has no node. */
  focusDocument(docId: string): boolean {
    const index = this.scene.nodes.nodeIndex.docIdToNodeIndex.get(docId);
    if (index === undefined) {
      // A result with no projected node stays fully usable in the list; there
      // is simply nowhere to fly to.
      return false;
    }

    const position = this.scene.nodes.worldPositionOf(index, this.scratchPoint);
    if (!position) {
      return false;
    }

    this.scene.camera.focusPoint(position, this.scene.nodes.worldExtent);
    this.scene.requestRender();
    return true;
  }

  /**
   * Frame the current result set.
   *
   * Only results that exist in the projection participate. Returns false when
   * none do, which is what disables the control.
   */
  fitResults(snapshot: AppStateSnapshot): boolean {
    const positions = this.resultPositions(snapshot);
    if (positions.length === 0) {
      return false;
    }

    const fitted = this.scene.camera.fitPoints(positions, this.scene.nodes.worldExtent);
    if (fitted) {
      this.scene.requestRender();
    }
    return fitted;
  }

  /** True when Fit Results has anything to frame. */
  canFitResults(snapshot: AppStateSnapshot): boolean {
    const map = this.scene.nodes.nodeIndex.docIdToNodeIndex;
    return snapshot.results.some((result) => map.has(result.doc_id));
  }

  private resultPositions(snapshot: AppStateSnapshot): Vector3[] {
    const map = this.scene.nodes.nodeIndex.docIdToNodeIndex;
    const positions: Vector3[] = [];

    for (const result of snapshot.results) {
      const index = map.get(result.doc_id);
      if (index === undefined) {
        continue;
      }
      const position = this.scene.nodes.worldPositionOf(index, new Vector3());
      if (position) {
        positions.push(position);
      }
    }

    return positions;
  }

  dispose(): void {
    this.disposed = true;
    const canvas = this.canvas;
    canvas.removeEventListener("pointerdown", this.handlePointerDown);
    canvas.removeEventListener("pointermove", this.handlePointerMove);
    canvas.removeEventListener("pointerup", this.handlePointerUp);
    canvas.removeEventListener("pointercancel", this.handlePointerCancel);
    canvas.removeEventListener("pointerleave", this.handlePointerLeave);

    if (this.hoverFrame !== 0) {
      cancelAnimationFrame(this.hoverFrame);
      this.hoverFrame = 0;
    }
  }

  // --- pointer handling ---------------------------------------------------

  private readonly handlePointerDown = (event: PointerEvent): void => {
    this.pointerId = event.pointerId;
    this.pointerType = event.pointerType || "mouse";
    this.pointerOrigin = { x: event.clientX, y: event.clientY };
    this.dragging = false;
  };

  private readonly handlePointerMove = (event: PointerEvent): void => {
    // A gesture becomes a camera drag once it travels far enough; from then on
    // the release must not select anything.
    if (this.pointerOrigin && event.pointerId === this.pointerId && !this.dragging) {
      if (exceedsDragThreshold(this.pointerOrigin, { x: event.clientX, y: event.clientY })) {
        this.dragging = true;
        this.clearHover();
      }
    }

    if (this.dragging || this.pointerType === "touch") {
      // No hover during an orbit, and no hover-follows-finger on touch.
      return;
    }

    this.queueHover(event);
  };

  private readonly handlePointerUp = (event: PointerEvent): void => {
    const wasDragging = this.dragging;
    const origin = this.pointerOrigin;

    this.pointerOrigin = null;
    this.pointerId = null;
    this.dragging = false;

    // OrbitControls owns this gesture; releasing from a drag must never select.
    if (wasDragging || !origin) {
      return;
    }

    const point = this.toCanvasPoint(event.clientX, event.clientY);
    const index = this.pick(point.x, point.y, pickRadiusForPointer(event.pointerType));

    if (index === -1) {
      // Empty space clears the selection, which is how you get back to the
      // whole map without hunting for a control.
      this.selection.clear();
      return;
    }

    const docId = this.scene.nodes.nodeIndex.nodeIndexToDocId[index];
    if (docId) {
      // Exactly the path a result-list click takes.
      this.selection.select(docId);
    }
  };

  private readonly handlePointerCancel = (): void => {
    this.pointerOrigin = null;
    this.pointerId = null;
    this.dragging = false;
    this.clearHover();
  };

  private readonly handlePointerLeave = (): void => {
    this.clearHover();
  };

  private queueHover(event: PointerEvent): void {
    this.pendingHover = this.toCanvasPoint(event.clientX, event.clientY);

    if (this.hoverFrame !== 0) {
      // A frame is already booked, and normally it will run and clear this.
      //
      // But a requested frame is not guaranteed to be delivered: the browser
      // stops servicing rAF while the page is not being painted (a hidden or
      // occluded tab). Without this escape hatch the handle stays set forever
      // and hover is dead for the rest of the session. Past the deadline,
      // drop the stale booking and schedule again.
      if (performance.now() - this.hoverRequestedAt < STALE_HOVER_FRAME_MS) {
        return;
      }
      cancelAnimationFrame(this.hoverFrame);
      this.hoverFrame = 0;
    }

    // Coalesce to one pick per frame: pointermove can fire far faster than the
    // display refreshes, and picking every event would be wasted work.
    this.hoverRequestedAt = performance.now();
    this.hoverFrame = requestAnimationFrame(() => {
      this.hoverFrame = 0;
      const pending = this.pendingHover;
      this.pendingHover = null;
      if (pending && !this.disposed) {
        this.resolveHover(pending.x, pending.y);
      }
    });
  }

  private resolveHover(x: number, y: number): void {
    const index = this.pick(x, y, pickRadiusForPointer(this.pointerType));

    if (index === -1) {
      this.clearHover();
      return;
    }

    const docId = this.scene.nodes.nodeIndex.nodeIndexToDocId[index];
    const node = this.scene.nodes.nodeIndex.nodes[index];
    if (!docId || !node) {
      this.clearHover();
      return;
    }

    this.state.setHovered(docId);

    const snapshot = this.state.getState();
    const asResult = snapshot.results.find((result) => result.doc_id === docId);

    this.callbacks.onHover({
      docId,
      title: node.title,
      author: node.author,
      source: node.source,
      similarity: asResult ? asResult.similarity : null,
      x,
      y,
    });
  }

  private clearHover(): void {
    this.pendingHover = null;
    if (this.state.getState().hoveredDocId !== null) {
      this.state.setHovered(null);
    }
    this.callbacks.onHover(null);
  }

  private pick(x: number, y: number, radiusPx: number): number {
    const count = this.scene.nodes.count;
    if (count === 0) {
      return -1;
    }

    const canvas = this.canvas;
    const width = canvas.clientWidth || canvas.width;
    const height = canvas.clientHeight || canvas.height;

    const screen = this.scene.nodes.projectToScreen(this.scene.camera.camera, width, height);
    return pickNearestNode(screen, count, x, y, radiusPx).index;
  }

  private toCanvasPoint(clientX: number, clientY: number): { x: number; y: number } {
    const rect = this.canvas.getBoundingClientRect();
    return { x: clientX - rect.left, y: clientY - rect.top };
  }
}
