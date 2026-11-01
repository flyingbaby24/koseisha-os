import { Vector3 } from "three";

import type { ThoughtMapScene } from "../scene/ThoughtMapScene";
import { computeFocusDistance } from "../scene/cameraFraming";
import { computeNodeVisualState, joinMetrics } from "../scene/nodeVisualState";
import {
  DRAG_THRESHOLD_PX,
  countWithinRadius,
  exceedsDragThreshold,
  pickNearestNode,
  pickRadiusForPointer,
  type PointerOrigin,
} from "../scene/picking";
import type { AppState, AppStateSnapshot } from "./AppState";
import type { SelectionController } from "./SelectionController";
import { DOUBLE_TAP_MS } from "./tapTiming";

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
  /**
   * A gesture on the map has become a drag, pinch or pan — never fired for a
   * tap, and never on touch-down, so a layout that makes room for the map
   * cannot move under a finger that is only tapping.
   */
  onGestureStart?: () => void;
  /** A short message for the reader, shown over the map. */
  onNotice?: (text: string) => void;
  /**
   * A finger tapped the map (touch and pen only), reported before the tap
   * selects anything. A second tap may follow within DOUBLE_TAP_MS, so the
   * layout must hold still until then: a panel that moved after the first tap
   * would put a different control under the second.
   */
  onTap?: () => void;
}

/**
 * A finger tap covering at least this many documents is too crowded to pick
 * one meaningfully; zoomed out, the map zooms toward it instead.
 */
export const DENSE_TAP_MIN = 6;
/** "Zoomed out": farther than this many single-document focus distances. */
const DENSE_TAP_ZOOMED_OUT = 1.6;

export const DENSE_TAP_NOTICE =
  "Many documents overlap here, so the map zoomed in. Tap again to choose one.";

/**
 * How long to trust a booked animation frame before assuming it will never
 * arrive. Comfortably longer than a frame at any real refresh rate, short
 * enough that hover recovers immediately when painting resumes.
 */
const STALE_HOVER_FRAME_MS = 250;

/** Finger and stylus: imprecise contact, so taps get the forgiving rules. */
function isCoarsePointer(pointerType: string): boolean {
  return pointerType === "touch" || pointerType === "pen";
}

/** Touch slop: Android uses ~8 dp; a finger tap that wobbles less is still a tap. */
const TOUCH_DRAG_THRESHOLD_PX = 10;

/** Double tap: the second press this close to the first (a fingertip's width). */
export const DOUBLE_TAP_SLOP_PX = 40;
/** How far a double tap zooms: to half the distance, as map software does. */
export const DOUBLE_TAP_ZOOM = 0.5;

/** A finished single tap that a second one could turn into a double tap. */
interface LastTap {
  x: number;
  y: number;
  time: number;
  /** The node the tap selected, or -1 when it landed on empty space. */
  index: number;
}

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

  /** Every pointer currently down, by pointerId, with where it went down. */
  private readonly pointers = new Map<number, PointerOrigin>();
  private pointerType = "mouse";
  /** Any pointer in the current gesture travelled past the slop. */
  private dragging = false;
  /** More than one pointer took part in the current gesture (pinch / pan). */
  private multiTouch = false;
  /** Node under the first pointer when it went down, for a tap to select. */
  private downPick = -1;
  /** The first press of this gesture stopped a camera glide (touch only). */
  private stoppedGlide = false;
  /** Documents under the first pointer at press, capped at DENSE_TAP_MIN. */
  private downCrowd = 0;
  /** onGestureStart has fired for the current gesture. */
  private gestureAnnounced = false;
  /** The previous finger tap, while a second could still make it a double. */
  private lastTap: LastTap | null = null;
  /** The press in progress is the second of a double tap, if it stays a tap. */
  private doubleTapPending = false;
  /** Where the first finger of the current gesture went down, canvas pixels. */
  private downPoint = { x: 0, y: 0 };

  /** Hover picking is deferred to a frame so a fast drag cannot flood it. */
  private hoverFrame = 0;
  private hoverRequestedAt = 0;
  private pendingHover: { x: number; y: number } | null = null;

  private lastVisualKey = "";
  private lastNodesRef: unknown = null;
  private lastSavedRef: unknown = null;
  /** The result list last seen, to recognise a fresh search. */
  private lastResultsRef: unknown = null;
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
    // Zooming moves the points out from under a still pointer; a tooltip left
    // behind would describe a node that is no longer there.
    canvas.addEventListener("wheel", this.handleWheel, { passive: true });
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

    this.frameFreshResults(snapshot);

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

  /**
   * Show where a new search landed — when the reader is not looking at
   * anything in particular.
   *
   * From the whole-map view a result set that sits close together collapses
   * into a single small mark, and the list's "10 results" has no visible
   * counterpart in the space. So a fresh, non-empty result set is framed,
   * exactly as Fit Results would frame it. With a document selected the
   * camera stays put: selection survives a search, and pulling the view away
   * from what someone is reading would be the surprise. Reduced motion makes
   * the move instant, like every other camera move.
   */
  private frameFreshResults(snapshot: AppStateSnapshot): void {
    if (snapshot.results === this.lastResultsRef) {
      return;
    }
    this.lastResultsRef = snapshot.results;
    if (
      snapshot.status === "success" &&
      snapshot.results.length > 0 &&
      snapshot.selectedDocId === null
    ) {
      this.fitResults(snapshot);
    }
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

    // A glide rather than a cut, so the reader sees where the document is
    // relative to where they were looking.
    this.scene.camera.focusPoint(position, this.scene.nodes.worldExtent, undefined, {
      animate: true,
    });
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

    const fitted = this.scene.camera.fitPoints(
      positions,
      this.scene.nodes.worldExtent,
      undefined,
      { animate: true },
    );
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
    canvas.removeEventListener("wheel", this.handleWheel);

    if (this.hoverFrame !== 0) {
      cancelAnimationFrame(this.hoverFrame);
      this.hoverFrame = 0;
    }
  }

  // --- pointer handling ---------------------------------------------------

  private readonly handlePointerDown = (event: PointerEvent): void => {
    if (this.pointers.size === 0) {
      this.dragging = false;
      this.multiTouch = false;
      this.gestureAnnounced = false;
    }
    this.pointerType = event.pointerType || "mouse";
    this.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (this.pointers.size === 1) {
      // What the finger landed on. OrbitControls starts rotating on the first
      // move, so by release a wobbling finger can sit over a neighbour.
      const point = this.toCanvasPoint(event.clientX, event.clientY);
      this.downPoint = point;
      const hit = this.pickAt(point.x, point.y, pickRadiusForPointer(this.pointerType));
      this.downPick = hit.index;
      this.downCrowd = hit.crowd;
      // A finger aimed at a node that was still gliding lands where the node
      // used to be. On touch, the press that stops a glide only stops it.
      const interrupted = this.scene.camera.consumeInterruptedGlide();
      const coarse = isCoarsePointer(this.pointerType);
      this.stoppedGlide = interrupted && coarse;
      this.doubleTapPending = coarse && this.followsLastTap(point, performance.now());
      if (!this.doubleTapPending) {
        this.lastTap = null;
      }
      if (coarse && !this.doubleTapPending && !this.stoppedGlide && !this.tapWouldAssist()) {
        this.showPressed(this.downPick);
      }
    }
    if (this.pointers.size > 1) {
      // A second finger makes this a pinch or a pan: it can no longer end as a tap.
      this.multiTouch = true;
      this.lastTap = null;
      this.clearHover();
      this.announceGesture();
    }
  };

  /** Whether a press here and now is the second half of a double tap. */
  private followsLastTap(point: { x: number; y: number }, now: number): boolean {
    const last = this.lastTap;
    return (
      last !== null &&
      now - last.time <= DOUBLE_TAP_MS &&
      Math.hypot(point.x - last.x, point.y - last.y) <= DOUBLE_TAP_SLOP_PX
    );
  }

  /** A finger tap here would zoom toward a crowd rather than select. */
  private tapWouldAssist(): boolean {
    return this.downPick !== -1 && this.downCrowd >= DENSE_TAP_MIN && this.isZoomedOut();
  }

  /**
   * Light the node under a finger the moment it touches down.
   *
   * A finger hides what it presses, and selection waits for the release, so
   * without this nothing answers until the finger lifts. It is the hover
   * state, without the tooltip a fingertip would cover; a drag, a second
   * finger or the release clears it like any hover.
   */
  private showPressed(index: number): void {
    if (index === -1) {
      return;
    }
    const docId = this.scene.nodes.nodeIndex.nodeIndexToDocId[index];
    if (docId) {
      this.state.setHovered(docId);
    }
  }

  private announceGesture(): void {
    if (!this.gestureAnnounced) {
      this.gestureAnnounced = true;
      this.callbacks.onGestureStart?.();
    }
  }

  private readonly handlePointerMove = (event: PointerEvent): void => {
    // A gesture becomes a camera drag once it travels far enough; from then on
    // the release must not select anything.
    const origin = this.pointers.get(event.pointerId);
    if (origin && !this.dragging) {
      // A finger wobbles more than a mouse; give touch a wider slop.
      const slop = event.pointerType === "touch" ? TOUCH_DRAG_THRESHOLD_PX : DRAG_THRESHOLD_PX;
      if (exceedsDragThreshold(origin, { x: event.clientX, y: event.clientY }, slop)) {
        this.dragging = true;
        this.clearHover();
        this.announceGesture();
      }
    }

    if (this.dragging || this.pointerType === "touch") {
      // No hover during an orbit, and no hover-follows-finger on touch.
      return;
    }

    this.queueHover(event);
  };

  private readonly handlePointerUp = (event: PointerEvent): void => {
    // Match the release to its own pointer; an unknown pointer is not ours.
    if (!this.pointers.delete(event.pointerId)) {
      return;
    }
    const wasTap = !this.dragging && !this.multiTouch;
    if (this.pointers.size === 0) {
      this.dragging = false;
      this.multiTouch = false;
    }

    // OrbitControls owns drags and multi-finger gestures; releasing from one
    // must never select.
    if (!wasTap) {
      this.lastTap = null;
      this.doubleTapPending = false;
      return;
    }

    const index = this.downPick;
    const coarse = isCoarsePointer(this.pointerType);
    if (coarse) {
      this.callbacks.onTap?.();
    }

    // A click either selects (and the camera glides the node to the centre)
    // or clears. Either way the point under a still pointer is about to move,
    // so the tooltip goes now and returns with the next pointer move.
    this.clearHover();

    // Checked before the glide rule: the first tap of a double tap on a
    // document starts a glide, and the second press is what stops it.
    if (this.doubleTapPending) {
      const first = this.lastTap;
      this.doubleTapPending = false;
      // A third tap starts afresh rather than zooming again.
      this.lastTap = null;
      this.zoomForDoubleTap(first?.index ?? -1);
      return;
    }

    if (this.stoppedGlide) {
      return;
    }

    // Zoomed out, a fingertip covers dozens of documents (24,421 at the
    // centre of a phone's whole-map view). Picking one would be arbitrary, so
    // the tap zooms toward them instead; the next tap can choose.
    if (coarse && this.tapWouldAssist()) {
      this.zoomToward(index);
      this.callbacks.onNotice?.(DENSE_TAP_NOTICE);
      return;
    }

    // Only a tap that selected or did nothing can begin a double tap: one
    // that stopped a glide or zoomed toward a crowd already answered.
    if (coarse) {
      this.lastTap = { ...this.downPoint, time: performance.now(), index };
    }

    if (index === -1) {
      // With a mouse, empty space clears the selection: it is how you get back
      // to the whole map without hunting for a control, and a mouse rarely
      // misses by accident. A finger often does — and on a phone, clearing
      // also takes away the document being read — so touch leaves it alone.
      // Tapping another document replaces it; Back returns to the list.
      if (!isCoarsePointer(this.pointerType)) {
        this.selection.clear();
      }
      return;
    }

    const docId = this.scene.nodes.nodeIndex.nodeIndexToDocId[index];
    if (docId) {
      // Exactly the path a result-list click takes.
      this.selection.select(docId);
    }
  };

  private readonly handleWheel = (): void => {
    if (this.hoverFrame !== 0) {
      cancelAnimationFrame(this.hoverFrame);
      this.hoverFrame = 0;
    }
    this.clearHover();
  };

  private readonly handlePointerCancel = (event: PointerEvent): void => {
    this.pointers.delete(event.pointerId);
    if (this.pointers.size === 0) {
      this.dragging = false;
      this.multiTouch = false;
    }
    this.lastTap = null;
    this.doubleTapPending = false;
    this.clearHover();
  };

  /**
   * The second tap of a double tap: zoom in to half the distance.
   *
   * After a tap that selected a document, that means closer to the document —
   * finishing, nearer, the glide the second press interrupted. Anywhere else
   * the point under the finger stays under it while the map grows around it.
   */
  private zoomForDoubleTap(firstIndex: number): void {
    const camera = this.scene.camera;
    const extent = this.scene.nodes.worldExtent;
    if (!(extent > 0)) {
      return;
    }

    const node = firstIndex === -1 ? null : this.scene.nodes.worldPositionOf(firstIndex, this.scratchPoint);
    if (node) {
      const base = Math.min(camera.focusDistance, computeFocusDistance(extent));
      camera.focusPoint(node, extent, (base * DOUBLE_TAP_ZOOM) / extent, { animate: true });
      this.scene.requestRender();
      return;
    }

    const canvas = this.canvas;
    const width = canvas.clientWidth || canvas.width;
    const height = canvas.clientHeight || canvas.height;
    const point = camera.pointOnFocusPlane(
      (this.downPoint.x / width) * 2 - 1,
      1 - (this.downPoint.y / height) * 2,
      this.scratchPoint,
    );
    if (point) {
      camera.zoomAbout(point, DOUBLE_TAP_ZOOM, extent, { animate: true });
      this.scene.requestRender();
    }
  }

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

  private isZoomedOut(): boolean {
    const single = computeFocusDistance(this.scene.nodes.worldExtent);
    return this.scene.camera.focusDistance > single * DENSE_TAP_ZOOMED_OUT;
  }

  /** Glide toward a node, a third of the way in — never past focus distance. */
  private zoomToward(index: number): void {
    const position = this.scene.nodes.worldPositionOf(index, this.scratchPoint);
    const extent = this.scene.nodes.worldExtent;
    if (!position || !(extent > 0)) {
      return;
    }
    const single = computeFocusDistance(extent);
    const distance = Math.max(single, this.scene.camera.focusDistance / 3);
    this.scene.camera.focusPoint(position, extent, distance / extent, { animate: true });
    this.scene.requestRender();
  }

  /** The nearest node within the radius, and how crowded that spot is. */
  private pickAt(x: number, y: number, radiusPx: number): { index: number; crowd: number } {
    const count = this.scene.nodes.count;
    if (count === 0) {
      return { index: -1, crowd: 0 };
    }
    const canvas = this.canvas;
    const width = canvas.clientWidth || canvas.width;
    const height = canvas.clientHeight || canvas.height;
    const screen = this.scene.nodes.projectToScreen(this.scene.camera.camera, width, height);
    return {
      index: pickNearestNode(screen, count, x, y, radiusPx).index,
      crowd: countWithinRadius(screen, count, x, y, radiusPx, DENSE_TAP_MIN),
    };
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
