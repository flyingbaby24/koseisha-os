import type { SavedDocument } from "../api/libraryTypes";
import { DEFAULT_FEATURES, type DeploymentFeatures } from "../config/runtime";
import type { MapNode, MapProjectionMetadata } from "../api/mapTypes";
import type { ParameterScore, SearchMode, SearchResult } from "../api/types";
import { DEFAULT_FILTER, DEFAULT_MODE, DEFAULT_SOURCE, DEFAULT_TOP } from "../config/searchOptions";

export type SearchStatus = "idle" | "searching" | "success" | "error";
export type MapStatus = "idle" | "loading" | "ready" | "error";
export type LibraryStatus = "idle" | "loading" | "ready" | "error";
/**
 * Whether the backend can serve semantic search yet.
 *
 * "warming" is a real, distinct state, not a flavour of "down": a process that
 * is still loading its model will answer normally in a moment, and telling
 * someone the service is unavailable would be wrong (T6 #37).
 */
export type BackendStatus = "unknown" | "warming" | "ready" | "unavailable";
/** Per-document save progress, so one row can show "Saving…" independently. */
export type SavePhase = "idle" | "saving" | "removing";

export interface AppStateSnapshot {
  // Search form
  readonly query: string;
  readonly mode: SearchMode;
  readonly source: string;
  readonly filter: string;
  readonly top: number;

  // Search outcome
  readonly status: SearchStatus;
  readonly results: readonly SearchResult[];
  readonly queryParameters: readonly ParameterScore[] | null;
  readonly selectedDocId: string | null;
  /**
   * Transient pointer hover. Never selection: it drives node highlight and the
   * tooltip only, and never changes the DetailPanel or moves the camera.
   */
  readonly hoveredDocId: string | null;
  readonly error: string | null;

  /** Query text the current results actually came from. */
  readonly lastQuery: string;

  /**
   * Result doc_ids driving map emphasis, in rank order.
   *
   * Deliberately separate from `results`. The result *list* clears on a failed
   * search — the rows are stale and the panel says so — but the thought space
   * keeps the last successful emphasis, so a transient API error does not wipe
   * the spatial context the user is reading. Replaced only by the next
   * successful search.
   */
  readonly emphasisDocIds: readonly string[];
  /** True once a search has succeeded, so non-results should dim. */
  readonly hasSearchEmphasis: boolean;

  // Thought space. Deliberately independent of the search fields above: a
  // failed search must not discard a loaded map, and a missing map must not
  // stop text search from working.
  readonly mapStatus: MapStatus;
  readonly mapNodes: readonly MapNode[];
  readonly mapMetadata: MapProjectionMetadata | null;
  readonly mapError: string | null;

  // Personal Library. Independent of search and map: the Personal database can
  // be down while both are healthy, and a library error must never take the
  // thought space with it.
  readonly libraryStatus: LibraryStatus;
  /**
   * The Personal Library lookup key. A *key*, not a credential — the backend
   * hashes it to derive a user id and performs no authentication.
   */
  readonly libraryIdentity: string;
  readonly savedWorks: readonly SavedDocument[];
  /** Membership lookup. O(1) per document, rebuilt only when the list changes. */
  readonly savedDocIds: ReadonlySet<string>;
  readonly libraryError: string | null;
  /** doc_id currently being saved or removed, for per-row progress. */
  readonly savePhase: SavePhase;
  readonly savePhaseDocId: string | null;

  // Deployment. What the *server* says it offers, not what this build assumed.
  readonly features: DeploymentFeatures;
  readonly backendStatus: BackendStatus;
  /** Why the backend is not ready yet, when it can say. Never a stack trace. */
  readonly backendDetail: string | null;
}

export type AppStateListener = (state: AppStateSnapshot) => void;

const INITIAL: AppStateSnapshot = {
  query: "",
  mode: DEFAULT_MODE,
  source: DEFAULT_SOURCE,
  filter: DEFAULT_FILTER,
  top: DEFAULT_TOP,
  status: "idle",
  results: [],
  queryParameters: null,
  selectedDocId: null,
  hoveredDocId: null,
  error: null,
  lastQuery: "",
  emphasisDocIds: [],
  hasSearchEmphasis: false,
  mapStatus: "idle",
  mapNodes: [],
  mapMetadata: null,
  mapError: null,
  libraryStatus: "idle",
  libraryIdentity: "",
  savedWorks: [],
  savedDocIds: new Set<string>(),
  libraryError: null,
  savePhase: "idle",
  savePhaseDocId: null,
  features: DEFAULT_FEATURES,
  backendStatus: "unknown",
  backendDetail: null,
};

/**
 * The single source of truth for the Search / Collect screen.
 *
 * Every panel and, from T4, the 3D scene read selection and results from here.
 * No panel keeps its own copy. Deliberately plain TypeScript: no framework, and
 * no DOM or WebGL dependency, so all transitions are testable in isolation.
 */
export class AppState {
  private state: AppStateSnapshot = INITIAL;
  private readonly listeners = new Set<AppStateListener>();

  /**
   * Identifies the search whose response is allowed to land. Bumped on every
   * start, so a slow earlier response cannot overwrite a newer one.
   */
  private activeRequestId = 0;

  getState(): AppStateSnapshot {
    return this.state;
  }

  /**
   * Adopt the deployment's own feature list.
   *
   * Disabling the library also clears its contents: leaving a stale saved list
   * on screen after the server said the feature does not exist would show
   * people data they can no longer act on.
   */
  setFeatures(features: DeploymentFeatures): void {
    if (features.library_enabled) {
      this.patch({ features });
      return;
    }

    this.patch({
      features,
      libraryStatus: "idle",
      libraryIdentity: "",
      savedWorks: [],
      savedDocIds: new Set<string>(),
      libraryError: null,
      savePhase: "idle",
      savePhaseDocId: null,
    });
  }

  setBackendStatus(status: BackendStatus, detail: string | null = null): void {
    this.patch({ backendStatus: status, backendDetail: detail });
  }

  subscribe(listener: AppStateListener): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => this.listeners.delete(listener);
  }

  setQuery(query: string): void {
    this.patch({ query });
  }

  setMode(mode: SearchMode): void {
    this.patch({ mode });
  }

  setSource(source: string): void {
    this.patch({ source });
  }

  setFilter(filter: string): void {
    this.patch({ filter });
  }

  setTop(top: number): void {
    this.patch({ top });
  }

  /** Begin a search. Returns the id that must be passed back on completion. */
  startSearch(): number {
    this.activeRequestId += 1;
    this.patch({
      status: "searching",
      error: null,
    });
    return this.activeRequestId;
  }

  get currentRequestId(): number {
    return this.activeRequestId;
  }

  isCurrent(requestId: number): boolean {
    return requestId === this.activeRequestId;
  }

  /**
   * Apply a completed search. Ignored when a newer search has already started,
   * which is what stops a slow request A from clobbering a faster request B.
   */
  searchSucceeded(
    requestId: number,
    payload: {
      query: string;
      results: readonly SearchResult[];
      queryParameters: readonly ParameterScore[] | null;
    },
  ): boolean {
    if (!this.isCurrent(requestId)) {
      return false;
    }

    // Selection deliberately survives a new search (semantics changed in T4).
    //
    // Before the thought space existed, "selected" could only mean "a row in
    // the current result list", so a search that dropped that row had to clear
    // it. Now a document can be selected by clicking its node, with no search
    // involved at all. Selection is a property of the map, not of the result
    // set, so a new search re-ranks the list without discarding what the user
    // is looking at. The DetailPanel falls back to map metadata when the
    // selected document is no longer a result.
    this.patch({
      status: "success",
      results: payload.results,
      queryParameters: payload.queryParameters,
      error: null,
      lastQuery: payload.query,
      emphasisDocIds: payload.results.map((result) => result.doc_id),
      hasSearchEmphasis: true,
    });
    return true;
  }

  searchFailed(requestId: number, message: string): boolean {
    if (!this.isCurrent(requestId)) {
      return false;
    }

    // The stale result rows go, but selection and map emphasis stay: a failed
    // request should not destroy what the user is currently looking at.
    this.patch({
      status: "error",
      error: message,
      results: [],
      queryParameters: null,
    });
    return true;
  }

  /**
   * Select a document, or pass null to clear.
   *
   * A document is selectable if it is in the current results *or* in the
   * loaded map — clicking a node that no search returned is a normal action
   * now. Ids in neither store are ignored.
   */
  select(docId: string | null): void {
    if (docId === null) {
      this.patch({ selectedDocId: null });
      return;
    }

    const known =
      this.state.results.some((result) => result.doc_id === docId) ||
      this.state.mapNodes.some((node) => node.doc_id === docId);

    if (!known) {
      return;
    }

    this.patch({ selectedDocId: docId });
  }

  /** Set or clear the hovered document. Never affects selection. */
  setHovered(docId: string | null): void {
    if (this.state.hoveredDocId === docId) {
      return;
    }
    this.patch({ hoveredDocId: docId });
  }

  getSelectedResult(): SearchResult | null {
    if (this.state.selectedDocId === null) {
      return null;
    }
    return this.state.results.find((r) => r.doc_id === this.state.selectedDocId) ?? null;
  }

  /** True when a search finished successfully and matched nothing. */
  hasEmptyResults(): boolean {
    return this.state.status === "success" && this.state.results.length === 0;
  }

  // --- thought space ------------------------------------------------------
  // These never touch search fields, and the search transitions above never
  // touch these.

  mapLoading(): void {
    this.patch({ mapStatus: "loading", mapError: null });
  }

  mapLoaded(nodes: readonly MapNode[], metadata: MapProjectionMetadata): void {
    this.patch({
      mapStatus: "ready",
      mapNodes: nodes,
      mapMetadata: metadata,
      mapError: null,
    });
  }

  mapFailed(message: string): void {
    // A previously loaded map is kept: losing connectivity should not empty a
    // thought space the user is already looking at.
    this.patch({ mapStatus: "error", mapError: message });
  }

  // --- personal library ---------------------------------------------------
  // None of these touch search, map or selection state.

  setLibraryIdentity(identity: string): void {
    const value = String(identity ?? "").trim();
    if (value === this.state.libraryIdentity) {
      return;
    }
    // Changing who the library belongs to invalidates everything loaded for
    // the previous identity.
    this.patch({
      libraryIdentity: value,
      savedWorks: [],
      savedDocIds: new Set<string>(),
      libraryStatus: "idle",
      libraryError: null,
    });
  }

  libraryLoading(): void {
    this.patch({ libraryStatus: "loading", libraryError: null });
  }

  libraryLoaded(works: readonly SavedDocument[]): void {
    this.patch({
      libraryStatus: "ready",
      savedWorks: works,
      savedDocIds: new Set(works.map((work) => work.doc_id)),
      libraryError: null,
    });
  }

  libraryFailed(message: string): void {
    // Anything already loaded is kept, exactly as with the map: a failed
    // refresh should not empty a library the user is reading.
    this.patch({ libraryStatus: "error", libraryError: message });
  }

  clearLibraryError(): void {
    if (this.state.libraryError !== null) {
      this.patch({ libraryError: null });
    }
  }

  setSavePhase(phase: SavePhase, docId: string | null): void {
    this.patch({ savePhase: phase, savePhaseDocId: phase === "idle" ? null : docId });
  }

  /** Add one saved work, replacing any existing entry for the same doc_id. */
  documentSaved(work: SavedDocument): void {
    const others = this.state.savedWorks.filter((saved) => saved.doc_id !== work.doc_id);
    const works = [work, ...others];
    this.patch({
      savedWorks: works,
      savedDocIds: new Set(works.map((saved) => saved.doc_id)),
      libraryStatus: "ready",
      savePhase: "idle",
      savePhaseDocId: null,
    });
  }

  documentRemoved(docId: string): void {
    const works = this.state.savedWorks.filter((saved) => saved.doc_id !== docId);
    this.patch({
      savedWorks: works,
      savedDocIds: new Set(works.map((saved) => saved.doc_id)),
      savePhase: "idle",
      savePhaseDocId: null,
    });
  }

  isSaved(docId: string | null | undefined): boolean {
    return docId ? this.state.savedDocIds.has(docId) : false;
  }

  private patch(changes: Partial<AppStateSnapshot>): void {
    this.state = { ...this.state, ...changes };
    for (const listener of this.listeners) {
      listener(this.state);
    }
  }
}
