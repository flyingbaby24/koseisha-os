import { isSearchMode } from "../api/types";
import type { AppState, AppStateSnapshot } from "../app/AppState";
import {
  DEFAULT_FILTER,
  DEFAULT_SOURCE,
  DEFAULT_TOP,
  FILTER_OPTIONS,
  MODE_DESCRIPTIONS,
  MODE_OPTIONS,
  SOURCE_DESCRIPTION,
  SOURCE_OPTIONS,
  TOP_DESCRIPTION,
  TOP_OPTIONS,
  describeFilter,
  optionLabel,
  type SelectOption,
} from "../config/searchOptions";

export interface SearchPanelCallbacks {
  onSearch: () => void;
}

let panelSequence = 0;

/**
 * Query input, Search, and the search options.
 *
 * The query is the one thing everyone needs, so it gets the row to itself.
 * Mode / Source / Filter / Results are all still here with the same values and
 * the same meaning, but behind an Options disclosure whose button always
 * states what is in effect — nobody has to open it to know how they are
 * searching, and nobody who never changes them has to look at them.
 */
export class SearchPanel {
  readonly element: HTMLElement;

  private readonly input: HTMLInputElement;
  private readonly modeSelect: HTMLSelectElement;
  private readonly sourceSelect: HTMLSelectElement;
  private readonly filterSelect: HTMLSelectElement;
  private readonly topSelect: HTMLSelectElement;
  private readonly button: HTMLButtonElement;
  private readonly spinner: HTMLElement;
  private readonly optionsToggle: HTMLButtonElement;
  private readonly optionsSummary: HTMLElement;
  private readonly optionsBadge: HTMLElement;
  private readonly controls: HTMLElement;
  private readonly modeHint: HTMLElement;
  private readonly filterHint: HTMLElement;
  private lastSummaryKey = "";

  constructor(
    private readonly state: AppState,
    private readonly callbacks: SearchPanelCallbacks,
  ) {
    const id = `tm-search-${(panelSequence += 1)}`;

    this.element = document.createElement("form");
    this.element.className = "tm-search";
    this.element.setAttribute("role", "search");
    (this.element as HTMLFormElement).noValidate = true;

    this.input = document.createElement("input");
    this.input.type = "search";
    this.input.className = "tm-search-input";
    this.input.placeholder = "Search ideas, titles or authors…";
    this.input.setAttribute("aria-label", "Search query");
    this.input.setAttribute("aria-keyshortcuts", "/");
    this.input.autocomplete = "off";
    this.input.enterKeyHint = "search";

    this.spinner = document.createElement("span");
    this.spinner.className = "tm-spinner";
    this.spinner.hidden = true;
    this.spinner.setAttribute("aria-hidden", "true");

    const shortcut = document.createElement("kbd");
    shortcut.className = "tm-search-shortcut";
    shortcut.textContent = "/";
    shortcut.title = "Press / to search";
    shortcut.setAttribute("aria-hidden", "true");

    const field = document.createElement("div");
    field.className = "tm-search-field";
    field.append(this.input, this.spinner, shortcut);

    this.button = document.createElement("button");
    this.button.type = "submit";
    this.button.className = "tm-search-button";
    this.button.textContent = "Search";

    this.optionsToggle = document.createElement("button");
    this.optionsToggle.type = "button";
    this.optionsToggle.className = "tm-options-toggle";
    this.optionsToggle.setAttribute("aria-expanded", "false");
    this.optionsToggle.setAttribute("aria-controls", `${id}-options`);

    const optionsLabel = document.createElement("span");
    optionsLabel.className = "tm-options-label";
    optionsLabel.textContent = "Options";

    this.optionsSummary = document.createElement("span");
    this.optionsSummary.className = "tm-options-summary";

    this.optionsBadge = document.createElement("span");
    this.optionsBadge.className = "tm-options-badge";
    this.optionsBadge.hidden = true;

    this.optionsToggle.append(optionsLabel, this.optionsSummary, this.optionsBadge);

    const row = document.createElement("div");
    row.className = "tm-search-row";
    row.append(field, this.button, this.optionsToggle);

    this.modeSelect = buildSelect("Mode", MODE_OPTIONS.map(toOption));
    this.sourceSelect = buildSelect("Source", SOURCE_OPTIONS);
    this.filterSelect = buildSelect("Filter", FILTER_OPTIONS);
    this.topSelect = buildSelect(
      "Results",
      TOP_OPTIONS.map((count) => ({ value: String(count), label: `Top ${count}` })),
    );

    this.modeHint = hint();
    this.filterHint = hint();
    const sourceHint = hint(SOURCE_DESCRIPTION);
    const topHint = hint(TOP_DESCRIPTION);

    this.controls = document.createElement("div");
    this.controls.className = "tm-search-controls";
    this.controls.id = `${id}-options`;
    this.controls.hidden = true;
    this.controls.append(
      labelled("Mode", this.modeSelect, this.modeHint, `${id}-mode-hint`),
      labelled("Source", this.sourceSelect, sourceHint, `${id}-source-hint`),
      labelled("Filter", this.filterSelect, this.filterHint, `${id}-filter-hint`),
      labelled("Results", this.topSelect, topHint, `${id}-top-hint`),
    );

    this.element.append(row, this.controls);
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

    this.optionsToggle.addEventListener("click", () => this.setOptionsOpen(this.controls.hidden));

    // Escape inside the options closes them and returns focus to the toggle,
    // the way a disclosure is expected to behave.
    this.controls.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        this.setOptionsOpen(false);
        this.optionsToggle.focus();
      }
    });
  }

  /** Show or hide the search options. */
  setOptionsOpen(open: boolean): void {
    this.controls.hidden = !open;
    this.optionsToggle.setAttribute("aria-expanded", String(open));
    this.element.classList.toggle("has-options-open", open);
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

    this.renderSummary(snapshot);

    const searching = snapshot.status === "searching";
    this.button.disabled = searching;
    this.button.textContent = searching ? "Searching…" : "Search";
    this.spinner.hidden = !searching;
    this.element.classList.toggle("is-searching", searching);
  }

  /** The collapsed Options button says what is in effect. */
  private renderSummary(snapshot: AppStateSnapshot): void {
    const key = `${snapshot.mode}|${snapshot.source}|${snapshot.filter}|${snapshot.top}`;
    if (key === this.lastSummaryKey) {
      return;
    }
    this.lastSummaryKey = key;

    const parts = [optionLabel(MODE_OPTIONS.map(toOption), snapshot.mode)];
    let changed = 0;
    if (snapshot.source !== DEFAULT_SOURCE) {
      parts.push(optionLabel(SOURCE_OPTIONS, snapshot.source));
      changed += 1;
    }
    if (snapshot.filter !== DEFAULT_FILTER) {
      parts.push(optionLabel(FILTER_OPTIONS, snapshot.filter));
      changed += 1;
    }
    parts.push(`Top ${snapshot.top}`);
    if (snapshot.top !== DEFAULT_TOP) {
      changed += 1;
    }

    this.optionsSummary.textContent = parts.join(" · ");
    this.optionsBadge.hidden = changed === 0;
    this.optionsBadge.textContent = String(changed);
    this.optionsToggle.title = `Search options: ${parts.join(", ")}`;
    this.optionsToggle.classList.toggle("is-narrowed", changed > 0);

    this.modeHint.textContent = MODE_DESCRIPTIONS[snapshot.mode];
    this.filterHint.textContent = describeFilter(snapshot.filter);
  }

  focus(): void {
    this.input.focus();
  }

  /** Focus and select the query, ready to be replaced. */
  focusAndSelect(): void {
    this.input.focus();
    this.input.select();
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

function hint(text = ""): HTMLElement {
  const element = document.createElement("span");
  element.className = "tm-field-hint";
  element.textContent = text;
  return element;
}

function labelled(text: string, control: HTMLElement, help: HTMLElement, helpId: string): HTMLElement {
  // The hint is announced with the control, not just shown beside it.
  help.id = helpId;
  control.setAttribute("aria-describedby", helpId);

  const wrapper = document.createElement("label");
  wrapper.className = "tm-field";

  const caption = document.createElement("span");
  caption.className = "tm-field-label";
  caption.textContent = text;

  wrapper.append(caption, control, help);
  return wrapper;
}
