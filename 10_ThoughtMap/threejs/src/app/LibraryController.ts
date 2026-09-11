import { ApiError } from "../api/errors";
import type { PersonalLibraryClient } from "../api/PersonalLibraryClient";
import type { SaveDocumentRequest, SavedDocument } from "../api/libraryTypes";
import type { AppState } from "./AppState";
import type { SelectedDocumentView } from "./DocumentSelectionResolver";

/** Where the identity is remembered between page loads. */
const IDENTITY_STORAGE_KEY = "thoughtmap.library.identity";

/**
 * Personal Library operations against shared state.
 *
 * Kept apart from search and map for the same reason their controllers are
 * separate: the Personal database failing must not disturb either. Every
 * failure here lands in `libraryError` and nowhere else.
 *
 * Save and delete are **confirmed, not optimistic**. A document is only marked
 * saved once the server says so, so the map can never show a saved ring for
 * something that was never persisted.
 */
export class LibraryController {
  private inFlight: AbortController | null = null;

  constructor(
    private readonly state: AppState,
    private readonly client: PersonalLibraryClient,
  ) {}

  /** Restore a remembered identity, if the browser has one. */
  restoreIdentity(): string {
    let stored = "";
    try {
      stored = window.localStorage.getItem(IDENTITY_STORAGE_KEY) ?? "";
    } catch {
      // Private mode or blocked storage. Not an error; the user types it again.
      stored = "";
    }

    if (stored) {
      this.state.setLibraryIdentity(stored);
    }
    return stored;
  }

  /**
   * Set the library identity and remember it.
   *
   * This is a lookup key, not a credential, so `localStorage` is appropriate —
   * there is no secret here to protect.
   */
  setIdentity(identity: string): void {
    const value = String(identity ?? "").trim();
    this.state.setLibraryIdentity(value);

    try {
      if (value) {
        window.localStorage.setItem(IDENTITY_STORAGE_KEY, value);
      } else {
        window.localStorage.removeItem(IDENTITY_STORAGE_KEY);
      }
    } catch {
      // Nothing to do; the identity still works for this session.
    }
  }

  clearIdentity(): void {
    this.setIdentity("");
  }

  /** Load the saved works for the current identity. Never rejects. */
  async load(): Promise<void> {
    const identity = this.state.getState().libraryIdentity;
    if (!identity) {
      return;
    }

    this.inFlight?.abort();
    const controller = new AbortController();
    this.inFlight = controller;

    this.state.libraryLoading();

    try {
      const works = await this.client.loadSaved(identity, { signal: controller.signal });
      this.state.libraryLoaded(works);
    } catch (error) {
      if (error instanceof ApiError && error.isAborted) {
        return;
      }
      console.error("[ThoughtMap] library load failed", error);
      this.state.libraryFailed(this.messageFor(error, "The Personal Library could not be loaded."));
    } finally {
      if (this.inFlight === controller) {
        this.inFlight = null;
      }
    }
  }

  /**
   * Save the selected document. Never rejects.
   *
   * A duplicate is a success, not an error: the document is in the library
   * either way, which is all the user asked for.
   */
  async save(document: SelectedDocumentView): Promise<boolean> {
    const identity = this.state.getState().libraryIdentity;
    if (!identity) {
      this.state.libraryFailed("Set a Personal Library ID before saving.");
      return false;
    }

    this.state.setSavePhase("saving", document.doc_id);

    const request: SaveDocumentRequest = {
      email: identity,
      // The canonical id is preserved exactly; nothing is generated here.
      doc_id: document.doc_id,
      title: document.title,
      author: document.author,
      source: document.source,
      original_doc_id: document.doc_id,
      url: document.url ?? "",
      source_url: document.url ?? "",
      parameters: document.parameters ? [...document.parameters] : null,
    };

    try {
      const response = await this.client.saveDocument(request);
      const saved: SavedDocument = response.item ?? {
        doc_id: document.doc_id,
        title: document.title,
        author: document.author,
        source: document.source,
      };
      this.state.documentSaved(saved);
      this.state.clearLibraryError();
      return true;
    } catch (error) {
      console.error("[ThoughtMap] save failed", error);
      this.state.setSavePhase("idle", null);
      this.state.libraryFailed(this.messageFor(error, "That document could not be saved."));
      return false;
    }
  }

  /**
   * Remove a document from the library. Never rejects.
   *
   * This removes library membership only. The document remains in the canonical
   * corpus, searchable and present in the map.
   */
  async remove(docId: string): Promise<boolean> {
    const identity = this.state.getState().libraryIdentity;
    if (!identity) {
      return false;
    }

    this.state.setSavePhase("removing", docId);

    try {
      await this.client.deleteSaved(identity, docId);
      this.state.documentRemoved(docId);
      this.state.clearLibraryError();
      return true;
    } catch (error) {
      console.error("[ThoughtMap] delete failed", error);
      this.state.setSavePhase("idle", null);
      this.state.libraryFailed(this.messageFor(error, "That document could not be removed."));
      return false;
    }
  }

  cancel(): void {
    this.inFlight?.abort();
    this.inFlight = null;
  }

  private messageFor(error: unknown, fallback: string): string {
    return error instanceof ApiError ? error.message : fallback;
  }
}

export { IDENTITY_STORAGE_KEY };
