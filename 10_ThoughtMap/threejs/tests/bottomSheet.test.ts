// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SearchResult } from "../src/api/types";
import { AppState } from "../src/app/AppState";
import { fromSearchResult } from "../src/app/DocumentSelectionResolver";
import { SearchScreen } from "../src/app/SearchScreen";
import {
  BottomSheet,
  PEEK_HEIGHT_PX,
  chooseSnap,
  computeSnapHeights,
  nextSnap,
  sheetModeFor,
  type SheetMode,
} from "../src/ui/BottomSheet";
import { DetailPanel } from "../src/ui/DetailPanel";

function result(docId: string): SearchResult {
  return { doc_id: docId, title: `Result ${docId}`, author: "Plato", source: "gutendex", similarity: 0.5 };
}

describe("snap heights", () => {
  it("rests at a header, half the screen, and just below the search bar", () => {
    const heights = computeSnapHeights(844, 70);
    expect(heights.peek).toBe(PEEK_HEIGHT_PX);
    expect(heights.half).toBe(422);
    expect(heights.full).toBe(844 - 70 - 8);
  });

  it("never lets half exceed full on a short screen", () => {
    const heights = computeSnapHeights(320, 200);
    expect(heights.half).toBeLessThanOrEqual(heights.full);
    expect(heights.full).toBeGreaterThanOrEqual(PEEK_HEIGHT_PX);
  });

  it("survives nonsense measurements", () => {
    const heights = computeSnapHeights(Number.NaN, -5);
    expect(Number.isFinite(heights.half)).toBe(true);
    expect(Number.isFinite(heights.full)).toBe(true);
  });
});

describe("where a released drag rests", () => {
  const heights = { peek: 112, half: 420, full: 760 };

  it("goes to the nearest stop when released slowly", () => {
    expect(chooseSnap(150, 0, heights)).toBe("peek");
    expect(chooseSnap(380, 0.1, heights)).toBe("half");
    expect(chooseSnap(700, -0.1, heights)).toBe("full");
  });

  it("follows a flick to the next stop in its direction", () => {
    expect(chooseSnap(200, 1.2, heights)).toBe("half");
    expect(chooseSnap(450, 1.2, heights)).toBe("full");
    expect(chooseSnap(400, -1.2, heights)).toBe("peek");
    expect(chooseSnap(740, -1.2, heights)).toBe("half");
  });

  it("stays within the ends", () => {
    expect(chooseSnap(780, 2, heights)).toBe("full");
    expect(chooseSnap(90, -2, heights)).toBe("peek");
  });

  it("cycles peek, half, full on handle taps", () => {
    expect(nextSnap("peek")).toBe("half");
    expect(nextSnap("half")).toBe("full");
    expect(nextSnap("full")).toBe("peek");
  });

  it("puts a sideways phone in the side layout before the upright one", () => {
    expect(sheetModeFor(() => true)).toBe("side");
    expect(sheetModeFor((q) => q.includes("max-width"))).toBe("bottom");
    expect(sheetModeFor(() => false)).toBe("none");
  });
});

describe("BottomSheet", () => {
  function make(mode: SheetMode = "bottom") {
    const root = document.createElement("div");
    const handle = document.createElement("button");
    const zone = document.createElement("div");
    const tab = document.createElement("button");
    zone.append(tab);
    root.append(handle, zone);
    document.body.append(root);
    const sheet = new BottomSheet({ root, handle, dragZones: [zone], topEdge: () => 70, mode: () => mode });
    const pointer = (target: EventTarget, type: string, y: number) =>
      target.dispatchEvent(new PointerEvent(type, { pointerId: 1, pointerType: "touch", clientY: y, bubbles: true }));
    return { root, handle, zone, tab, sheet, pointer };
  }

  afterEach(() => {
    document.body.replaceChildren();
  });

  it("sets the stop and its height on the layout root", () => {
    const { root, sheet } = make();
    expect(root.dataset["sheet"]).toBe("peek");
    expect(root.style.getPropertyValue("--tm-sheet-h")).toBe(`${PEEK_HEIGHT_PX}px`);

    sheet.setSnap("half");
    expect(root.dataset["sheet"]).toBe("half");
    expect(root.style.getPropertyValue("--tm-sheet-h")).toBe(`${sheet.snapHeights.half}px`);
    sheet.dispose();
  });

  it("cycles through the stops when the handle is tapped", () => {
    const { handle, sheet } = make();
    handle.click();
    expect(sheet.snap).toBe("half");
    handle.click();
    expect(sheet.snap).toBe("full");
    handle.click();
    expect(sheet.snap).toBe("peek");
    sheet.dispose();
  });

  it("follows a drag on the header and rests at the nearest stop", async () => {
    const { zone, sheet, pointer } = make();
    const target = sheet.snapHeights.half;
    pointer(zone, "pointerdown", 700);
    pointer(window, "pointermove", 690);
    pointer(window, "pointermove", 700 - (target - PEEK_HEIGHT_PX) - 30);
    // Held still before lifting: placed, not flung.
    await new Promise((resolve) => setTimeout(resolve, 120));
    pointer(window, "pointerup", 700 - (target - PEEK_HEIGHT_PX) - 30);
    expect(sheet.snap).toBe("half");
    sheet.dispose();
  });

  it("follows a flick past the nearest stop", () => {
    const { zone, sheet, pointer } = make();
    pointer(zone, "pointerdown", 700);
    pointer(window, "pointermove", 690);
    pointer(window, "pointermove", 640);
    pointer(window, "pointerup", 640);
    expect(sheet.snap).toBe("half");
    sheet.dispose();
  });

  it("does not treat a tap on the header as a drag", () => {
    const { zone, root, sheet, pointer } = make();
    pointer(zone, "pointerdown", 700);
    pointer(window, "pointermove", 697);
    pointer(window, "pointerup", 697);
    expect(sheet.snap).toBe("peek");
    expect(root.classList.contains("is-sheet-dragging")).toBe(false);
    sheet.dispose();
  });

  it("swallows the click a drag would otherwise deliver to a tab", () => {
    const { zone, tab, sheet, pointer } = make();
    const onTab = vi.fn();
    tab.addEventListener("click", onTab);
    pointer(zone, "pointerdown", 700);
    pointer(window, "pointermove", 600);
    pointer(window, "pointerup", 600);
    tab.click();
    expect(onTab).not.toHaveBeenCalled();
    sheet.dispose();
  });

  it("does nothing outside the phone layout", () => {
    const { root, handle, sheet } = make("none");
    handle.click();
    expect(root.style.getPropertyValue("--tm-sheet-h")).toBe("");
    expect(root.dataset["sheetMode"]).toBe("none");
    sheet.dispose();
  });
});

describe("phone layout rules", () => {
  function phone(mode: SheetMode = "bottom") {
    const mount = document.createElement("div");
    document.body.append(mount);
    const screen = new SearchScreen(mount, undefined, undefined, {
      sheetMode: () => mode,
      coarsePointer: () => true,
    });
    return { mount, screen };
  }

  afterEach(() => {
    document.body.replaceChildren();
  });

  it("opens to half when a search starts and when a document is selected", () => {
    const { screen } = phone();
    expect(screen.sheet.snap).toBe("peek");

    screen.state.startSearch();
    expect(screen.sheet.snap).toBe("half");

    screen.sheet.setSnap("peek");
    screen.state.searchSucceeded(screen.state.currentRequestId, {
      query: "q",
      results: [result("a")],
      queryParameters: null,
    });
    screen.selection.select("a");
    expect(screen.sheet.snap).toBe("half");
    screen.dispose();
  });

  it("waits out a possible second tap before opening for a map tap's selection", () => {
    vi.useFakeTimers();
    try {
      const { screen } = phone();
      screen.state.searchSucceeded(screen.state.startSearch(), {
        query: "q",
        results: [result("a")],
        queryParameters: null,
      });
      screen.sheet.setSnap("peek");

      screen.holdLayoutForTap();
      screen.selection.select("a");
      expect(screen.sheet.snap).toBe("peek");

      vi.advanceTimersByTime(300);
      expect(screen.sheet.snap).toBe("half");
      screen.dispose();
    } finally {
      vi.useRealTimers();
    }
  });

  it("drops the opening if the tap turns into exploring", () => {
    vi.useFakeTimers();
    try {
      const { screen } = phone();
      screen.state.searchSucceeded(screen.state.startSearch(), {
        query: "q",
        results: [result("a")],
        queryParameters: null,
      });
      screen.sheet.setSnap("peek");

      screen.holdLayoutForTap();
      screen.selection.select("a");
      screen.onMapGesture();
      vi.advanceTimersByTime(300);
      expect(screen.sheet.snap).toBe("peek");
      screen.dispose();
    } finally {
      vi.useRealTimers();
    }
  });

  it("gives the map the screen only when a map gesture has begun", () => {
    const { screen } = phone();
    screen.sheet.setSnap("full");
    screen.onMapGesture();
    expect(screen.sheet.snap).toBe("peek");
    screen.dispose();
  });

  it("leaves tablet and desktop layouts alone", () => {
    const { screen } = phone("none");
    screen.sheet.setSnap("half");
    screen.onMapGesture();
    expect(screen.sheet.snap).toBe("half");
    screen.dispose();
  });

  it("makes room for the keyboard, and closes it after searching", () => {
    const { mount, screen } = phone();
    const input = mount.querySelector<HTMLInputElement>('input[type="search"]')!;
    // Not focused on load on a phone: the keyboard would cover the map.
    expect(document.activeElement).not.toBe(input);

    screen.sheet.setSnap("half");
    input.focus();
    expect(screen.sheet.snap).toBe("peek");

    input.form!.dispatchEvent(new Event("submit", { cancelable: true }));
    expect(document.activeElement).not.toBe(input);
    screen.dispose();
  });

  it("steps through the results, starting at the first from outside them", () => {
    const { screen } = phone();
    screen.state.searchSucceeded(screen.state.startSearch(), {
      query: "q",
      results: [result("a"), result("b"), result("c")],
      queryParameters: null,
    });

    screen.stepResult(1);
    expect(screen.state.getState().selectedDocId).toBe("a");
    screen.stepResult(1);
    expect(screen.state.getState().selectedDocId).toBe("b");
    screen.stepResult(-1);
    expect(screen.state.getState().selectedDocId).toBe("a");
    screen.stepResult(-1);
    expect(screen.state.getState().selectedDocId).toBe("a");
    screen.dispose();
  });

  it("shows a map notice, and a lasting one while the 3D view is paused", () => {
    const { mount, screen } = phone();
    const notice = mount.querySelector<HTMLElement>(".tm-map-notice")!;
    expect(notice.hidden).toBe(true);

    screen.showMapNotice("Zoomed in");
    expect(notice.hidden).toBe(false);
    expect(notice.textContent).toBe("Zoomed in");

    screen.setMapSuspended(true);
    expect(notice.textContent).toContain("paused");
    expect(mount.querySelector(".tm-layout")!.classList.contains("is-map-suspended")).toBe(true);

    screen.setMapSuspended(false);
    expect(notice.hidden).toBe(true);
    screen.dispose();
  });
});

describe("document stepper", () => {
  it("says where the document sits among the results and limits the ends", () => {
    const panel = new DetailPanel();
    const state = new AppState();
    state.searchSucceeded(state.startSearch(), {
      query: "q",
      results: [result("a"), result("b"), result("c")],
      queryParameters: null,
    });

    panel.render(state.getState(), fromSearchResult(result("b")));
    const position = panel.element.querySelector(".tm-step-position")!;
    const prev = panel.element.querySelector<HTMLButtonElement>(".tm-step.is-prev")!;
    const next = panel.element.querySelector<HTMLButtonElement>(".tm-step.is-next")!;
    expect(position.textContent).toBe("2 / 3");
    expect(prev.disabled).toBe(false);
    expect(next.disabled).toBe(false);

    panel.render(state.getState(), fromSearchResult(result("c")));
    expect(next.disabled).toBe(true);

    panel.render(state.getState(), fromSearchResult(result("zzz")));
    expect(position.textContent).toBe("– / 3");
    expect(prev.disabled).toBe(true);
    expect(next.disabled).toBe(false);
  });

  it("reports which way to step", () => {
    const onStep = vi.fn();
    const panel = new DetailPanel({ onStep });
    const state = new AppState();
    state.searchSucceeded(state.startSearch(), {
      query: "q",
      results: [result("a"), result("b")],
      queryParameters: null,
    });
    panel.render(state.getState(), fromSearchResult(result("a")));
    panel.element.querySelector<HTMLButtonElement>(".tm-step.is-next")!.click();
    expect(onStep).toHaveBeenCalledWith(1);
  });
});
