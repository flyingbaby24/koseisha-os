import type { SavedDocument } from "../api/libraryTypes";
import type { AppStateSnapshot } from "../app/AppState";
import { mapMembership } from "../app/mapMembership";
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

  private readonly intro: HTMLElement;
  private readonly identityInput: HTMLInputElement;
  private readonly identityForm: HTMLFormElement;
  private readonly identityNote: HTMLElement;
  private readonly identityBar: HTMLElement;
  private readonly identityValue: HTMLElement;
  private readonly clearButton: HTMLButtonElement;
  private readonly reloadButton: HTMLButtonElement;
  private readonly status: HTMLElement;
  private readonly errorBox: HTMLElement;
  private readonly errorMessage: HTMLElement;
  private readonly emptyState: HTMLElement;
  private readonly skeleton: HTMLElement;
  private readonly list: HTMLElement;

  private renderedWorks: readonly SavedDocument[] | null = null;
  private renderedMembership: ReadonlySet<string> | null = null;
  private readonly rows = new Map<string, HTMLElement>();

  constructor(private readonly callbacks: LibraryPanelCallbacks) {
    this.element = document.createElement("div");
    this.element.className = "tm-library";

    // --- introduction (no identity yet) -----------------------------------
    this.intro = document.createElement("div");
    this.intro.className = "tm-empty is-library";
    const introTitle = document.createElement("p");
    introTitle.className = "tm-empty-title";
    introTitle.textContent = "Your Personal Library";
    const introText = document.createElement("p");
    introText.className = "tm-empty-text";
    introText.textContent =
      "Keep documents to return to. Saved works are marked with a mint ring in the map " +
      "and in the results.";
    this.intro.append(introTitle, introText);

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
    setButton.textContent = "Open";

    this.identityForm.append(this.identityInput, setButton);

    this.identityNote = document.createElement("p");
    this.identityNote.className = "tm-note tm-library-identity-note";
    this.identityNote.textContent =
      "An ID to find your library. Not a sign-in — no password, no account.";

    // Shown instead of the form once an identity is in use.
    this.identityBar = document.createElement("div");
    this.identityBar.className = "tm-library-who";
    const whoLabel = document.createElement("span");
    whoLabel.className = "tm-library-who-label";
    whoLabel.textContent = "Library ID";
    this.identityValue = document.createElement("span");
    this.identityValue.className = "tm-library-who-value";

    this.clearButton = document.createElement("button");
    this.clearButton.type = "button";
    this.clearButton.className = "tm-library-button is-quiet";
    this.clearButton.textContent = "Change";

    this.reloadButton = document.createElement("button");
    this.reloadButton.type = "button";
    this.reloadButton.className = "tm-library-button is-quiet";
    this.reloadButton.textContent = "Reload";

    this.identityBar.append(whoLabel, this.identityValue, this.clearButton, this.reloadButton);

    this.errorBox = document.createElement("div");
    this.errorBox.className = "tm-alert";
    this.errorBox.hidden = true;
    this.errorMessage = document.createElement("p");
    this.errorMessage.className = "tm-error";
    this.errorMessage.setAttribute("role", "alert");
    const retry = document.createElement("button");
    retry.type = "button";
    retry.className = "tm-button is-quiet";
    retry.textContent = "Try again";
    retry.addEventListener("click", () => this.callbacks.onReload());
    this.errorBox.append(this.errorMessage, retry);

    this.status = document.createElement("p");
    this.status.className = "tm-note tm-library-status";
    this.status.setAttribute("role", "status");

    this.emptyState = document.createElement("div");
    this.emptyState.className = "tm-empty";
    const emptyTitle = document.createElement("p");
    emptyTitle.className = "tm-empty-title";
    emptyTitle.textContent = "No saved works yet";
    const emptyText = document.createElement("p");
    emptyText.className = "tm-empty-text";
    emptyText.textContent =
      "Select a result or a point in the map, then choose Save in the document panel.";
    this.emptyState.append(emptyTitle, emptyText);
    this.emptyState.hidden = true;

    this.skeleton = document.createElement("ul");
    this.skeleton.className = "tm-skeleton";
    this.skeleton.setAttribute("aria-hidden", "true");
    for (let index = 0; index < 3; index += 1) {
      const row = document.createElement("li");
      row.append(document.createElement("span"), document.createElement("span"));
      this.skeleton.append(row);
    }
    this.skeleton.hidden = true;

    this.list = document.createElement("ul");
    this.list.className = "tm-library-list";
    this.list.setAttribute("aria-label", "Saved works");

    this.element.append(
      this.intro,
      this.identityForm,
      this.identityNote,
      this.identityBar,
      this.errorBox,
      this.status,
      this.emptyState,
      this.skeleton,
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

    this.clearButton.addEventListener("click", () => {
      this.callbacks.onClearIdentity();
      this.identityInput.focus();
    });
    this.reloadButton.addEventListener("click", () => this.callbacks.onReload());
  }

  /** Put the cursor in the ID field (when the reader was sent here to set one). */
  focusIdentity(): void {
    if (!this.identityForm.hidden) {
      this.identityInput.focus();
    }
  }

  render(snapshot: AppStateSnapshot): void {
    const hasIdentity = snapshot.libraryIdentity !== "";

    if (this.identityInput.value !== snapshot.libraryIdentity && document.activeElement !== this.identityInput) {
      this.identityInput.value = snapshot.libraryIdentity;
    }
    this.intro.hidden = hasIdentity;
    this.identityForm.hidden = hasIdentity;
    this.identityNote.hidden = hasIdentity;
    this.identityBar.hidden = !hasIdentity;
    this.identityValue.textContent = snapshot.libraryIdentity;
    this.identityValue.title = snapshot.libraryIdentity;
    this.clearButton.hidden = !hasIdentity;
    this.reloadButton.hidden = !hasIdentity;
    this.reloadButton.disabled = snapshot.libraryStatus === "loading";

    // A library error is shown here and beside the Save action; search and
    // the map are unaffected by it.
    this.errorBox.hidden = !snapshot.libraryError;
    this.errorMessage.textContent = snapshot.libraryError ?? "";

    const loading = snapshot.libraryStatus === "loading";
    this.skeleton.hidden = !(hasIdentity && loading && snapshot.savedWorks.length === 0);
    this.emptyState.hidden = true;
    this.element.classList.toggle("is-loading", loading);

    if (!hasIdentity) {
      this.status.hidden = true;
      this.status.textContent = "Enter an ID to load your saved works.";
      this.list.hidden = true;
      return;
    }
    this.status.hidden = false;

    if (loading && snapshot.savedWorks.length === 0) {
      this.status.textContent = "Loading saved works…";
      this.list.hidden = true;
      return;
    }

    if (snapshot.savedWorks.length === 0) {
      if (snapshot.libraryStatus === "error") {
        this.status.textContent = "Could not load your library.";
      } else {
        this.status.textContent = "";
        this.status.hidden = true;
        this.emptyState.hidden = false;
      }
      this.list.hidden = true;
      return;
    }

    this.status.textContent = loading
      ? "Refreshing…"
      : `${formatCount(snapshot.savedWorks.length, "saved work")} · select one to find it in the map`;
    this.list.hidden = false;

    const membership = mapMembership(snapshot);
    if (snapshot.savedWorks !== this.renderedWorks || membership !== this.renderedMembership) {
      this.renderedWorks = snapshot.savedWorks;
      this.renderedMembership = membership;
      this.rows.clear();
      this.list.replaceChildren(
        ...snapshot.savedWorks.map((work) => this.buildRow(work, membership)),
      );
    }

    for (const [docId, row] of this.rows) {
      const selected = docId === snapshot.selectedDocId;
      row.classList.toggle("is-selected", selected);
      row.querySelector(".tm-library-item-main")?.setAttribute("aria-current", String(selected));

      const removing = snapshot.savePhase === "removing" && snapshot.savePhaseDocId === docId;
      row.classList.toggle("is-removing", removing);
      const remove = row.querySelector<HTMLButtonElement>(".tm-library-remove");
      if (remove) {
        remove.textContent = removing ? "…" : "✕";
        remove.disabled = removing;
      }
    }
  }

  private buildRow(work: SavedDocument, membership: ReadonlySet<string> | null): HTMLElement {
    const row = document.createElement("li");
    row.className = "tm-library-item";
    row.dataset["docId"] = work.doc_id;

    const inMap = membership?.has(work.doc_id) ?? true;
    row.classList.toggle("is-offmap", !inMap);

    const main = document.createElement("button");
    main.type = "button";
    main.className = "tm-library-item-main";
    main.title = inMap ? "Select and show in the map" : "Select (no position in the map)";

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
    if (!inMap) {
      parts.push("not in map");
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
    remove.textContent = "✕";
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
