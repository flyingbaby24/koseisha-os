import { PersonalLibraryClient } from "../api/PersonalLibraryClient";
import { ThoughtMapApiClient } from "../api/ThoughtMapApiClient";
import { DetailPanel } from "../ui/DetailPanel";
import { LibraryPanel } from "../ui/LibraryPanel";
import { BackendStatusBanner } from "../ui/BackendStatusBanner";
import { BottomSheet, isCoarsePrimaryPointer, type SheetMode } from "../ui/BottomSheet";
import { MapStatusView } from "../ui/MapStatusView";
import { ResultPanel } from "../ui/ResultPanel";
import { SearchPanel } from "../ui/SearchPanel";
import { AppState, type AppStateSnapshot } from "./AppState";
import { DocumentSelectionResolver } from "./DocumentSelectionResolver";
import { LibraryController } from "./LibraryController";
import { MapController } from "./MapController";
import { SearchController } from "./SearchController";
import { SelectionController } from "./SelectionController";

/**
 * Composes the Search / Collect screen: state, controllers, and panels.
 *
 * Panels are pure renderers of the shared snapshot. They receive callbacks
 * that go back through the controllers, so there is one write path and one
 * read path.
 */
export class SearchScreen {
  readonly state: AppState;
  readonly search: SearchController;
  readonly selection: SelectionController;
  readonly map: MapController;
  readonly library: LibraryController;
  readonly resolver = new DocumentSelectionResolver();

  /** Fires when selection changes, so the map can focus the chosen node. */
  private readonly selectionListeners = new Set<(docId: string | null) => void>();
  /** Fires when the reader asks to see an already-selected document again. */
  private readonly locateListeners = new Set<(docId: string) => void>();
  private lastSelectedDocId: string | null = null;
  private lastStatus: AppStateSnapshot["status"] = "idle";

  private readonly searchPanel: SearchPanel;
  private readonly resultPanel: ResultPanel;
  private readonly detailPanel: DetailPanel;
  private readonly mapStatusView: MapStatusView;
  private readonly libraryPanel: LibraryPanel;
  private readonly backendBanner: BackendStatusBanner;
  private readonly tabs: Map<string, HTMLButtonElement> = new Map();
  private readonly tabCounts: Map<string, HTMLElement> = new Map();
  private tabBar!: HTMLDivElement;
  private readonly root: HTMLElement;
  private readonly centre: HTMLElement;
  private readonly dock: HTMLElement;
  private readonly notice: HTMLElement;
  private noticeTimer: ReturnType<typeof setTimeout> | null = null;
  /** The phone layout's panel; inert on tablets and desktops. */
  readonly sheet: BottomSheet;
  private readonly coarsePointer: () => boolean;
  /** Mirrors features.library_enabled, so the DOM is touched only on change. */
  private libraryVisible = true;
  private activeTab: "results" | "library" = "results";
  private readonly unsubscribe: () => void;

  constructor(
    mount: HTMLElement,
    client: ThoughtMapApiClient = new ThoughtMapApiClient(),
    libraryClient: PersonalLibraryClient = new PersonalLibraryClient(),
    options: SearchScreenOptions = {},
  ) {
    this.coarsePointer = options.coarsePointer ?? isCoarsePrimaryPointer;
    this.state = new AppState();
    this.search = new SearchController(this.state, client);
    this.selection = new SelectionController(this.state);
    this.map = new MapController(this.state, client);
    this.library = new LibraryController(this.state, libraryClient);

    this.searchPanel = new SearchPanel(this.state, {
      onSearch: () => {
        // On a phone, close the keyboard so the results it would cover show.
        if (this.coarsePointer()) {
          this.searchPanel.blur();
        }
        void this.search.search();
      },
      // Typing needs the map and the search bar, not the panel: the keyboard
      // is about to take the bottom of the screen.
      onFocusChange: (focused) => {
        if (focused && this.sheet.layoutMode === "bottom") {
          this.sheet.setSnap("peek");
        }
      },
    });
    this.resultPanel = new ResultPanel({
      // Selection has exactly one path, here and for the 3D scene in T4.
      onSelect: (docId) => this.selectOrLocate(docId),
      // Pointing at a row lights its node, the mirror of map hover lighting
      // the row: the two views of one document always agree.
      onHover: (docId) => this.state.setHovered(docId),
      onRetry: () => void this.search.search(),
      onExample: (query) => {
        this.state.setQuery(query);
        void this.search.search();
      },
    });
    this.detailPanel = new DetailPanel({
      onLocate: (docId) => this.emitLocate(docId),
      onBack: () => this.setView("list"),
      onRequestLibrary: () => {
        this.showTab("library");
        this.setView("list");
        this.libraryPanel.focusIdentity();
      },
      onStep: (delta) => this.stepResult(delta),
    });
    this.mapStatusView = new MapStatusView();
    this.backendBanner = new BackendStatusBanner();

    this.libraryPanel = new LibraryPanel({
      onSetIdentity: (identity) => {
        this.library.setIdentity(identity);
        void this.library.load();
      },
      onClearIdentity: () => this.library.clearIdentity(),
      // Saved works select through the same controller as results and nodes.
      onSelect: (docId) => this.selectOrLocate(docId),
      onRemove: (docId) => void this.library.remove(docId),
      onReload: () => void this.library.load(),
    });

    // Save / remove is confirmed by the server before anything is marked saved.
    this.detailPanel.onSaveToggle((docId, currentlySaved) => {
      if (currentlySaved) {
        void this.library.remove(docId);
        return;
      }
      const document = this.resolver.resolve(this.state.getState());
      if (document && document.doc_id === docId) {
        void this.library.save(document);
      }
    });

    const brand = document.createElement("div");
    brand.className = "tm-brand";
    const mark = document.createElement("span");
    mark.className = "tm-brand-mark";
    mark.setAttribute("aria-hidden", "true");
    const name = document.createElement("h1");
    name.className = "tm-brand-name";
    name.textContent = "ThoughtMap";
    brand.append(mark, name);

    const bar = document.createElement("header");
    bar.className = "tm-topbar";
    bar.append(brand, this.searchPanel.element);

    const top = document.createElement("div");
    top.className = "tm-layout-top";
    top.append(bar, this.backendBanner.element);

    // The centre is the window onto the Thought Space. The canvas fills the
    // whole screen behind the panels; this element marks the part of it that
    // is actually visible, so the camera can centre on it (`mapWindow`). It
    // stays pointer-transparent so orbit works through it.
    this.centre = document.createElement("div");
    this.centre.className = "tm-layout-centre";

    const hint = document.createElement("p");
    hint.className = "tm-map-hint";
    hint.append(
      hintText(
        "for-pointer",
        "Drag to orbit · Right-drag to pan · Scroll to zoom · Click a point to select",
      ),
      hintText("for-touch", "Drag to orbit · Pinch to zoom · Tap to select"),
    );

    // Camera controls are adopted into this dock (`adoptMapControls`), so they
    // sit under the visible map at every width instead of under the panels.
    this.dock = document.createElement("div");
    this.dock.className = "tm-map-dock";
    this.dock.append(hint);

    // One short line over the map for things the map itself says: a crowded
    // tap that zoomed instead of guessing, or a paused 3D view.
    this.notice = document.createElement("p");
    this.notice.className = "tm-map-notice";
    this.notice.setAttribute("role", "status");
    this.notice.setAttribute("aria-live", "polite");
    this.notice.hidden = true;

    this.centre.append(this.mapStatusView.element, this.notice, this.dock);

    // Results and Library share the left column as tabs. Search / Collect
    // stays one screen; nothing here belongs to Battle Prep.
    const left = document.createElement("section");
    left.className = "tm-panel tm-left";

    const tabBar = document.createElement("div");
    tabBar.className = "tm-tabs";
    tabBar.setAttribute("role", "tablist");
    tabBar.setAttribute("aria-label", "Results and Library");
    tabBar.addEventListener("keydown", this.handleTabKeydown);
    this.tabBar = tabBar;

    for (const [id, label] of [["results", "Results"], ["library", "Library"]] as const) {
      const tab = document.createElement("button");
      tab.type = "button";
      tab.className = "tm-tab";
      tab.id = `tm-tab-${id}`;
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-controls", `tm-tabpanel-${id}`);
      const text = document.createElement("span");
      text.textContent = label;
      const count = document.createElement("span");
      count.className = "tm-tab-count";
      count.hidden = true;
      tab.append(text, count);
      tab.addEventListener("click", () => this.showTab(id));
      this.tabs.set(id, tab);
      this.tabCounts.set(id, count);
      tabBar.append(tab);
    }

    for (const [id, panel] of [
      ["results", this.resultPanel.element],
      ["library", this.libraryPanel.element],
    ] as const) {
      panel.classList.add("tm-tabpanel");
      panel.id = `tm-tabpanel-${id}`;
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", `tm-tab-${id}`);
    }
    left.append(tabBar, this.resultPanel.element, this.libraryPanel.element);

    // On wide screens the sheet is layout-neutral (`display: contents`) and
    // its two panels take the outer columns. On a phone it becomes the bottom
    // sheet under the map window, showing the list or the document.
    const sheet = document.createElement("div");
    sheet.className = "tm-sheet";
    // The grab handle exists at every width but is only shown, and only
    // does anything, in the phone layout.
    const handle = document.createElement("button");
    handle.type = "button";
    handle.className = "tm-sheet-handle";
    sheet.append(handle, left, this.detailPanel.element);

    const columns = document.createElement("div");
    columns.className = "tm-layout-columns";
    columns.append(sheet, this.centre);

    this.root = document.createElement("div");
    this.root.className = "tm-layout";
    this.root.dataset["view"] = "list";
    this.root.append(top, columns);
    mount.append(this.root);

    this.sheet = new BottomSheet({
      root: this.root,
      handle,
      dragZones: [tabBar, this.detailPanel.headElement],
      topEdge: () => top.getBoundingClientRect().bottom,
      ...(options.sheetMode ? { mode: options.sheetMode } : {}),
    });

    this.unsubscribe = this.state.subscribe((snapshot) => {
      this.searchPanel.render(snapshot);
      this.resultPanel.render(snapshot);
      this.detailPanel.render(snapshot, this.resolver.resolve(snapshot));
      this.mapStatusView.render(snapshot);
      this.libraryPanel.render(snapshot);
      this.backendBanner.render(snapshot);
      this.applyDeploymentFeatures(snapshot);
      this.renderTabBadges(snapshot);
      this.root.classList.toggle("has-selection", snapshot.selectedDocId !== null);

      // A new search brings the list back on narrow screens: that is what the
      // reader is waiting for.
      if (snapshot.status === "searching" && this.lastStatus !== "searching") {
        this.setView("list");
        this.showTab("results");
        this.raiseSheetFromPeek();
      }
      this.lastStatus = snapshot.status;

      if (snapshot.selectedDocId !== this.lastSelectedDocId) {
        this.lastSelectedDocId = snapshot.selectedDocId;
        this.setView(snapshot.selectedDocId === null ? "list" : "detail");
        if (snapshot.selectedDocId !== null) {
          this.raiseSheetFromPeek();
        }
        for (const listener of this.selectionListeners) {
          listener(snapshot.selectedDocId);
        }
      }
    });

    document.addEventListener("keydown", this.handleShortcut);

    this.showTab("results");
    // On a phone, focusing on load can raise the keyboard over the map before
    // anyone asked to type.
    if (!this.coarsePointer()) {
      this.searchPanel.focus();
    }
  }

  /**
   * A drag or pinch on the map has begun (never a mere touch-down): give the
   * map the screen. Called by the interaction layer only once a gesture is
   * known not to be a tap, so a tap never moves the layout under the finger.
   */
  onMapGesture(): void {
    if (this.sheet.layoutMode === "bottom" && this.sheet.snap !== "peek") {
      this.sheet.setSnap("peek");
    }
  }

  /** Show a short message over the map; `persist` keeps it until replaced. */
  showMapNotice(text: string, persist = false): void {
    if (this.noticeTimer !== null) {
      clearTimeout(this.noticeTimer);
      this.noticeTimer = null;
    }
    this.notice.textContent = text;
    this.notice.hidden = false;
    if (!persist) {
      this.noticeTimer = setTimeout(() => this.hideMapNotice(), 2800);
    }
  }

  hideMapNotice(): void {
    if (this.noticeTimer !== null) {
      clearTimeout(this.noticeTimer);
      this.noticeTimer = null;
    }
    this.notice.hidden = true;
    this.notice.textContent = "";
  }

  /** The browser took the WebGL context away (or gave it back). */
  setMapSuspended(suspended: boolean): void {
    this.root.classList.toggle("is-map-suspended", suspended);
    if (suspended) {
      this.showMapNotice(
        "The browser paused the 3D view to save resources. It will return on its own; search and documents still work.",
        true,
      );
    } else {
      this.hideMapNotice();
    }
  }

  /**
   * Select the previous or next result. From a document that is not among
   * the results, "next" starts at the first one.
   */
  stepResult(delta: -1 | 1): void {
    const { results, selectedDocId } = this.state.getState();
    if (results.length === 0) {
      return;
    }
    const index = results.findIndex((result) => result.doc_id === selectedDocId);
    const target = index === -1 ? (delta > 0 ? 0 : -1) : index + delta;
    const next = results[target];
    if (next) {
      this.selection.select(next.doc_id);
    }
  }

  /** A search or a selection wants the panel readable, not just its header. */
  private raiseSheetFromPeek(): void {
    if (this.sheet.layoutMode === "bottom" && this.sheet.snap === "peek") {
      this.sheet.setSnap("half");
    }
  }

  /** The visible part of the map, between the panels. */
  get mapWindow(): HTMLElement {
    return this.centre;
  }

  /** Move the page's camera controls under the visible map. */
  adoptMapControls(...elements: Array<HTMLElement | null>): void {
    for (const element of elements) {
      if (element) {
        this.dock.append(element);
      }
    }
  }

  /**
   * Narrow layouts show the list or the selected document, not both.
   * Wider layouts ignore this and show both side by side.
   */
  setView(view: "list" | "detail"): void {
    if (this.root.dataset["view"] !== view) {
      this.root.dataset["view"] = view;
    }
  }

  /**
   * Select a document, or — if it already is — show it again.
   *
   * Clicking the selected row after orbiting away is the natural way to say
   * "where was that?"; selecting it again would be a no-op, so it re-centres.
   */
  private selectOrLocate(docId: string): void {
    if (this.state.getState().selectedDocId === docId) {
      this.setView("detail");
      this.emitLocate(docId);
      return;
    }
    this.selection.select(docId);
  }

  private emitLocate(docId: string): void {
    for (const listener of this.locateListeners) {
      listener(docId);
    }
  }

  /**
   * Keyboard shortcuts that never fight with typing: `/` jumps to the search
   * box, Escape steps back (detail → list, then clears the selection).
   */
  private readonly handleShortcut = (event: KeyboardEvent): void => {
    if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) {
      return;
    }
    const target = event.target as HTMLElement | null;
    const typing =
      target instanceof HTMLInputElement ||
      target instanceof HTMLTextAreaElement ||
      target instanceof HTMLSelectElement ||
      target?.isContentEditable === true;

    if (event.key === "/" && !typing) {
      event.preventDefault();
      this.searchPanel.focusAndSelect();
      return;
    }

    if (event.key === "Escape" && !typing && this.state.getState().selectedDocId !== null) {
      event.preventDefault();
      this.selection.clear();
    }
  };

  /** Left/Right/Home/End move between tabs, as the tab pattern expects. */
  private readonly handleTabKeydown = (event: KeyboardEvent): void => {
    const order = [...this.tabs.entries()].filter(([, tab]) => !tab.hidden);
    const current = order.findIndex(([, tab]) => tab === document.activeElement);
    if (current === -1) {
      return;
    }
    let next = -1;
    if (event.key === "ArrowRight") {
      next = (current + 1) % order.length;
    } else if (event.key === "ArrowLeft") {
      next = (current - 1 + order.length) % order.length;
    } else if (event.key === "Home") {
      next = 0;
    } else if (event.key === "End") {
      next = order.length - 1;
    }
    const entry = order[next];
    if (!entry) {
      return;
    }
    event.preventDefault();
    this.showTab(entry[0] as "results" | "library");
    entry[1].focus();
  };

  /**
   * Reflect the deployment's feature list in the chrome.
   *
   * Called on every render because `/config` answers after the first paint;
   * it must be cheap and idempotent, so it only ever toggles two flags.
   */
  private applyDeploymentFeatures(snapshot: AppStateSnapshot): void {
    const enabled = snapshot.features.library_enabled;
    if (enabled === this.libraryVisible) {
      return;
    }
    this.libraryVisible = enabled;

    const tab = this.tabs.get("library");
    if (tab) {
      tab.hidden = !enabled;
    }
    this.tabBar.hidden = !enabled;

    if (!enabled && this.activeTab === "library") {
      this.showTab("results");
    }
  }

  /**
   * Start using the Personal Library, if this deployment has one.
   *
   * Deliberately not done in the constructor: whether the library exists is the
   * server's answer, and asking for a saved list the deployment does not serve
   * would produce a 404 and a visible error for a feature nobody can use.
   */
  enableLibraryIfAvailable(): void {
    if (!this.state.getState().features.library_enabled) {
      return;
    }
    // A remembered library ID loads immediately; a failure here is local to the
    // library panel and never blocks search or the map.
    if (this.library.restoreIdentity()) {
      void this.library.load();
    }
  }

  /** Switch the left column between Results and Library. */
  showTab(id: "results" | "library"): void {
    this.activeTab = id;
    for (const [key, tab] of this.tabs) {
      const active = key === id;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    }
    this.resultPanel.element.hidden = id !== "results";
    this.libraryPanel.element.hidden = id !== "library";
  }

  private renderTabBadges(snapshot: AppStateSnapshot): void {
    setCount(this.tabCounts.get("results"), snapshot.results.length);
    setCount(this.tabCounts.get("library"), snapshot.savedWorks.length);
  }

  /** Observe selection changes (used to focus the camera on the chosen node). */
  onSelectionChange(listener: (docId: string | null) => void): () => void {
    this.selectionListeners.add(listener);
    return () => this.selectionListeners.delete(listener);
  }

  /** Observe requests to bring an already-selected document back into view. */
  onLocateRequest(listener: (docId: string) => void): () => void {
    this.locateListeners.add(listener);
    return () => this.locateListeners.delete(listener);
  }

  dispose(): void {
    this.sheet.dispose();
    this.hideMapNotice();
    document.removeEventListener("keydown", this.handleShortcut);
    this.selectionListeners.clear();
    this.locateListeners.clear();
    this.unsubscribe();
    this.search.cancel();
    this.map.cancel();
    this.library.cancel();
  }
}

function setCount(element: HTMLElement | undefined, count: number): void {
  if (!element) {
    return;
  }
  const text = count > 0 ? String(count) : "";
  if (element.textContent !== text) {
    element.textContent = text;
  }
  element.hidden = count === 0;
}

function hintText(className: string, text: string): HTMLElement {
  const span = document.createElement("span");
  span.className = className;
  span.textContent = text;
  return span;
}

export interface SearchScreenOptions {
  /** Which panel layout applies. Defaults to the viewport's media queries. */
  sheetMode?: () => SheetMode;
  /** Whether the primary pointer is a finger. Defaults to `(pointer: coarse)`. */
  coarsePointer?: () => boolean;
}
