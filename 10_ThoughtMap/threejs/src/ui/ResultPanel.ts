import type { SearchResult } from "../api/types";
import type { AppStateSnapshot } from "../app/AppState";
import { formatCount, formatSimilarity, orDash } from "./format";

export interface ResultPanelCallbacks {
  onSelect: (docId: string) => void;
}

/**
 * The ranked result list.
 *
 * Renders `state.results` in the order the API returned them. It never sorts,
 * filters, or re-ranks — that ordering is the backend's answer.
 */
export class ResultPanel {
  readonly element: HTMLElement;

  private readonly status: HTMLElement;
  private readonly list: HTMLElement;
  private readonly rows = new Map<string, HTMLElement>();
  private renderedResults: readonly SearchResult[] = [];
  private lastSelectedDocId: string | null = null;

  constructor(private readonly callbacks: ResultPanelCallbacks) {
    this.element = document.createElement("section");
    this.element.className = "tm-panel tm-results";

    const heading = document.createElement("h2");
    heading.className = "tm-panel-title";
    heading.textContent = "Results";

    this.status = document.createElement("p");
    this.status.className = "tm-note";
    // "10 results for Plato" is the outcome of the action someone just took.
    // Without a live region it is announced to nobody, and a keyboard user has
    // to go looking for whether anything happened (T7 #33).
    this.status.setAttribute("role", "status");
    this.status.setAttribute("aria-live", "polite");

    this.list = document.createElement("ul");
    this.list.className = "tm-result-list";
    this.list.setAttribute("role", "listbox");
    this.list.setAttribute("aria-label", "Search results");

    this.element.append(heading, this.status, this.list);
  }

  render(snapshot: AppStateSnapshot): void {
    this.renderStatus(snapshot);

    // Rebuild rows only when the result set itself changed; a selection change
    // just moves a class.
    if (snapshot.results !== this.renderedResults) {
      this.renderedResults = snapshot.results;
      this.rows.clear();
      this.list.replaceChildren(
        ...snapshot.results.map((result, index) => this.buildRow(result, index)),
      );
    }

    let newlySelected: HTMLElement | null = null;

    for (const [docId, row] of this.rows) {
      const selected = docId === snapshot.selectedDocId;
      row.classList.toggle("is-selected", selected);
      row.setAttribute("aria-selected", String(selected));
      row.classList.toggle("is-hovered", docId === snapshot.hoveredDocId);
      // A marker, not a second Save button: the action lives in the detail
      // panel, and a button per row would clutter a list of fifty.
      row.classList.toggle("is-saved", snapshot.savedDocIds.has(docId));

      if (selected && docId !== this.lastSelectedDocId) {
        newlySelected = row;
      }
    }

    // Selecting a node in the map can pick a document far down the list, so
    // bring it into view — but only when the selection actually changed, or
    // every unrelated re-render would yank the list around.
    if (newlySelected) {
      newlySelected.scrollIntoView({ block: "nearest" });
    }
    this.lastSelectedDocId = snapshot.selectedDocId;
  }

  private renderStatus(snapshot: AppStateSnapshot): void {
    this.list.hidden = snapshot.results.length === 0;

    if (snapshot.status === "idle") {
      this.status.hidden = false;
      this.status.textContent = "Enter a query to search the thought space.";
      return;
    }

    if (snapshot.status === "searching") {
      this.status.hidden = false;
      this.status.textContent = "Searching…";
      return;
    }

    if (snapshot.status === "error") {
      // The error text itself is shown by the detail/error area, not here.
      this.status.hidden = false;
      this.status.textContent = "Search failed.";
      return;
    }

    if (snapshot.results.length === 0) {
      // A successful search that matched nothing is not an error.
      this.status.hidden = false;
      this.status.textContent = `No results for “${snapshot.lastQuery}”.`;
      return;
    }

    this.status.hidden = false;
    this.status.textContent = `${formatCount(snapshot.results.length, "result")} for “${snapshot.lastQuery}”.`;
  }

  private buildRow(result: SearchResult, index: number): HTMLElement {
    const row = document.createElement("li");
    row.className = "tm-result";
    row.tabIndex = 0;
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

    const meta = document.createElement("span");
    meta.className = "tm-result-meta";
    meta.textContent = `${orDash(result.author)} · ${orDash(result.source)}`;

    main.append(title, meta);

    const similarity = document.createElement("span");
    similarity.className = "tm-result-similarity";
    similarity.textContent = formatSimilarity(result.similarity);

    const savedMark = document.createElement("span");
    savedMark.className = "tm-result-saved";
    savedMark.textContent = "✦";
    savedMark.title = "In your Personal Library";
    savedMark.setAttribute("aria-label", "Saved to your Personal Library");

    row.append(rank, main, savedMark, similarity);

    const select = () => this.callbacks.onSelect(result.doc_id);
    row.addEventListener("click", select);
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        select();
      }
    });

    this.rows.set(result.doc_id, row);
    return row;
  }
}
