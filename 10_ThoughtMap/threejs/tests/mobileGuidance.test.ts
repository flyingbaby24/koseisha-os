// @vitest-environment happy-dom
/**
 * Guidance on a touch screen. Findings from docs/mobile-ux-audit/README.md:
 *
 *   M-16  the gestures are explained once, legibly, on a touch screen
 *   M-17  coming back to the list lands on the document just read
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { SearchResult } from "../src/api/types";
import { SearchScreen } from "../src/app/SearchScreen";

function result(docId: string): SearchResult {
  return { doc_id: docId, title: `Result ${docId}`, author: "Plato", source: "gutendex", similarity: 0.5 };
}

function screenFor(coarse: boolean) {
  const mount = document.createElement("div");
  document.body.append(mount);
  const screen = new SearchScreen(mount, undefined, undefined, {
    sheetMode: () => (coarse ? "bottom" : "none"),
    coarsePointer: () => coarse,
  });
  const card = mount.querySelector<HTMLElement>(".tm-gesture-help")!;
  const mapReady = () => screen.state.mapLoaded([], {} as never);
  return { mount, screen, card, mapReady };
}

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
  document.body.replaceChildren();
});

describe("M-16: the gestures are explained once on a touch screen", () => {
  it("appears once the map is ready, not before", () => {
    const { screen, card, mapReady } = screenFor(true);
    expect(card.hidden).toBe(true);

    mapReady();
    expect(card.hidden).toBe(false);
    expect(card.textContent).toContain("Double-tap");
    screen.dispose();
  });

  it("is not shown with a mouse, which has the hint line instead", () => {
    const { screen, card, mapReady } = screenFor(false);
    mapReady();
    expect(card.hidden).toBe(true);
    screen.dispose();
  });

  it("goes away with Got it, and stays away next visit", () => {
    const first = screenFor(true);
    first.mapReady();
    first.card.querySelector<HTMLButtonElement>("button")!.click();
    expect(first.card.hidden).toBe(true);
    first.screen.dispose();

    const next = screenFor(true);
    next.mapReady();
    expect(next.card.hidden).toBe(true);
    next.screen.dispose();
  });

  it("gets out of the way once someone starts moving the map", () => {
    const first = screenFor(true);
    first.mapReady();
    first.screen.onMapGesture();
    expect(first.card.hidden).toBe(true);
    first.screen.dispose();

    const next = screenFor(true);
    next.mapReady();
    expect(next.card.hidden).toBe(true);
    next.screen.dispose();
  });

  it("still works where the browser refuses storage", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("SecurityError");
    });
    const { screen, card, mapReady } = screenFor(true);
    mapReady();
    expect(card.hidden).toBe(false);
    expect(() => card.querySelector<HTMLButtonElement>("button")!.click()).not.toThrow();
    expect(card.hidden).toBe(true);
    screen.dispose();
  });

  it("is not shown when the map failed", () => {
    const { screen, card } = screenFor(true);
    screen.state.mapFailed("WebGL unavailable");
    expect(card.hidden).toBe(true);
    screen.dispose();
  });
});

describe("M-17: coming back to the list lands on the document just read", () => {
  it("scrolls the selected row into view when Back returns to the list", () => {
    const { mount, screen } = screenFor(true);
    screen.state.searchSucceeded(screen.state.startSearch(), {
      query: "q",
      results: ["a", "b", "c", "d", "e"].map(result),
      queryParameters: null,
    });
    screen.selection.select("b");
    screen.stepResult(1);
    screen.stepResult(1);
    expect(screen.state.getState().selectedDocId).toBe("d");

    const row = mount.querySelector<HTMLElement>('.tm-result[data-doc-id="d"]')!;
    const reveal = vi.spyOn(row, "scrollIntoView");
    mount.querySelector<HTMLButtonElement>('[aria-label="Back to the list"]')!.click();

    expect(mount.querySelector(".tm-layout")!.getAttribute("data-view")).toBe("list");
    expect(reveal).toHaveBeenCalledWith({ block: "nearest" });
    screen.dispose();
  });

  it("does nothing when no result is selected", () => {
    const { mount, screen } = screenFor(true);
    screen.state.searchSucceeded(screen.state.startSearch(), {
      query: "q",
      results: ["a", "b"].map(result),
      queryParameters: null,
    });
    const rows = [...mount.querySelectorAll<HTMLElement>(".tm-result")];
    const spies = rows.map((row) => vi.spyOn(row, "scrollIntoView"));
    mount.querySelector<HTMLButtonElement>('[aria-label="Back to the list"]')!.click();
    for (const spy of spies) {
      expect(spy).not.toHaveBeenCalled();
    }
    screen.dispose();
  });
});
