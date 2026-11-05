// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ParameterScore, SearchResult } from "../src/api/types";
import { AppState } from "../src/app/AppState";
import { fromMapNode, fromSearchResult } from "../src/app/DocumentSelectionResolver";
import { SelectionController } from "../src/app/SelectionController";
import { DetailPanel } from "../src/ui/DetailPanel";
import { ParameterList } from "../src/ui/ParameterList";
import { ResultPanel } from "../src/ui/ResultPanel";

function result(overrides: Partial<SearchResult> & { doc_id: string }): SearchResult {
  return {
    title: `Title ${overrides.doc_id}`,
    author: "Plato",
    source: "gutendex",
    similarity: 0.5,
    ...overrides,
  };
}

function stateWith(results: SearchResult[], queryParameters: ParameterScore[] | null = null): AppState {
  const state = new AppState();
  const id = state.startSearch();
  state.searchSucceeded(id, { query: "Plato", results, queryParameters });
  return state;
}

function rowTexts(panel: ResultPanel): string[] {
  return Array.from(panel.element.querySelectorAll(".tm-result-title")).map(
    (node) => node.textContent ?? "",
  );
}

describe("ResultPanel", () => {
  let onSelect: ReturnType<typeof vi.fn<(docId: string) => void>>;
  let panel: ResultPanel;

  beforeEach(() => {
    onSelect = vi.fn<(docId: string) => void>();
    panel = new ResultPanel({ onSelect });
  });

  it("shows a prompt before any search", () => {
    panel.render(new AppState().getState());
    expect(panel.element.querySelector(".tm-note")?.textContent).toContain("Enter a query");
  });

  it("shows a loading note while searching", () => {
    const state = new AppState();
    state.startSearch();
    panel.render(state.getState());
    expect(panel.element.querySelector(".tm-note")?.textContent).toContain("Searching");
  });

  it("maps each result to title, author, source and similarity", () => {
    const state = stateWith([
      result({ doc_id: "a", title: "The Republic", author: "Plato", source: "gutendex", similarity: 0.736 }),
    ]);
    panel.render(state.getState());

    const row = panel.element.querySelector(".tm-result");
    expect(row?.querySelector(".tm-result-title")?.textContent).toBe("The Republic");
    expect(row?.querySelector(".tm-result-meta")?.textContent).toBe("Plato · gutendex");
    expect(row?.querySelector(".tm-result-similarity")?.textContent).toBe("0.7360");
  });

  it("renders results in the API's order without re-sorting", () => {
    const state = stateWith([
      result({ doc_id: "a", title: "Low", similarity: 0.2 }),
      result({ doc_id: "b", title: "High", similarity: 0.9 }),
      result({ doc_id: "c", title: "Mid", similarity: 0.5 }),
    ]);
    panel.render(state.getState());
    expect(rowTexts(panel)).toEqual(["Low", "High", "Mid"]);
  });

  it("states a zero-result search plainly and not as an error", () => {
    const state = stateWith([]);
    panel.render(state.getState());

    const note = panel.element.querySelector(".tm-note")?.textContent ?? "";
    expect(note).toContain("No results");
    expect(note).toContain("Plato");
    expect(panel.element.querySelector(".tm-error")).toBeNull();
  });

  it("reports the result count", () => {
    panel.render(stateWith([result({ doc_id: "a" }), result({ doc_id: "b" })]).getState());
    expect(panel.element.querySelector(".tm-note")?.textContent).toContain("2 results");

    panel.render(stateWith([result({ doc_id: "a" })]).getState());
    expect(panel.element.querySelector(".tm-note")?.textContent).toContain("1 result for");
  });

  it("routes a click to the selection callback", () => {
    const state = stateWith([result({ doc_id: "a" }), result({ doc_id: "b" })]);
    panel.render(state.getState());

    const rows = panel.element.querySelectorAll<HTMLElement>(".tm-result");
    rows[1]?.click();

    expect(onSelect).toHaveBeenCalledWith("b");
  });

  it("marks the selected row from shared state", () => {
    const state = stateWith([result({ doc_id: "a" }), result({ doc_id: "b" })]);
    const selection = new SelectionController(state);
    panel.render(state.getState());

    selection.select("b");
    panel.render(state.getState());

    const rows = panel.element.querySelectorAll<HTMLElement>(".tm-result");
    expect(rows[0]?.classList.contains("is-selected")).toBe(false);
    expect(rows[1]?.classList.contains("is-selected")).toBe(true);
    expect(rows[1]?.getAttribute("aria-selected")).toBe("true");
  });

  it("shows an API error message, beside the results, without any stack trace", () => {
    const state = new AppState();
    state.searchFailed(state.startSearch(), "The ThoughtMap API failed to complete the search.");

    panel.render(state.getState());

    const error = panel.element.querySelector<HTMLElement>(".tm-error");
    expect(error?.hidden).toBe(false);
    expect(error?.textContent).toBe("The ThoughtMap API failed to complete the search.");
    expect(error?.textContent).not.toContain("Traceback");
    expect(panel.element.querySelector(".tm-note")?.textContent).toContain("Search failed");
  });

  it("offers a retry after a failure and removes the error once a search succeeds", () => {
    const onRetry = vi.fn();
    const retrying = new ResultPanel({ onSelect, onRetry });
    const state = new AppState();
    state.searchFailed(state.startSearch(), "Down.");
    retrying.render(state.getState());

    const retry = Array.from(retrying.element.querySelectorAll<HTMLButtonElement>("button")).find(
      (button) => button.textContent === "Try again",
    );
    retry?.click();
    expect(onRetry).toHaveBeenCalledTimes(1);

    state.searchSucceeded(state.startSearch(), { query: "q", results: [], queryParameters: null });
    retrying.render(state.getState());
    expect(retrying.element.querySelector(".tm-error")).toBeNull();
  });

  it("marks a result that has no node in the loaded map, and only then", () => {
    const state = stateWith([result({ doc_id: "in" }), result({ doc_id: "out" })]);
    panel.render(state.getState());
    // No map yet: nothing can be claimed missing from it.
    expect(panel.element.querySelectorAll(".tm-result.is-offmap")).toHaveLength(0);

    state.mapLoaded([{ doc_id: "in", title: "", author: "", source: "", x: 0, y: 0, z: 0 }], {} as never);
    panel.render(state.getState());

    const rows = panel.element.querySelectorAll<HTMLElement>(".tm-result");
    expect(rows[0]?.classList.contains("is-offmap")).toBe(false);
    expect(rows[1]?.classList.contains("is-offmap")).toBe(true);
    // Still selectable: being off the map never removes a result from use.
    rows[1]?.click();
    expect(onSelect).toHaveBeenCalledWith("out");
  });

  it("reports pointer hover on a row so the map can light the node", () => {
    const onHover = vi.fn();
    const hovering = new ResultPanel({ onSelect, onHover });
    hovering.render(stateWith([result({ doc_id: "a" })]).getState());

    hovering.element.querySelector(".tm-result")?.dispatchEvent(new Event("mouseenter"));
    expect(onHover).toHaveBeenCalledWith("a");
  });

  it("gives the list a single tab stop and moves with the arrow keys", () => {
    const state = stateWith([result({ doc_id: "a" }), result({ doc_id: "b" }), result({ doc_id: "c" })]);
    document.body.append(panel.element);
    panel.render(state.getState());

    const rows = Array.from(panel.element.querySelectorAll<HTMLElement>(".tm-result"));
    expect(rows.map((row) => row.tabIndex)).toEqual([0, -1, -1]);

    rows[0]?.focus();
    rows[0]?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    expect(document.activeElement).toBe(rows[1]);
    panel.element.remove();
  });

  it("falls back to a dash for missing title or author", () => {
    const state = stateWith([result({ doc_id: "a", title: "", author: "" })]);
    panel.render(state.getState());
    expect(panel.element.querySelector(".tm-result-title")?.textContent).toBe("—");
  });
});

describe("DetailPanel", () => {
  it("prompts for a selection when nothing is selected", () => {
    const panel = new DetailPanel();
    const state = stateWith([result({ doc_id: "a" })]);

    panel.render(state.getState(), null);

    expect(panel.element.querySelector<HTMLElement>(".tm-note")?.hidden).toBe(false);
    expect(panel.element.querySelector<HTMLElement>(".tm-detail-body")?.hidden).toBe(true);
  });

  it("shows the selected document's fields", () => {
    const panel = new DetailPanel();
    const selected = result({
      doc_id: "gutendex:doc_000631",
      title: "Apology",
      author: "Plato",
      source: "gutendex",
      similarity: 0.97,
    });
    const state = stateWith([selected]);
    state.select(selected.doc_id);

    panel.render(state.getState(), fromSearchResult(selected));

    expect(panel.element.querySelector(".tm-detail-title")?.textContent).toBe("Apology");
    const values = Array.from(panel.element.querySelectorAll(".tm-detail-field dd")).map(
      (node) => node.textContent,
    );
    expect(values).toEqual(["Plato", "gutendex", "0.9700", "gutendex:doc_000631"]);
  });

  it("renders an Open Link button when the URL is usable", () => {
    const panel = new DetailPanel();
    const selected = result({ doc_id: "a", url: "https://www.gutenberg.org/ebooks/1497" });
    panel.render(stateWith([selected]).getState(), fromSearchResult(selected));

    const link = panel.element.querySelector<HTMLAnchorElement>(".tm-link-button");
    expect(link?.hidden).toBe(false);
    expect(link?.href).toBe("https://www.gutenberg.org/ebooks/1497");
    expect(link?.target).toBe("_blank");
    expect(link?.rel).toContain("noopener");
    expect(link?.rel).toContain("noreferrer");
    expect(panel.element.querySelector<HTMLElement>(".tm-link-unavailable")?.hidden).toBe(true);
  });

  it("shows an unavailable note instead of a dead button when the URL is missing", () => {
    const panel = new DetailPanel();
    const selected = result({ doc_id: "a" });
    panel.render(stateWith([selected]).getState(), fromSearchResult(selected));

    expect(panel.element.querySelector<HTMLElement>(".tm-link-button")?.hidden).toBe(true);
    expect(panel.element.querySelector<HTMLElement>(".tm-link-unavailable")?.hidden).toBe(false);
  });

  it("refuses to link a non-http scheme", () => {
    const panel = new DetailPanel();
    const selected = result({ doc_id: "a", url: "javascript:alert(1)" });
    panel.render(stateWith([selected]).getState(), fromSearchResult(selected));

    const link = panel.element.querySelector<HTMLAnchorElement>(".tm-link-button");
    expect(link?.hidden).toBe(true);
    expect(link?.hasAttribute("href")).toBe(false);
  });

  it("renders an empty state for a document with no parameters instead of throwing", () => {
    const panel = new DetailPanel();
    const selected = result({ doc_id: "a" });

    expect(() => panel.render(stateWith([selected]).getState(), fromSearchResult(selected))).not.toThrow();

    // No query profile and no document profile: the radar says so rather than
    // drawing an empty chart.
    const radar = panel.element.querySelector(".tm-radar");
    expect(radar?.querySelector<HTMLElement>(".tm-radar-note")?.hidden).toBe(false);
    expect(radar?.querySelectorAll(".tm-radar-shape")).toHaveLength(0);
  });

  it("renders the document's Thought Composition on the radar", () => {
    const panel = new DetailPanel();
    const selected = result({
      doc_id: "a",
      parameters: [
        { key: "science", value: 0.12 },
        { key: "philosophy", value: 0.15 },
      ],
    });
    panel.render(stateWith([selected]).getState(), fromSearchResult(selected));

    const labels = Array.from(panel.element.querySelectorAll(".tm-radar-label")).map(
      (node) => node.textContent,
    );
    // Canonical axis order, regardless of the order the API sent.
    expect(labels.slice(0, 3)).toEqual(["Philosophy", "Psychology", "Science"]);
    expect(panel.element.querySelectorAll(".tm-radar-shape.is-document")).toHaveLength(1);
  });

  it("renders the query profile from the search, not from the selection", () => {
    const panel = new DetailPanel();
    const queryParameters: ParameterScore[] = [
      { key: "philosophy", value: 0.1392 },
      { key: "ideal", value: 0.1385 },
    ];
    const state = stateWith([result({ doc_id: "a" })], queryParameters);

    panel.render(state.getState(), null);

    // The query polygon is present with nothing selected.
    expect(panel.element.querySelectorAll(".tm-radar-shape.is-query")).toHaveLength(1);
    expect(panel.element.querySelectorAll(".tm-radar-shape.is-document")).toHaveLength(0);

    const table = panel.element.querySelector(".tm-radar-table");
    expect(table?.textContent).toContain("13.9%");
  });

  it("shows an unavailable note when there is no profile to draw", () => {
    const panel = new DetailPanel();
    const state = stateWith([result({ doc_id: "a" })], null);

    panel.render(state.getState(), null);

    const note = panel.element.querySelector<HTMLElement>(".tm-radar-note");
    expect(note?.hidden).toBe(false);
    expect(note?.textContent).toContain("No parameter profile");
  });

  it("renders a document selected from the map without faking a similarity", () => {
    const panel = new DetailPanel();
    const node = {
      doc_id: "gutendex:doc_000900",
      title: "Meditations",
      author: "Marcus Aurelius",
      source: "gutendex",
      x: 1,
      y: 2,
      z: 3,
      cluster: 2,
    };

    panel.render(stateWith([result({ doc_id: "other" })]).getState(), fromMapNode(node));

    const values = Array.from(panel.element.querySelectorAll(".tm-detail-field dd")).map(
      (n) => n.textContent,
    );
    expect(values[0]).toBe("Marcus Aurelius");
    expect(values[3]).toBe("gutendex:doc_000900");
    // Never "0.0000": that would claim maximal dissimilarity.
    expect(values[2]).toBe("Not in current results");
    expect(values[2]).not.toContain("0.0000");
  });

  it("explains that a map-selected document is outside the current results", () => {
    const panel = new DetailPanel();
    const node = { doc_id: "a", title: "T", author: "", source: "zip", x: 0, y: 0, z: 0, cluster: 0 };

    panel.render(stateWith([]).getState(), fromMapNode(node));
    expect(panel.element.querySelector<HTMLElement>(".tm-detail-origin")?.hidden).toBe(false);

    const searched = result({ doc_id: "a" });
    panel.render(stateWith([searched]).getState(), fromSearchResult(searched));
    expect(panel.element.querySelector<HTMLElement>(".tm-detail-origin")?.hidden).toBe(true);
  });

  it("leaves search failures to the result list and keeps showing the document", () => {
    const panel = new DetailPanel();
    const node = { doc_id: "a", title: "Kept", author: "", source: "zip", x: 0, y: 0, z: 0, cluster: 0 };
    const state = new AppState();
    state.searchFailed(state.startSearch(), "The ThoughtMap API failed to complete the search.");

    panel.render(state.getState(), fromMapNode(node));

    expect(panel.element.querySelector(".tm-error")).toBeNull();
    expect(panel.element.querySelector(".tm-detail-title")?.textContent).toBe("Kept");
  });
});

describe("ParameterList", () => {
  it("scales bars against the largest axis so a composition stays readable", () => {
    const list = new ParameterList("Test", "none");
    list.render([
      { key: "philosophy", value: 0.14 },
      { key: "science", value: 0.07 },
    ]);

    const fills = list.element.querySelectorAll<HTMLElement>(".tm-param-fill");
    expect(fills[0]?.style.width).toBe("100%");
    expect(fills[1]?.style.width).toBe("50%");
  });

  it("displays percentages while the caller keeps 0..1 values", () => {
    const list = new ParameterList("Test", "none");
    const scores: ParameterScore[] = [{ key: "philosophy", value: 0.1392 }];
    list.render(scores);

    expect(list.element.querySelector(".tm-param-value")?.textContent).toBe("13.9%");
    // The source data is untouched.
    expect(scores[0]?.value).toBe(0.1392);
  });

  it("shows the empty message for a missing set", () => {
    const list = new ParameterList("Test", "nothing here");
    list.render(null);

    expect(list.element.querySelector<HTMLElement>(".tm-note")?.hidden).toBe(false);
    expect(list.element.querySelector<HTMLElement>(".tm-params-body")?.hidden).toBe(true);
  });
});
