/**
 * The phone layout's panel: a sheet over the bottom of the thought space.
 *
 * Three resting heights — peek (a header's worth), half, full — and a drag
 * between them from the handle or the panel's header row. The sheet only sets
 * a CSS custom property and a data attribute on the layout root; CSS turns
 * those into the grid row the map window sits above, and the scene's existing
 * safe-area measurement re-centres the camera on whatever map stays visible.
 *
 * Nothing here knows about search, selection or the map. SearchScreen decides
 * *when* to move the sheet; this decides *how*.
 */

export type SheetMode = "bottom" | "side" | "none";
export type SheetSnap = "peek" | "half" | "full";

/** Phones held sideways: the panel moves to the right edge instead. */
export const SIDE_SHEET_QUERY = "(max-height: 500px) and (orientation: landscape)";
/** Phones held upright. Must match the bottom-sheet rules in main.css. */
export const BOTTOM_SHEET_QUERY = "(max-width: 720px)";

/** Handle plus one header row (tabs, or Back with previous / next). */
export const PEEK_HEIGHT_PX = 112;
/** Vertical travel before a press on the handle or header becomes a drag. */
const DRAG_START_PX = 6;
/** Flick speed (px/ms) above which the sheet goes to the next stop. */
const FLING_SPEED = 0.45;

export interface SnapHeights {
  peek: number;
  half: number;
  full: number;
}

const ORDER: readonly SheetSnap[] = ["peek", "half", "full"];

/**
 * Resting heights for a viewport. `topEdge` is where the search bar ends; the
 * full sheet stops just below it so the query stays visible.
 */
export function computeSnapHeights(viewportHeight: number, topEdge: number): SnapHeights {
  const vh = Number.isFinite(viewportHeight) && viewportHeight > 0 ? viewportHeight : 800;
  const top = Number.isFinite(topEdge) && topEdge > 0 ? topEdge : 0;
  const full = Math.max(PEEK_HEIGHT_PX, Math.round(vh - top - 8));
  const half = Math.min(full, Math.max(PEEK_HEIGHT_PX + 40, Math.round(vh * 0.5)));
  return { peek: PEEK_HEIGHT_PX, half, full };
}

/**
 * Where a released drag comes to rest.
 *
 * A flick goes to the next stop in its direction; a slow release goes to the
 * nearest stop. `velocity` is px/ms, positive when the sheet is growing.
 */
export function chooseSnap(height: number, velocity: number, heights: SnapHeights): SheetSnap {
  if (Math.abs(velocity) > FLING_SPEED) {
    if (velocity > 0) {
      return ORDER.find((snap) => heights[snap] > height + 1) ?? "full";
    }
    return [...ORDER].reverse().find((snap) => heights[snap] < height - 1) ?? "peek";
  }
  let best: SheetSnap = "peek";
  for (const snap of ORDER) {
    if (Math.abs(heights[snap] - height) < Math.abs(heights[best] - height)) {
      best = snap;
    }
  }
  return best;
}

/** The next stop when the handle is tapped: peek → half → full → peek. */
export function nextSnap(current: SheetSnap): SheetSnap {
  return ORDER[(ORDER.indexOf(current) + 1) % ORDER.length]!;
}

export function sheetModeFor(matches: (query: string) => boolean): SheetMode {
  if (matches(SIDE_SHEET_QUERY)) {
    return "side";
  }
  if (matches(BOTTOM_SHEET_QUERY)) {
    return "bottom";
  }
  return "none";
}

export interface BottomSheetOptions {
  /** Layout root: receives `data-sheet` and `--tm-sheet-h`. */
  root: HTMLElement;
  handle: HTMLButtonElement;
  /** Header rows that drag the sheet too (tab bar, document header). */
  dragZones: readonly HTMLElement[];
  /** Bottom edge of the search bar, in CSS px. */
  topEdge: () => number;
  /** Which layout applies. Defaults to the media queries above. */
  mode?: () => SheetMode;
  initial?: SheetSnap;
}

const HANDLE_LABEL: Record<SheetSnap, string> = {
  peek: "Show more of the panel",
  half: "Expand the panel",
  full: "Collapse the panel",
};

interface DragState {
  pointerId: number;
  target: HTMLElement;
  startY: number;
  startHeight: number;
  height: number;
  lastY: number;
  lastTime: number;
  velocity: number;
  active: boolean;
}

export class BottomSheet {
  private current: SheetSnap;
  private heights: SnapHeights = { peek: PEEK_HEIGHT_PX, half: 400, full: 700 };
  private drag: DragState | null = null;
  /** Swallow the click a drag would otherwise deliver to a tab or button. */
  private suppressClickUntil = 0;
  private readonly listeners = new Set<(snap: SheetSnap) => void>();
  private readonly queries: MediaQueryList[] = [];
  private readonly mode: () => SheetMode;

  constructor(private readonly options: BottomSheetOptions) {
    this.current = options.initial ?? "peek";
    this.mode = options.mode ?? (() => sheetModeFor(mediaMatches));

    const { handle } = options;
    handle.addEventListener("click", this.handleClick);
    handle.addEventListener("keydown", this.handleKeydown);
    for (const zone of [handle, ...options.dragZones]) {
      zone.addEventListener("pointerdown", this.handlePointerDown);
      zone.addEventListener("click", this.swallowClickAfterDrag, true);
    }
    window.addEventListener("pointermove", this.handlePointerMove);
    window.addEventListener("pointerup", this.handlePointerUp);
    window.addEventListener("pointercancel", this.handlePointerUp);
    window.addEventListener("resize", this.relayout);
    for (const query of [SIDE_SHEET_QUERY, BOTTOM_SHEET_QUERY]) {
      const list = matchMediaSafe(query);
      if (list) {
        list.addEventListener("change", this.relayout);
        this.queries.push(list);
      }
    }
    this.relayout();
  }

  get snap(): SheetSnap {
    return this.current;
  }

  get layoutMode(): SheetMode {
    return this.mode();
  }

  get snapHeights(): SnapHeights {
    return this.heights;
  }

  onChange(listener: (snap: SheetSnap) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /** Move to a resting height. A no-op outside the bottom-sheet layout. */
  setSnap(snap: SheetSnap): void {
    const changed = snap !== this.current;
    this.current = snap;
    this.apply();
    if (changed) {
      for (const listener of this.listeners) {
        listener(snap);
      }
    }
  }

  /** Recompute stops for the current viewport and re-apply the current one. */
  readonly relayout = (): void => {
    this.heights = computeSnapHeights(window.innerHeight, this.options.topEdge());
    this.apply();
  };

  dispose(): void {
    const { handle } = this.options;
    handle.removeEventListener("click", this.handleClick);
    handle.removeEventListener("keydown", this.handleKeydown);
    for (const zone of [handle, ...this.options.dragZones]) {
      zone.removeEventListener("pointerdown", this.handlePointerDown);
      zone.removeEventListener("click", this.swallowClickAfterDrag, true);
    }
    window.removeEventListener("pointermove", this.handlePointerMove);
    window.removeEventListener("pointerup", this.handlePointerUp);
    window.removeEventListener("pointercancel", this.handlePointerUp);
    window.removeEventListener("resize", this.relayout);
    for (const list of this.queries) {
      list.removeEventListener("change", this.relayout);
    }
    this.listeners.clear();
  }

  private apply(height?: number): void {
    const { root, handle } = this.options;
    const mode = this.mode();
    root.dataset["sheetMode"] = mode;
    root.dataset["sheet"] = this.current;
    if (mode !== "bottom") {
      root.style.removeProperty("--tm-sheet-h");
      return;
    }
    const value = height ?? this.heights[this.current];
    root.style.setProperty("--tm-sheet-h", `${Math.round(value)}px`);
    handle.setAttribute("aria-label", HANDLE_LABEL[this.current]);
    handle.title = HANDLE_LABEL[this.current];
  }

  private readonly handleClick = (): void => {
    if (performance.now() < this.suppressClickUntil || this.mode() !== "bottom") {
      return;
    }
    this.setSnap(nextSnap(this.current));
  };

  private readonly handleKeydown = (event: KeyboardEvent): void => {
    if (this.mode() !== "bottom") {
      return;
    }
    const index = ORDER.indexOf(this.current);
    if (event.key === "ArrowUp" && index < ORDER.length - 1) {
      event.preventDefault();
      this.setSnap(ORDER[index + 1]!);
    } else if (event.key === "ArrowDown" && index > 0) {
      event.preventDefault();
      this.setSnap(ORDER[index - 1]!);
    }
  };

  private readonly handlePointerDown = (event: PointerEvent): void => {
    if (this.mode() !== "bottom" || this.drag || (event.pointerType === "mouse" && event.button !== 0)) {
      return;
    }
    const height = this.heights[this.current];
    this.drag = {
      pointerId: event.pointerId,
      target: event.currentTarget as HTMLElement,
      startY: event.clientY,
      startHeight: height,
      height,
      lastY: event.clientY,
      lastTime: event.timeStamp,
      velocity: 0,
      active: false,
    };
  };

  private readonly handlePointerMove = (event: PointerEvent): void => {
    const drag = this.drag;
    if (!drag || event.pointerId !== drag.pointerId) {
      return;
    }
    const grown = drag.startY - event.clientY;
    if (!drag.active) {
      if (Math.abs(grown) < DRAG_START_PX) {
        return;
      }
      // Only now, once this is clearly a drag, does the layout start moving.
      drag.active = true;
      this.options.root.classList.add("is-sheet-dragging");
      try {
        drag.target.setPointerCapture(event.pointerId);
      } catch {
        // Not all environments support capture; window listeners still track it.
      }
    }
    const dt = Math.max(1, event.timeStamp - drag.lastTime);
    const instant = (drag.lastY - event.clientY) / dt;
    drag.velocity = drag.velocity * 0.6 + instant * 0.4;
    drag.lastY = event.clientY;
    drag.lastTime = event.timeStamp;
    drag.height = Math.min(this.heights.full, Math.max(this.heights.peek - 24, drag.startHeight + grown));
    this.apply(drag.height);
  };

  private readonly handlePointerUp = (event: PointerEvent): void => {
    const drag = this.drag;
    if (!drag || event.pointerId !== drag.pointerId) {
      return;
    }
    this.drag = null;
    if (!drag.active) {
      return;
    }
    this.options.root.classList.remove("is-sheet-dragging");
    this.suppressClickUntil = performance.now() + 350;
    // A finger that held still before lifting placed the sheet; it did not fling it.
    const velocity = event.timeStamp - drag.lastTime > 100 ? 0 : drag.velocity;
    this.setSnap(chooseSnap(drag.height, velocity, this.heights));
    // setSnap is a no-op for the attribute when the stop did not change, but
    // the height was moved by hand, so put it back on its stop either way.
    this.apply();
  };

  private readonly swallowClickAfterDrag = (event: Event): void => {
    if (performance.now() < this.suppressClickUntil) {
      event.stopPropagation();
      event.preventDefault();
    }
  };
}

function matchMediaSafe(query: string): MediaQueryList | null {
  try {
    return typeof globalThis.matchMedia === "function" ? globalThis.matchMedia(query) : null;
  } catch {
    return null;
  }
}

function mediaMatches(query: string): boolean {
  return matchMediaSafe(query)?.matches ?? false;
}

/** Whether the primary pointer is a finger (no hover, imprecise). */
export function isCoarsePrimaryPointer(): boolean {
  return mediaMatches("(pointer: coarse)");
}
