import type { AppStateSnapshot } from "../app/AppState";
import { summariseSources } from "../config/sourceStyles";

/**
 * The map's visual vocabulary, in the order of importance it encodes.
 * Glyphs are drawn in CSS to match the shader (`NodeRenderer`).
 */
const STATE_KEY: ReadonlyArray<{ id: string; label: string; title: string }> = [
  { id: "selected", label: "Selected", title: "The selected document — a gold reticle" },
  { id: "result", label: "Result", title: "Search results — cyan, brighter with rank" },
  { id: "saved", label: "Saved", title: "In your Personal Library — a mint ring" },
  { id: "document", label: "Document", title: "Every other document, coloured by source" },
];

/**
 * Status and legend for the thought space, shown over the canvas column.
 *
 * A map failure never replaces the application: it says the space is
 * unavailable and points out that search still works. There are no per-node
 * labels — 4915 of them would be unreadable and ruinous for the frame budget.
 * Titles arrive with hover and selection in T4.
 */
export class MapStatusView {
  readonly element: HTMLElement;

  private readonly message: HTMLElement;
  private readonly detail: HTMLElement;
  private readonly legend: HTMLElement;
  private readonly sources: HTMLElement;
  private readonly key: HTMLElement;
  private lastNodes: readonly unknown[] | null = null;

  constructor() {
    this.element = document.createElement("div");
    this.element.className = "tm-map-status";

    this.message = document.createElement("p");
    this.message.className = "tm-map-message";

    this.detail = document.createElement("p");
    this.detail.className = "tm-map-detail";

    this.legend = document.createElement("div");
    this.legend.className = "tm-map-legend";
    this.legend.setAttribute("aria-label", "Map legend");
    this.legend.setAttribute("role", "group");

    this.key = document.createElement("div");
    this.key.className = "tm-map-key";
    for (const entry of STATE_KEY) {
      const item = document.createElement("span");
      item.className = `tm-map-key-item is-${entry.id}`;
      item.title = entry.title;
      const glyph = document.createElement("span");
      glyph.className = "tm-map-glyph";
      glyph.setAttribute("aria-hidden", "true");
      item.append(glyph, entry.label);
      this.key.append(item);
    }

    this.sources = document.createElement("div");
    this.sources.className = "tm-map-sources";

    this.legend.append(this.key, this.sources);
    this.element.append(this.message, this.detail, this.legend);
  }

  render(snapshot: AppStateSnapshot): void {
    const { mapStatus, mapNodes, mapError, mapMetadata } = snapshot;

    if (mapStatus === "loading" && mapNodes.length === 0) {
      this.element.hidden = false;
      this.element.classList.remove("is-error");
      this.element.classList.add("is-loading");
      this.message.hidden = false;
      this.message.textContent = "Loading Thought Space…";
      this.detail.textContent = "Projecting the corpus into three dimensions.";
      this.detail.hidden = false;
      this.legend.hidden = true;
      return;
    }

    this.element.classList.remove("is-loading");

    if (mapStatus === "error" && mapNodes.length === 0) {
      this.element.hidden = false;
      this.element.classList.add("is-error");
      this.message.hidden = false;
      this.message.textContent = "Thought Space unavailable";
      // The point of this line: the rest of the app is still usable.
      this.detail.textContent = `${mapError ?? ""} Search remains available.`.trim();
      this.detail.hidden = false;
      this.legend.hidden = true;
      return;
    }

    if (mapNodes.length === 0) {
      this.element.hidden = true;
      return;
    }

    // Map is on screen: keep only the compact legend.
    this.element.hidden = false;
    this.element.classList.remove("is-error");
    this.message.textContent = "";
    this.message.hidden = true;
    this.detail.hidden = true;

    if (mapNodes !== this.lastNodes) {
      this.lastNodes = mapNodes;
      this.renderLegend(mapNodes, mapMetadata?.document_count ?? mapNodes.length);
    }
    this.legend.hidden = false;
    this.element.classList.toggle("is-searching-map", snapshot.hasSearchEmphasis);
  }

  private renderLegend(nodes: readonly { source: string }[], total: number): void {
    const summary = summariseSources(nodes);

    const heading = document.createElement("span");
    heading.className = "tm-map-legend-total";
    heading.textContent = `${total.toLocaleString()} documents`;

    const items = summary.map((entry) => {
      const item = document.createElement("span");
      item.className = "tm-map-legend-item";

      const swatch = document.createElement("span");
      swatch.className = "tm-map-swatch";
      const [r, g, b] = entry.color;
      swatch.style.background = `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`;

      const label = document.createElement("span");
      label.textContent = `${entry.label} ${entry.count.toLocaleString()}`;

      item.append(swatch, label);
      return item;
    });

    this.sources.replaceChildren(heading, ...items);
  }
}
