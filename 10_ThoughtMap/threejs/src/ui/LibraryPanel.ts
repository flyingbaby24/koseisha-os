import type { SavedDocument } from "../api/libraryTypes";
import type { AppStateSnapshot } from "../app/AppState";
import { formatCount, orDash } from "./format";

export interface LibraryPanelCallbacks {
  onSetIdentity: (identity: string) => void;
  onClearIdentity: () => void;
  onSelect: (docId: string) => void;
  onRemove: (docId: string) => void;
  onReload: () => void;
}

/**
 * The Personal Library, as a tab beside the search results.
 *
 * Deliberately a tab rather than a separate screen: the Search / Collect
 * boundary is fixed, and collecting is part of it. Nothing here belongs to
 * Battle Prep.
 */
export class LibraryPanel {
  readonly element: HTMLElement;

  private readonly identityInput: HTMLInputElement;
  private readonly identityForm: HTMLFormElement;
  private readonly identityNote: HTMLElement;
  private readonly clearButton: HTMLButtonElement;
  private readonly reloadButton: HTMLButtonElement;
  private readonly status: HTMLElement;
  private readonly errorBox: HTMLElement;
  private readonly list: HTMLElement;

  private renderedWorks: readonly SavedDocument[] | null = null;
  private readonly rows = new Map<string, HTMLElement>();

  constructor(private readonly callbacks: LibraryPanelCallbacks) {
    this.element = document.createElement("div");
    this.element.className = "tm-library";

    // --- identity ---------------------------------------------------------
    this.identityForm = document.createElement("form");
    this.identityForm.className = "tm-library-identity";
    this.identityForm.noValidate = true;

    this.identityInput = document.createElement("input");
    this.identityInput.type = "text";
    this.identityInput.className = "tm-library-identity-input";
    // Honest wording: this is a lookup key, not a login. The backend performs
    // no authentication, so the UI must not imply otherwise.
    this.identityInput.placeholder = "Personal Library ID / email";
    this.identityInput.setAttribute("aria-label", "Personal Library ID");
    this.identityInput.autocomplete = "off";

    const setButton = document.createElement("button");
    setButton.type = "submit";
    setButton.className = "tm-library-button";
    setButton.textContent = "Use";

    this.clearButton = document.createElement("button");
    this.clearButton.type = "button";
    this.clearButton.className = "tm-library-button is-quiet";
    this.clearButton.textContent = "Change";

    this.reloadButton = document.createElement("button");
    this.reloadButton.type = "button";
    this.reloadButton.className = "tm-library-button is-quiet";
    this.reloadButton.textContent = "Reload";

    this.identityForm.append(this.identityInput, setButton, this.clearButton, this.reloadButton);

    this.identityNote = document.createElement("p");
    this.identityNote.className = "tm-note tm-library-identity-note";
    this.identityNote.textContent =
      "An ID to find your library. Not a sign-in — no password, no account.";

    this.errorBox = document.createElement("p");
    this.errorBox.className = "tm-error";
    this.errorBox.hidden = true;
    this.errorBox.setAttribute("role", "alert");

    this.status = document.createElement("p");
    this.status.className = "tm-note";

    this.list = document.createElement("ul");
    this.list.className = "tm-library-list";
    this.list.setAttribute("role", "listbox");
    this.list.setAttribute("aria-label", "Saved works");

    this.element.append(
      this.identityForm,
      this.identityNote,
      this.errorBox,
      this.status,
      this.list,
    );

    this.bind();
  }

  private bind(): void {
    this.identityForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const value = this.identityInput.value.trim();
      if (value) {
        this.callbacks.onSetIdentity(value);
      }
    });

    this.clearButton.addEventListener("click", () => this.callbacks.onClearIdentity());
    this.reloadButton.addEventListener("click", () => this.callbacks.onReload());
  }

  render(snapshot: AppStateSnapshot): void {
    const hasIdentity = snapshot.libraryIdentity !== "";

    if (this.identityInput.value !== snapshot.libraryIdentity && document.activeElement !== this.identityInput) {
      this.identityInput.value = snapshot.libraryIdentity;
    }
    this.clearButton.hidden = !hasIdentity;
    this.reloadButton.hidden = !hasIdentity;

    // A library error is shown here and only here; search and the map are
    // unaffected by it.
    if (snapshot.libraryError) {
      this.errorBox.hidden = false;
      this.errorBox.textContent = snapshot.libraryError;
    } else {
      this.errorBox.hidden = true;
      this.errorBox.textContent = "";
    }

    if (!hasIdentity) {
      this.status.textContent = "Enter an ID to load your saved works.";
      this.list.hidden = true;
      return;
    }

    if (snapshot.libraryStatus === "loading" && snapshot.savedWorks.length === 0) {
      this.status.textContent = "Loading saved works…";
      this.list.hidden = true;
      return;
    }

    if (snapshot.savedWorks.length === 0) {
      this.status.textContent =
        snapshot.libraryStatus === "error"
          ? "Could not load your library."
          : "No saved works yet. Select a document and choose Save.";
      this.list.hidden = true;
      return;
    }

    this.status.textContent = formatCount(snapshot.savedWorks.length, "saved work");
    this.list.hidden = false;

    if (snapshot.savedWorks !== this.renderedWorks) {
      this.renderedWorks = snapshot.savedWorks;
      this.rows.clear();
      this.list.replaceChildren(
        ...snapshot.savedWorks.map((work) => this.buildRow(work, snapshot)),
      );
    }

    for (const [docId, row] of this.rows) {
      const selected = docId === snapshot.selectedDocId;
      row.classList.toggle("is-selected", selected);
      row.setAttribute("aria-selected", String(selected));
    }
  }

  private buildRow(work: SavedDocument, snapshot: AppStateSnapshot): HTMLElement {
    const row = document.createElement("li");
    row.className = "tm-library-item";
    row.setAttribute("role", "option");
    row.dataset["docId"] = work.doc_id;

    const main = document.createElement("button");
    main.type = "button";
    main.className = "tm-library-item-main";

    const title = document.createElement("span");
    title.className = "tm-library-item-title";
    title.textContent = orDash(work.title);

    const meta = document.createElement("span");
    meta.className = "tm-library-item-meta";
    const parts = [orDash(work.author), orDash(work.source)];
    const savedAt = formatSavedAt(work.saved_at);
    if (savedAt) {
      parts.push(savedAt);
    }
    meta.textContent = parts.join(" · ");

    main.append(title, meta);
    // Same selection path as a search result or a map node.
    main.addEventListener("click", () => this.callbacks.onSelect(work.doc_id));

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "tm-library-remove";
    remove.title = "Remove from Personal Library";
    remove.setAttribute("aria-label", `Remove ${work.title || work.doc_id} from your library`);
    remove.textContent =
      snapshot.savePhase === "removing" && snapshot.savePhaseDocId === work.doc_id ? "…" : "✕";
    remove.addEventListener("click", (event) => {
      event.stopPropagation();
      this.callbacks.onRemove(work.doc_id);
    });

    row.append(main, remove);
    this.rows.set(work.doc_id, row);
    return row;
  }
}

/** `2026-09-10T…` → `2026-09-10`, or empty when absent or unparseable. */
export function formatSavedAt(value: string | undefined | null): string {
  const text = (value ?? "").trim();
  if (!text) {
    return "";
  }
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  return parsed.toISOString().slice(0, 10);
}
