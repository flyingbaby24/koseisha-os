import { isSearchMode } from "../api/types";
import type { AppState, AppStateSnapshot } from "../app/AppState";
import {
  FILTER_OPTIONS,
  MODE_OPTIONS,
  SOURCE_OPTIONS,
  TOP_OPTIONS,
  type SelectOption,
} from "../config/searchOptions";

export interface SearchPanelCallbacks {
  onSearch: () => void;
}

/** Query input, mode/source/filter/top selectors, and the Search button. */
export class SearchPanel {
  readonly element: HTMLElement;

  private readonly input: HTMLInputElement;
  private readonly modeSelect: HTMLSelectElement;
  private readonly sourceSelect: HTMLSelectElement;
  private readonly filterSelect: HTMLSelectElement;
  private readonly topSelect: HTMLSelectElement;
  private readonly button: HTMLButtonElement;
  private readonly spinner: HTMLElement;

  constructor(
    private readonly state: AppState,
    private readonly callbacks: SearchPanelCallbacks,
  ) {
    this.element = document.createElement("form");
    this.element.className = "tm-search";
    (this.element as HTMLFormElement).noValidate = true;

    this.input = document.createElement("input");
    this.input.type = "search";
    this.input.className = "tm-search-input";
    this.input.placeholder = "Search the thought space…";
    this.input.setAttribute("aria-label", "Search query");
    this.input.autocomplete = "off";

    this.modeSelect = buildSelect("Mode", MODE_OPTIONS.map(toOption));
    this.sourceSelect = buildSelect("Source", SOURCE_OPTIONS);
    this.filterSelect = buildSelect("Filter", FILTER_OPTIONS);
    this.topSelect = buildSelect(
      "Results",
      TOP_OPTIONS.map((count) => ({ value: String(count), label: `Top ${count}` })),
    );

    this.button = document.createElement("button");
    this.button.type = "submit";
    this.button.className = "tm-search-button";
    this.button.textContent = "Search";

    this.spinner = document.createElement("span");
    this.spinner.className = "tm-spinner";
    this.spinner.hidden = true;
    this.spinner.setAttribute("aria-hidden", "true");

    const row = document.createElement("div");
    row.className = "tm-search-row";
    row.append(this.input, this.button, this.spinner);

    const controls = document.createElement("div");
    controls.className = "tm-search-controls";
    controls.append(
      labelled("Mode", this.modeSelect),
      labelled("Source", this.sourceSelect),
      labelled("Filter", this.filterSelect),
      labelled("Results", this.topSelect),
    );

    this.element.append(row, controls);
    this.bind();
  }

  private bind(): void {
    // Submitting the form covers both the button and Enter in the input.
    this.element.addEventListener("submit", (event) => {
      event.preventDefault();
      this.callbacks.onSearch();
    });

    this.input.addEventListener("input", () => this.state.setQuery(this.input.value));

    this.modeSelect.addEventListener("change", () => {
      const value = this.modeSelect.value;
      if (isSearchMode(value)) {
        this.state.setMode(value);
      }
    });

    this.sourceSelect.addEventListener("change", () => this.state.setSource(this.sourceSelect.value));
    this.filterSelect.addEventListener("change", () => this.state.setFilter(this.filterSelect.value));
    this.topSelect.addEventListener("change", () =>
      this.state.setTop(Number.parseInt(this.topSelect.value, 10)),
    );
  }

  render(snapshot: AppStateSnapshot): void {
    // Only write back when different, so typing is not interrupted.
    if (this.input.value !== snapshot.query) {
      this.input.value = snapshot.query;
    }
    if (this.modeSelect.value !== snapshot.mode) {
      this.modeSelect.value = snapshot.mode;
    }
    if (this.sourceSelect.value !== snapshot.source) {
      this.sourceSelect.value = snapshot.source;
    }
    if (this.filterSelect.value !== snapshot.filter) {
      this.filterSelect.value = snapshot.filter;
    }
    const top = String(snapshot.top);
    if (this.topSelect.value !== top) {
      this.topSelect.value = top;
    }

    const searching = snapshot.status === "searching";
    this.button.disabled = searching;
    this.button.textContent = searching ? "Searching…" : "Search";
    this.spinner.hidden = !searching;
    this.element.classList.toggle("is-searching", searching);
  }

  focus(): void {
    this.input.focus();
  }
}

function toOption(option: { value: string; label: string }): SelectOption {
  return { value: option.value, label: option.label };
}

function buildSelect(ariaLabel: string, options: readonly SelectOption[]): HTMLSelectElement {
  const select = document.createElement("select");
  select.className = "tm-select";
  select.setAttribute("aria-label", ariaLabel);

  for (const option of options) {
    const element = document.createElement("option");
    element.value = option.value;
    element.textContent = option.label;
    select.append(element);
  }

  return select;
}

function labelled(text: string, control: HTMLElement): HTMLElement {
  const wrapper = document.createElement("label");
  wrapper.className = "tm-field";

  const caption = document.createElement("span");
  caption.className = "tm-field-label";
  caption.textContent = text;

  wrapper.append(caption, control);
  return wrapper;
}
