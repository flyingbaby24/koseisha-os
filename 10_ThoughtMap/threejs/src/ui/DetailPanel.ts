import type { AppStateSnapshot } from "../app/AppState";
import type { SelectedDocumentView } from "../app/DocumentSelectionResolver";
import { formatSimilarity, orDash } from "./format";
import { ParameterRadar } from "./ParameterRadar";

/**
 * The selected document, plus the query profile.
 *
 * Reads selection from the shared state snapshot; it never tracks its own.
 */
export class DetailPanel {
  readonly element: HTMLElement;

  private readonly errorBox: HTMLElement;
  private readonly emptyNote: HTMLElement;
  private readonly body: HTMLElement;
  private readonly title: HTMLElement;
  private readonly author: HTMLElement;
  private readonly source: HTMLElement;
  private readonly similarity: HTMLElement;
  private readonly docId: HTMLElement;
  private readonly link: HTMLAnchorElement;
  private readonly linkUnavailable: HTMLElement;
  private readonly originNote: HTMLElement;
  private readonly radar: ParameterRadar;
  private readonly saveButton: HTMLButtonElement;
  private readonly saveNote: HTMLElement;

  constructor() {
    this.element = document.createElement("section");
    this.element.className = "tm-panel tm-detail";

    const heading = document.createElement("h2");
    heading.className = "tm-panel-title";
    heading.textContent = "Detail";

    this.errorBox = document.createElement("p");
    this.errorBox.className = "tm-error";
    this.errorBox.hidden = true;
    this.errorBox.setAttribute("role", "alert");

    this.emptyNote = document.createElement("p");
    this.emptyNote.className = "tm-note";
    this.emptyNote.textContent = "Select a result to see its detail.";

    this.title = document.createElement("h3");
    this.title.className = "tm-detail-title";

    this.author = createField("Author");
    this.source = createField("Source");
    this.similarity = createField("Similarity");
    this.docId = createField("Document ID");

    const fields = document.createElement("dl");
    fields.className = "tm-detail-fields";
    fields.append(this.author, this.source, this.similarity, this.docId);

    this.link = document.createElement("a");
    this.link.className = "tm-link-button";
    this.link.textContent = "Open Link";
    // Opening an external document must not give the target page a handle on
    // this window, and must not leak the artifact URL as a referrer.
    this.link.target = "_blank";
    this.link.rel = "noopener noreferrer nofollow";

    this.linkUnavailable = document.createElement("span");
    this.linkUnavailable.className = "tm-link-unavailable";
    this.linkUnavailable.textContent = "No source link available";

    // One radar showing both profiles on a shared scale, so the reader can see
    // where the document agrees with and diverges from the search intent.
    this.radar = new ParameterRadar("Thought Composition");

    this.saveButton = document.createElement("button");
    this.saveButton.type = "button";
    this.saveButton.className = "tm-save-button";
    this.saveButton.textContent = "Save";

    this.saveNote = document.createElement("span");
    this.saveNote.className = "tm-save-note";
    this.saveNote.hidden = true;

    const actions = document.createElement("div");
    actions.className = "tm-detail-actions";
    actions.append(this.saveButton, this.saveNote, this.link, this.linkUnavailable);


    this.originNote = document.createElement("p");
    this.originNote.className = "tm-note tm-detail-origin";
    this.originNote.textContent =
      "Selected from the thought space. Search this document to see its similarity and profile.";
    this.originNote.hidden = true;

    this.body = document.createElement("div");
    this.body.className = "tm-detail-body";
    this.body.append(this.title, fields, this.originNote, actions);

    this.element.append(heading, this.errorBox, this.emptyNote, this.body, this.radar.element);
  }

  /** Register the Save/Remove handler. The panel never calls the API itself. */
  onSaveToggle(handler: (docId: string, currentlySaved: boolean) => void): void {
    this.saveButton.addEventListener("click", () => {
      const docId = this.saveButton.dataset["docId"];
      if (docId) {
        handler(docId, this.saveButton.dataset["saved"] === "true");
      }
    });
  }

  render(snapshot: AppStateSnapshot, selected: SelectedDocumentView | null): void {
    if (snapshot.status === "error" && snapshot.error) {
      this.errorBox.hidden = false;
      this.errorBox.textContent = snapshot.error;
    } else {
      this.errorBox.hidden = true;
      this.errorBox.textContent = "";
    }

    // Query and document share one radar and one scale.
    this.radar.render([
      { label: "Query", scores: snapshot.queryParameters, variant: "query" },
      {
        label: selected ? shortLabel(selected.title) : "Document",
        scores: selected?.parameters ?? null,
        variant: "document",
      },
    ]);

    if (!selected) {
      this.emptyNote.hidden = snapshot.status === "error";
      this.body.hidden = true;
      return;
    }

    this.emptyNote.hidden = true;
    this.body.hidden = false;

    this.title.textContent = orDash(selected.title);
    setFieldValue(this.author, orDash(selected.author));
    setFieldValue(this.source, orDash(selected.source));
    setFieldValue(this.docId, orDash(selected.doc_id));

    // A document selected from the map has no similarity. Saying so is honest;
    // rendering 0.0000 would claim it is maximally dissimilar.
    setFieldValue(
      this.similarity,
      selected.similarity === null ? "Not in current results" : formatSimilarity(selected.similarity),
    );

    this.originNote.hidden = selected.origin !== "map";

    this.renderLink(selected.url ?? undefined);
    this.renderSaveAction(snapshot, selected);
  }

  /**
   * Save / Saved / Saving, driven by confirmed server state.
   *
   * A duplicate save is not an error — the document is in the library either
   * way — so it lands in exactly the same "Saved" state as a fresh save.
   */
  private renderSaveAction(snapshot: AppStateSnapshot, selected: SelectedDocumentView): void {
    // A deployment without a Personal Library has no Save control, rather than
    // a disabled one. A greyed-out button invites people to work out how to
    // enable it; there is nothing to enable (T6 #23).
    if (!snapshot.features.library_enabled) {
      this.saveButton.hidden = true;
      this.saveNote.hidden = true;
      return;
    }
    this.saveButton.hidden = false;

    const hasIdentity = snapshot.libraryIdentity !== "";
    const saved = snapshot.savedDocIds.has(selected.doc_id);
    const busy =
      snapshot.savePhaseDocId === selected.doc_id && snapshot.savePhase !== "idle";

    this.saveButton.dataset["docId"] = selected.doc_id;
    this.saveButton.dataset["saved"] = String(saved);
    this.saveButton.disabled = !hasIdentity || busy;
    this.saveButton.classList.toggle("is-saved", saved);

    if (busy) {
      this.saveButton.textContent =
        snapshot.savePhase === "saving" ? "Saving…" : "Removing…";
    } else if (saved) {
      this.saveButton.textContent = "Saved";
      this.saveButton.title = "Remove from your Personal Library";
    } else {
      this.saveButton.textContent = "Save";
      this.saveButton.title = "Save to your Personal Library";
    }

    this.saveNote.hidden = hasIdentity;
    this.saveNote.textContent = hasIdentity ? "" : "Set a Library ID to save";
  }

  /** A missing URL shows an explicit unavailable note, never a dead button. */
  private renderLink(url: string | undefined): void {
    const href = (url ?? "").trim();

    if (!href || !isSafeExternalUrl(href)) {
      this.link.hidden = true;
      this.link.removeAttribute("href");
      this.linkUnavailable.hidden = false;
      return;
    }

    this.link.hidden = false;
    this.link.href = href;
    this.linkUnavailable.hidden = true;
  }
}

/** Only http/https may be turned into a clickable link. */
export function isSafeExternalUrl(value: string): boolean {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function createField(label: string): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "tm-detail-field";

  const term = document.createElement("dt");
  term.textContent = label;

  const value = document.createElement("dd");
  value.textContent = "—";

  wrapper.append(term, value);
  return wrapper;
}

function setFieldValue(field: HTMLElement, value: string): void {
  const target = field.querySelector("dd");
  if (target) {
    target.textContent = value;
  }
}


/** Keep the radar legend readable for very long titles. */
function shortLabel(title: string): string {
  const text = (title ?? "").trim() || "Document";
  return text.length > 28 ? `${text.slice(0, 27)}…` : text;
}
