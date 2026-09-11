import { PersonalLibraryClient } from "../api/PersonalLibraryClient";
import { ThoughtMapApiClient } from "../api/ThoughtMapApiClient";
import { DetailPanel } from "../ui/DetailPanel";
import { LibraryPanel } from "../ui/LibraryPanel";
import { BackendStatusBanner } from "../ui/BackendStatusBanner";
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
  private lastSelectedDocId: string | null = null;

  private readonly searchPanel: SearchPanel;
  private readonly resultPanel: ResultPanel;
  private readonly detailPanel: DetailPanel;
  private readonly mapStatusView: MapStatusView;
  private readonly libraryPanel: LibraryPanel;
  private readonly backendBanner: BackendStatusBanner;
  private readonly tabs: Map<string, HTMLButtonElement> = new Map();
  private tabBar!: HTMLDivElement;
  /** Mirrors features.library_enabled, so the DOM is touched only on change. */
  private libraryVisible = true;
  private activeTab: "results" | "library" = "results";
  private readonly unsubscribe: () => void;

  constructor(
    mount: HTMLElement,
    client: ThoughtMapApiClient = new ThoughtMapApiClient(),
    libraryClient: PersonalLibraryClient = new PersonalLibraryClient(),
  ) {
    this.state = new AppState();
    this.search = new SearchController(this.state, client);
    this.selection = new SelectionController(this.state);
    this.map = new MapController(this.state, client);
    this.library = new LibraryController(this.state, libraryClient);

    this.searchPanel = new SearchPanel(this.state, {
      onSearch: () => void this.search.search(),
    });
    this.resultPanel = new ResultPanel({
      // Selection has exactly one path, here and for the 3D scene in T4.
      onSelect: (docId) => this.selection.select(docId),
    });
    this.detailPanel = new DetailPanel();
    this.mapStatusView = new MapStatusView();
    this.backendBanner = new BackendStatusBanner();

    this.libraryPanel = new LibraryPanel({
      onSetIdentity: (identity) => {
        this.library.setIdentity(identity);
        void this.library.load();
      },
      onClearIdentity: () => this.library.clearIdentity(),
      // Saved works select through the same controller as results and nodes.
      onSelect: (docId) => this.selection.select(docId),
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

    const top = document.createElement("div");
    top.className = "tm-layout-top";
    top.append(this.backendBanner.element, this.searchPanel.element);

    // The centre column is the window onto the Thought Space; only the status
    // overlay lives there, so the canvas behind it stays reachable.
    const centre = document.createElement("div");
    centre.className = "tm-layout-centre";
    centre.append(this.mapStatusView.element);

    // Results and Library share the left column as tabs. Search / Collect
    // stays one screen; nothing here belongs to Battle Prep.
    const left = document.createElement("section");
    left.className = "tm-panel tm-left";

    const tabBar = document.createElement("div");
    tabBar.className = "tm-tabs";
    tabBar.setAttribute("role", "tablist");
    this.tabBar = tabBar;

    for (const [id, label] of [["results", "Results"], ["library", "Library"]] as const) {
      const tab = document.createElement("button");
      tab.type = "button";
      tab.className = "tm-tab";
      tab.textContent = label;
      tab.setAttribute("role", "tab");
      tab.addEventListener("click", () => this.showTab(id));
      this.tabs.set(id, tab);
      tabBar.append(tab);
    }

    this.resultPanel.element.classList.add("tm-tabpanel");
    this.libraryPanel.element.classList.add("tm-tabpanel");
    left.append(tabBar, this.resultPanel.element, this.libraryPanel.element);

    const columns = document.createElement("div");
    columns.className = "tm-layout-columns";
    columns.append(left, centre, this.detailPanel.element);

    const root = document.createElement("div");
    root.className = "tm-layout";
    root.append(top, columns);
    mount.append(root);

    this.unsubscribe = this.state.subscribe((snapshot) => {
      this.searchPanel.render(snapshot);
      this.resultPanel.render(snapshot);
      this.detailPanel.render(snapshot, this.resolver.resolve(snapshot));
      this.mapStatusView.render(snapshot);
      this.libraryPanel.render(snapshot);
      this.backendBanner.render(snapshot);
      this.applyDeploymentFeatures(snapshot);
      this.renderTabBadges(snapshot);

      if (snapshot.selectedDocId !== this.lastSelectedDocId) {
        this.lastSelectedDocId = snapshot.selectedDocId;
        for (const listener of this.selectionListeners) {
          listener(snapshot.selectedDocId);
        }
      }
    });

    this.showTab("results");
    this.searchPanel.focus();
  }

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
    }
    this.resultPanel.element.hidden = id !== "results";
    this.libraryPanel.element.hidden = id !== "library";
  }

  private renderTabBadges(snapshot: { savedWorks: readonly unknown[] }): void {
    const library = this.tabs.get("library");
    if (library) {
      library.textContent =
        snapshot.savedWorks.length > 0 ? `Library (${snapshot.savedWorks.length})` : "Library";
      library.classList.toggle("is-active", this.activeTab === "library");
      library.setAttribute("aria-selected", String(this.activeTab === "library"));
    }
  }

  /** Observe selection changes (used to focus the camera on the chosen node). */
  onSelectionChange(listener: (docId: string | null) => void): () => void {
    this.selectionListeners.add(listener);
    return () => this.selectionListeners.delete(listener);
  }

  dispose(): void {
    this.selectionListeners.clear();
    this.unsubscribe();
    this.search.cancel();
    this.map.cancel();
    this.library.cancel();
  }
}
