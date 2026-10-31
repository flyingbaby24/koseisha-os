import type { AppStateSnapshot, SavePhase } from "../app/AppState";
import type { SelectedDocumentView } from "../app/DocumentSelectionResolver";
import { mapMembership } from "../app/mapMembership";
import { sourceStyle } from "../config/sourceStyles";
import { formatSimilarity, orDash } from "./format";
import { ParameterRadar } from "./ParameterRadar";
import { cssColor } from "./ResultPanel";

export interface DetailPanelCallbacks {
  /** Bring the selected document back into view in the map. */
  onLocate?: (docId: string) => void;
  /** Leave the detail view (narrow layouts show one panel at a time). */
  onBack?: () => void;
  /** Take the reader to where a Library ID is entered. */
  onRequestLibrary?: () => void;
}

/** How long "Saved to your Library" stays before it gives way. */
const FEEDBACK_MS = 2600;

/**
 * The selected document, plus the query profile.
 *
 * Reads selection from the shared state snapshot; it never tracks its own.
 *
 * Search failures are reported in the results list, beside the action that
 * caused them; this panel is about one document and keeps showing it.
 */
export class DetailPanel {
  readonly element: HTMLElement;

  private readonly emptyNote: HTMLElement;
  private readonly body: HTMLElement;
  private readonly title: HTMLElement;
  private readonly badges: HTMLElement;
  private readonly sourceBadge: HTMLElement;
  private readonly mapBadge: HTMLElement;
  private readonly savedBadge: HTMLElement;
  private readonly author: HTMLElement;
  private readonly source: HTMLElement;
  private readonly similarity: HTMLElement;
  private readonly docId: HTMLElement;
  private readonly link: HTMLAnchorElement;
  private readonly linkUnavailable: HTMLElement;
  private readonly originNote: HTMLElement;
  private readonly radar: ParameterRadar;
  private readonly saveButton: HTMLButtonElement;
  private readonly locateButton: HTMLButtonElement;
  private readonly saveNote: HTMLElement;
  private readonly saveError: HTMLElement;
  private readonly libraryPrompt: HTMLElement;

  private callbacks: DetailPanelCallbacks;
  private lastSavePhase: SavePhase = "idle";
  private lastSavePhaseDocId: string | null = null;
  private feedbackTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(callbacks: DetailPanelCallbacks = {}) {
    this.callbacks = callbacks;

    this.element = document.createElement("section");
    this.element.className = "tm-panel tm-detail";
    this.element.setAttribute("aria-label", "Selected document");

    const head = document.createElement("div");
    head.className = "tm-detail-head";

    // Only shown where the list and the detail share one panel slot.
    const back = document.createElement("button");
    back.type = "button";
    back.className = "tm-detail-back";
    back.textContent = "Results";
    back.setAttribute("aria-label", "Back to the list");
    back.addEventListener("click", () => this.callbacks.onBack?.());

    const heading = document.createElement("h2");
    heading.className = "tm-panel-title";
    heading.textContent = "Selected document";

    head.append(back, heading);

    this.emptyNote = document.createElement("p");
    this.emptyNote.className = "tm-note tm-detail-empty";
    this.emptyNote.textContent =
      "Select a result, a saved work, or a point in the map to read its details.";

    this.title = document.createElement("h3");
    this.title.className = "tm-detail-title";

    this.sourceBadge = badge("tm-badge is-source");
    this.mapBadge = badge("tm-badge is-map");
    this.savedBadge = badge("tm-badge is-saved");
    this.savedBadge.textContent = "In your Library";
    this.badges = document.createElement("div");
    this.badges.className = "tm-detail-badges";
    this.badges.append(this.sourceBadge, this.mapBadge, this.savedBadge);

    this.author = createField("Author");
    this.source = createField("Source");
    this.similarity = createField("Similarity");
    this.docId = createField("Document ID");
    this.docId.classList.add("is-id");

    const fields = document.createElement("dl");
    fields.className = "tm-detail-fields";
    fields.append(this.author, this.source, this.similarity, this.docId);

    this.link = document.createElement("a");
    this.link.className = "tm-link-button";
    this.link.textContent = "Open source";
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

    this.locateButton = document.createElement("button");
    this.locateButton.type = "button";
    this.locateButton.className = "tm-locate-button";
    this.locateButton.textContent = "Show in map";
    this.locateButton.addEventListener("click", () => {
      const docId = this.locateButton.dataset["docId"];
      if (docId) {
        this.callbacks.onLocate?.(docId);
      }
    });

    const actions = document.createElement("div");
    actions.className = "tm-detail-actions";
    actions.append(this.saveButton, this.locateButton, this.link, this.linkUnavailable);

    this.saveNote = document.createElement("p");
    this.saveNote.className = "tm-save-note";
    this.saveNote.setAttribute("role", "status");
    this.saveNote.hidden = true;

    // A failed save would otherwise only be reported in the Library tab, which
    // may not be the one on screen.
    this.saveError = document.createElement("p");
    this.saveError.className = "tm-inline-error";
    this.saveError.hidden = true;

    this.libraryPrompt = document.createElement("p");
    this.libraryPrompt.className = "tm-library-prompt";
    this.libraryPrompt.hidden = true;
    const promptButton = document.createElement("button");
    promptButton.type = "button";
    promptButton.className = "tm-text-button";
    promptButton.textContent = "Set a Library ID";
    promptButton.addEventListener("click", () => this.callbacks.onRequestLibrary?.());
    this.libraryPrompt.append(promptButton, " to save documents.");

    this.originNote = document.createElement("p");
    this.originNote.className = "tm-note tm-detail-origin";
    this.originNote.textContent =
      "Selected from the thought space. Search this document to see its similarity and profile.";
    this.originNote.hidden = true;

    this.body = document.createElement("div");
    this.body.className = "tm-detail-body";
    this.body.append(
      this.title,
      this.badges,
      actions,
      this.saveNote,
      this.saveError,
      this.libraryPrompt,
      fields,
      this.originNote,
    );

    this.element.append(head, this.emptyNote, this.body, this.radar.element);
  }

  /** Register panel callbacks after construction. */
  setCallbacks(callbacks: DetailPanelCallbacks): void {
    this.callbacks = { ...this.callbacks, ...callbacks };
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
    // Query and document share one radar and one scale.
    this.radar.render([
      { label: "Query", scores: snapshot.queryParameters, variant: "query" },
      {
        label: selected ? shortLabel(selected.title) : "Document",
        scores: selected?.parameters ?? null,
        variant: "document",
      },
    ]);

    this.element.classList.toggle("has-selection", selected !== null);

    if (!selected) {
      this.emptyNote.hidden = false;
      this.body.hidden = true;
      this.trackSavePhase(snapshot, null);
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

    this.renderBadges(snapshot, selected);
    this.renderLink(selected.url ?? undefined);
    this.renderSaveAction(snapshot, selected);
    this.trackSavePhase(snapshot, selected);
  }

  private renderBadges(snapshot: AppStateSnapshot, selected: SelectedDocumentView): void {
    const style = sourceStyle(selected.source);
    this.sourceBadge.textContent = style.label;
    this.sourceBadge.style.setProperty("--tm-dot", cssColor(style.color));

    const membership = mapMembership(snapshot);
    const inMap = membership?.has(selected.doc_id) ?? false;
    this.mapBadge.hidden = membership === null;
    this.mapBadge.textContent = inMap ? "In map" : "Not in map";
    this.mapBadge.classList.toggle("is-missing", !inMap);
    this.mapBadge.title = inMap
      ? "This document has a position in the 3D thought space."
      : "This document has no position in the current projection.";

    this.locateButton.dataset["docId"] = selected.doc_id;
    this.locateButton.disabled = !inMap;
    this.locateButton.title = inMap
      ? "Centre the map on this document"
      : "This document has no position in the map";

    this.savedBadge.hidden = !snapshot.savedDocIds.has(selected.doc_id);
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
      this.saveError.hidden = true;
      this.libraryPrompt.hidden = true;
      return;
    }
    this.saveButton.hidden = false;

    const hasIdentity = snapshot.libraryIdentity !== "";
    this.saveError.hidden = !(hasIdentity && snapshot.libraryError);
    this.saveError.textContent = hasIdentity ? (snapshot.libraryError ?? "") : "";
    const saved = snapshot.savedDocIds.has(selected.doc_id);
    const busy =
      snapshot.savePhaseDocId === selected.doc_id && snapshot.savePhase !== "idle";

    this.saveButton.dataset["docId"] = selected.doc_id;
    this.saveButton.dataset["saved"] = String(saved);
    this.saveButton.disabled = !hasIdentity || busy;
    this.saveButton.classList.toggle("is-saved", saved);
    this.saveButton.classList.toggle("is-busy", busy);
    this.saveButton.setAttribute("aria-pressed", String(saved));

    if (busy) {
      this.saveButton.textContent =
        snapshot.savePhase === "saving" ? "Saving…" : "Removing…";
    } else if (saved) {
      this.saveButton.textContent = "Saved";
      this.saveButton.title = "Saved — select to remove from your Personal Library";
    } else {
      this.saveButton.textContent = "Save";
      this.saveButton.title = "Save to your Personal Library";
    }

    this.libraryPrompt.hidden = hasIdentity;
  }

  /**
   * Confirm a finished save or removal in words.
   *
   * The button flipping to "Saved" is easy to miss and says nothing to a
   * screen reader; a short status line does both, then gets out of the way.
   */
  private trackSavePhase(snapshot: AppStateSnapshot, selected: SelectedDocumentView | null): void {
    const finished =
      this.lastSavePhase !== "idle" &&
      snapshot.savePhase === "idle" &&
      this.lastSavePhaseDocId !== null;

    if (finished && selected && this.lastSavePhaseDocId === selected.doc_id) {
      const saved = snapshot.savedDocIds.has(selected.doc_id);
      if (this.lastSavePhase === "saving" && saved) {
        this.flash("Saved to your Library. It is marked with a mint ring in the map.");
      } else if (this.lastSavePhase === "removing" && !saved) {
        this.flash("Removed from your Library.");
      }
    }

    this.lastSavePhase = snapshot.savePhase;
    this.lastSavePhaseDocId = snapshot.savePhaseDocId ?? this.lastSavePhaseDocId;
    if (snapshot.savePhase === "idle") {
      this.lastSavePhaseDocId = null;
    }
  }

  private flash(message: string): void {
    if (this.feedbackTimer !== null) {
      clearTimeout(this.feedbackTimer);
    }
    this.saveNote.textContent = message;
    this.saveNote.hidden = false;
    this.feedbackTimer = setTimeout(() => {
      this.feedbackTimer = null;
      this.saveNote.hidden = true;
      this.saveNote.textContent = "";
    }, FEEDBACK_MS);
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

function badge(className: string): HTMLElement {
  const element = document.createElement("span");
  element.className = className;
  return element;
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
