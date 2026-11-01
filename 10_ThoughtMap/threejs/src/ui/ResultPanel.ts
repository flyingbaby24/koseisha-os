import type { SearchResult } from "../api/types";
import type { AppStateSnapshot } from "../app/AppState";
import { mapMembership } from "../app/mapMembership";
import { sourceStyle } from "../config/sourceStyles";
import { formatCount, formatSimilarity, orDash } from "./format";

export interface ResultPanelCallbacks {
  onSelect: (docId: string) => void;
  /** Pointer or keyboard is on a row; null when it leaves. Drives map hover. */
  onHover?: (docId: string | null) => void;
  /** Run the current search again (offered after a failure). */
  onRetry?: () => void;
  /** Run an example query (offered before the first search). */
  onExample?: (query: string) => void;
}

/** Starting points offered before the first search. */
const EXAMPLE_QUERIES = ["virtue and happiness", "the nature of time", "Plato"];

/** Placeholder rows shown while the first results are on their way. */
const SKELETON_ROWS = 5;

/**
 * The ranked result list.
 *
 * Renders `state.results` in the order the API returned them. It never sorts,
 * filters, or re-ranks — that ordering is the backend's answer.
 *
 * Four outcomes look different on purpose — waiting, searching, failed, and
 * "searched and matched nothing" — so nobody has to infer from an empty list
 * which of them just happened.
 */
export class ResultPanel {
  readonly element: HTMLElement;

  private readonly status: HTMLElement;
  private readonly summary: HTMLElement;
  private readonly list: HTMLElement;
  private readonly skeleton: HTMLElement;
  private readonly idleState: HTMLElement;
  private readonly emptyState: HTMLElement;
  private readonly emptyHint: HTMLElement;
  private readonly alert: HTMLElement;
  private readonly alertMessage: HTMLElement;
  private readonly rows = new Map<string, HTMLElement>();
  private renderedResults: readonly SearchResult[] = [];
  private renderedMembership: ReadonlySet<string> | null = null;
  private lastSelectedDocId: string | null = null;

  constructor(private readonly callbacks: ResultPanelCallbacks) {
    this.element = document.createElement("section");
    this.element.className = "tm-panel tm-results";

    const heading = document.createElement("h2");
    heading.className = "tm-panel-title";
    heading.textContent = "Results";

    this.status = document.createElement("p");
    this.status.className = "tm-note tm-results-status";
    // "10 results for Plato" is the outcome of the action someone just took.
    // Without a live region it is announced to nobody, and a keyboard user has
    // to go looking for whether anything happened (T7 #33).
    this.status.setAttribute("role", "status");
    this.status.setAttribute("aria-live", "polite");

    this.summary = document.createElement("p");
    this.summary.className = "tm-results-summary";
    this.summary.hidden = true;

    // Created once, attached only while a search has failed: an error element
    // must not exist at all for a search that merely matched nothing.
    this.alert = document.createElement("div");
    this.alert.className = "tm-alert";
    this.alertMessage = document.createElement("p");
    this.alertMessage.className = "tm-error";
    this.alertMessage.setAttribute("role", "alert");
    const retry = document.createElement("button");
    retry.type = "button";
    retry.className = "tm-button is-quiet";
    retry.textContent = "Try again";
    retry.addEventListener("click", () => this.callbacks.onRetry?.());
    this.alert.append(this.alertMessage, retry);

    this.idleState = this.buildIdleState();

    this.emptyState = document.createElement("div");
    this.emptyState.className = "tm-empty";
    const emptyTitle = document.createElement("p");
    emptyTitle.className = "tm-empty-title";
    emptyTitle.textContent = "Nothing matched";
    this.emptyHint = document.createElement("p");
    this.emptyHint.className = "tm-empty-text";
    this.emptyState.append(emptyTitle, this.emptyHint);
    this.emptyState.hidden = true;

    this.skeleton = document.createElement("ul");
    this.skeleton.className = "tm-skeleton";
    this.skeleton.setAttribute("aria-hidden", "true");
    for (let index = 0; index < SKELETON_ROWS; index += 1) {
      const row = document.createElement("li");
      row.append(document.createElement("span"), document.createElement("span"));
      this.skeleton.append(row);
    }
    this.skeleton.hidden = true;

    this.list = document.createElement("ul");
    this.list.className = "tm-result-list";
    this.list.setAttribute("role", "listbox");
    this.list.setAttribute("aria-label", "Search results");
    this.list.addEventListener("keydown", this.handleListKeydown);
    this.list.addEventListener("mouseleave", () => this.callbacks.onHover?.(null));
    this.list.addEventListener("focusout", (event) => {
      if (!this.list.contains(event.relatedTarget as Node | null)) {
        this.callbacks.onHover?.(null);
      }
    });

    this.element.append(
      heading,
      this.status,
      this.summary,
      this.idleState,
      this.emptyState,
      this.skeleton,
      this.list,
    );
  }

  render(snapshot: AppStateSnapshot): void {
    this.renderStatus(snapshot);

    const membership = mapMembership(snapshot);

    // Rebuild rows only when the result set (or the map they join) changed; a
    // selection change just moves a class.
    if (snapshot.results !== this.renderedResults || membership !== this.renderedMembership) {
      this.renderedResults = snapshot.results;
      this.renderedMembership = membership;
      this.rows.clear();
      this.list.replaceChildren(
        ...snapshot.results.map((result, index) => this.buildRow(result, index, membership)),
      );
      this.renderSummary(snapshot, membership);
    }

    let newlySelected: HTMLElement | null = null;
    let focusable: HTMLElement | null = null;

    for (const [docId, row] of this.rows) {
      const selected = docId === snapshot.selectedDocId;
      row.classList.toggle("is-selected", selected);
      row.setAttribute("aria-selected", String(selected));
      row.classList.toggle("is-hovered", docId === snapshot.hoveredDocId);
      // A marker, not a second Save button: the action lives in the detail
      // panel, and a button per row would clutter a list of fifty.
      row.classList.toggle("is-saved", snapshot.savedDocIds.has(docId));

      if (selected) {
        focusable = row;
        if (docId !== this.lastSelectedDocId) {
          newlySelected = row;
        }
      }
    }

    // Roving tab stop: Tab enters the list once (at the selection, or the top),
    // and the arrow keys move within it — fifty tab stops would be a wall.
    focusable ??= this.list.firstElementChild as HTMLElement | null;
    for (const row of this.rows.values()) {
      row.tabIndex = row === focusable ? 0 : -1;
    }

    // Selecting a node in the map can pick a document far down the list, so
    // bring it into view — but only when the selection actually changed, or
    // every unrelated re-render would yank the list around.
    if (newlySelected) {
      newlySelected.scrollIntoView({ block: "nearest" });
    }
    this.lastSelectedDocId = snapshot.selectedDocId;
  }

  /**
   * Bring the selected row into view, for when the list is shown again.
   *
   * While a phone shows the document instead of the list, the scroll on
   * selection lands on a hidden list and does nothing; stepping through
   * results then leaves the list far from the document just read.
   */
  revealSelected(): void {
    const docId = this.lastSelectedDocId;
    const row = docId === null ? undefined : this.rows.get(docId);
    row?.scrollIntoView({ block: "nearest" });
  }

  private renderStatus(snapshot: AppStateSnapshot): void {
    const searching = snapshot.status === "searching";
    const failed = snapshot.status === "error";
    const hasResults = snapshot.results.length > 0;

    this.list.hidden = !hasResults;
    // A re-search keeps the previous rows visible but visibly provisional.
    this.list.classList.toggle("is-stale", searching && hasResults);
    this.skeleton.hidden = !(searching && !hasResults);
    this.idleState.hidden = snapshot.status !== "idle";
    this.emptyState.hidden = !(snapshot.status === "success" && !hasResults);
    this.element.dataset["status"] = snapshot.status;

    if (failed) {
      this.alertMessage.textContent = snapshot.error ?? "The search could not be completed.";
      // Parent, not isConnected: the panel itself may not be in a document.
      if (this.alert.parentNode !== this.element) {
        this.status.after(this.alert);
      }
    } else if (this.alert.parentNode) {
      this.alert.remove();
    }

    if (snapshot.status === "idle") {
      this.status.textContent = "Enter a query to search the thought space.";
      this.summary.hidden = true;
      return;
    }

    if (searching) {
      this.status.textContent = "Searching…";
      return;
    }

    if (failed) {
      this.status.textContent = "Search failed.";
      this.summary.hidden = true;
      return;
    }

    if (!hasResults) {
      // A successful search that matched nothing is not an error.
      this.status.textContent = `No results for “${snapshot.lastQuery}”.`;
      this.emptyHint.textContent = emptySuggestion(snapshot);
      this.summary.hidden = true;
      return;
    }

    this.status.textContent = `${formatCount(snapshot.results.length, "result")} for “${snapshot.lastQuery}”.`;
  }

  /** One line on how the results relate to the map, only when it matters. */
  private renderSummary(snapshot: AppStateSnapshot, membership: ReadonlySet<string> | null): void {
    if (!membership || snapshot.results.length === 0) {
      this.summary.hidden = true;
      return;
    }
    const missing = snapshot.results.filter((result) => !membership.has(result.doc_id)).length;
    if (missing === 0) {
      this.summary.hidden = true;
      return;
    }
    this.summary.hidden = false;
    this.summary.textContent =
      `${formatCount(missing, "result")} ${missing === 1 ? "has" : "have"} no position in the ` +
      "map. Still fully readable here.";
  }

  private buildIdleState(): HTMLElement {
    const wrapper = document.createElement("div");
    wrapper.className = "tm-empty is-idle";

    const title = document.createElement("p");
    title.className = "tm-empty-title";
    title.textContent = "Search by idea, not only by word";

    const text = document.createElement("p");
    text.className = "tm-empty-text";
    text.textContent =
      "Results light up in the map. Select one to see where it sits and how its " +
      "Thought Composition compares with your query.";

    const examples = document.createElement("div");
    examples.className = "tm-examples";
    const label = document.createElement("span");
    label.className = "tm-examples-label";
    label.textContent = "Try";
    examples.append(label);
    for (const query of EXAMPLE_QUERIES) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "tm-chip";
      chip.textContent = query;
      chip.addEventListener("click", () => this.callbacks.onExample?.(query));
      examples.append(chip);
    }

    wrapper.append(title, text, examples);
    return wrapper;
  }

  private buildRow(
    result: SearchResult,
    index: number,
    membership: ReadonlySet<string> | null,
  ): HTMLElement {
    const row = document.createElement("li");
    row.className = "tm-result";
    row.tabIndex = -1;
    row.setAttribute("role", "option");
    row.dataset["docId"] = result.doc_id;

    const rank = document.createElement("span");
    rank.className = "tm-result-rank";
    rank.textContent = String(index + 1);

    const main = document.createElement("span");
    main.className = "tm-result-main";

    const title = document.createElement("span");
    title.className = "tm-result-title";
    title.textContent = orDash(result.title);
    title.title = result.title;

    const meta = document.createElement("span");
    meta.className = "tm-result-meta";
    // The dot carries no text, so the line still reads "Author · source".
    const dot = document.createElement("span");
    dot.className = "tm-source-dot";
    dot.style.setProperty("--tm-dot", cssColor(sourceStyle(result.source).color));
    meta.append(dot, `${orDash(result.author)} · ${orDash(result.source)}`);

    const flags = document.createElement("span");
    flags.className = "tm-result-flags";

    const savedMark = document.createElement("span");
    savedMark.className = "tm-result-saved";
    savedMark.textContent = "Saved";
    savedMark.title = "In your Personal Library";
    flags.append(savedMark);

    if (membership && !membership.has(result.doc_id)) {
      row.classList.add("is-offmap");
      const offMap = document.createElement("span");
      offMap.className = "tm-result-offmap";
      offMap.textContent = "Not in map";
      offMap.title =
        "This document has no position in the current 3D projection. Its detail and profile are still available.";
      flags.append(offMap);
    }

    main.append(title, meta, flags);

    const score = document.createElement("span");
    score.className = "tm-result-score";

    const similarity = document.createElement("span");
    similarity.className = "tm-result-similarity";
    similarity.textContent = formatSimilarity(result.similarity);

    // Absolute scale (0..1), not relative to the best result: a weak top hit
    // should look weak.
    const bar = document.createElement("span");
    bar.className = "tm-result-simbar";
    bar.setAttribute("aria-hidden", "true");
    const fill = document.createElement("span");
    const ratio = Number.isFinite(result.similarity) ? Math.min(1, Math.max(0, result.similarity)) : 0;
    fill.style.width = `${(ratio * 100).toFixed(1)}%`;
    bar.append(fill);

    score.append(similarity, bar);
    row.append(rank, main, score);

    const select = () => this.callbacks.onSelect(result.doc_id);
    row.addEventListener("click", select);
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        select();
      }
    });
    row.addEventListener("mouseenter", () => this.callbacks.onHover?.(result.doc_id));
    row.addEventListener("focus", () => this.callbacks.onHover?.(result.doc_id));

    this.rows.set(result.doc_id, row);
    return row;
  }

  /** Arrow keys, Home and End move between rows. */
  private readonly handleListKeydown = (event: KeyboardEvent): void => {
    const rows = [...this.rows.values()];
    const current = rows.indexOf(document.activeElement as HTMLElement);
    if (current === -1) {
      return;
    }

    let next = -1;
    if (event.key === "ArrowDown") {
      next = Math.min(rows.length - 1, current + 1);
    } else if (event.key === "ArrowUp") {
      next = Math.max(0, current - 1);
    } else if (event.key === "Home") {
      next = 0;
    } else if (event.key === "End") {
      next = rows.length - 1;
    }

    if (next === -1) {
      return;
    }
    event.preventDefault();
    const target = rows[next];
    if (target) {
      for (const row of rows) {
        row.tabIndex = row === target ? 0 : -1;
      }
      target.focus();
      target.scrollIntoView({ block: "nearest" });
    }
  };
}

/** Constructive next steps for a search that matched nothing. */
function emptySuggestion(snapshot: AppStateSnapshot): string {
  const narrowed: string[] = [];
  if (snapshot.source) {
    narrowed.push("the source");
  }
  if (snapshot.filter && snapshot.filter !== "general") {
    narrowed.push("the filter");
  }
  if (narrowed.length > 0) {
    return `Try clearing ${narrowed.join(" and ")} in Options, or use fewer words.`;
  }
  if (snapshot.mode === "keyword") {
    return "Keyword mode needs the words to appear in the catalogue. Try Semantic mode, or fewer words.";
  }
  return "Try fewer or broader words, or a different mode in Options.";
}

export function cssColor([r, g, b]: readonly [number, number, number]): string {
  return `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`;
}
