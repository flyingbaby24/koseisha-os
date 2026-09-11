import type { HoverInfo } from "../app/ThoughtMapInteractionController";
import { clampTooltipPosition } from "../scene/picking";
import { formatSimilarity, orDash } from "./format";

/**
 * One reusable tooltip for the whole map.
 *
 * Exactly one element exists regardless of corpus size — 4,915 nodes get one
 * tooltip, not 4,915 DOM nodes. It is pointer-transparent, so it can never
 * swallow a click meant for the node underneath it.
 */
export class MapTooltip {
  readonly element: HTMLElement;

  private readonly titleLine: HTMLElement;
  private readonly metaLine: HTMLElement;
  private readonly similarityLine: HTMLElement;

  constructor(private readonly container: HTMLElement) {
    this.element = document.createElement("div");
    this.element.className = "tm-map-tooltip";
    this.element.hidden = true;
    // Never intercepts pointer events; hover must keep reaching the canvas.
    this.element.setAttribute("aria-hidden", "true");

    this.titleLine = document.createElement("div");
    this.titleLine.className = "tm-tooltip-title";

    this.metaLine = document.createElement("div");
    this.metaLine.className = "tm-tooltip-meta";

    this.similarityLine = document.createElement("div");
    this.similarityLine.className = "tm-tooltip-similarity";

    this.element.append(this.titleLine, this.metaLine, this.similarityLine);
    this.container.append(this.element);
  }

  show(info: HoverInfo): void {
    this.titleLine.textContent = orDash(info.title);

    const author = (info.author ?? "").trim();
    const source = (info.source ?? "").trim();
    this.metaLine.textContent = [author, source].filter(Boolean).join(" · ") || "—";

    // Similarity only means something while this node is a current result.
    if (info.similarity === null) {
      this.similarityLine.hidden = true;
      this.similarityLine.textContent = "";
    } else {
      this.similarityLine.hidden = false;
      this.similarityLine.textContent = `similarity ${formatSimilarity(info.similarity)}`;
    }

    this.element.hidden = false;
    this.position(info.x, info.y);
  }

  hide(): void {
    this.element.hidden = true;
  }

  /** Offset from the cursor, kept inside the canvas on every edge. */
  private position(x: number, y: number): void {
    const rect = this.container.getBoundingClientRect();
    const width = this.element.offsetWidth || 200;
    const height = this.element.offsetHeight || 56;

    const placed = clampTooltipPosition(
      x + 16,
      y + 16,
      width,
      height,
      rect.width,
      rect.height,
    );

    this.element.style.transform = `translate(${placed.x}px, ${placed.y}px)`;
  }
}
