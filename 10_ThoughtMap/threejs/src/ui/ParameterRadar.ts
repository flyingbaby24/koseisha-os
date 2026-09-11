import type { ParameterScore } from "../api/types";
import { PARAMETER_AXIS_ORDER, axisLabel } from "../config/searchOptions";
import { formatShare } from "./format";
import {
  computeAxes,
  computePolygon,
  computeRings,
  computeSharedDomain,
  isEmptyProfile,
  toPolygonPoints,
  type RadarAxis,
} from "./radarGeometry";

export interface RadarProfile {
  /** Legend text, e.g. "Query" or the document title. */
  label: string;
  scores: readonly ParameterScore[] | null | undefined;
  /** CSS custom-property suffix picking the stroke/fill pair. */
  variant: "query" | "document";
}

const RADIUS = 100;
const LABEL_OFFSET = 20;
const VIEWBOX = 320;

/**
 * Ten-axis Thought Composition radar, in SVG.
 *
 * SVG rather than Three.js: this is a data chart, not part of the spatial map,
 * and it needs crisp text, DOM accessibility and a `viewBox` that scales itself.
 * Putting it in the WebGL scene would buy nothing and cost all three.
 *
 * Purely presentational — it receives canonical values and renders them. It
 * never fetches, never owns selection, and never mutates what it is given.
 */
export class ParameterRadar {
  readonly element: HTMLElement;

  private readonly svg: SVGSVGElement;
  private readonly plot: SVGGElement;
  private readonly legend: HTMLElement;
  private readonly table: HTMLElement;
  private readonly note: HTMLElement;
  private readonly axes: RadarAxis[];

  constructor(private readonly title: string) {
    this.axes = computeAxes(RADIUS, LABEL_OFFSET, PARAMETER_AXIS_ORDER, axisLabel);

    this.element = document.createElement("section");
    this.element.className = "tm-radar";

    const heading = document.createElement("h3");
    heading.className = "tm-radar-title";
    heading.textContent = title;

    this.svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    // A viewBox with no fixed pixel size lets CSS scale the chart to any
    // column width without overflowing or needing a ResizeObserver.
    this.svg.setAttribute("viewBox", `${-VIEWBOX / 2} ${-VIEWBOX / 2} ${VIEWBOX} ${VIEWBOX}`);
    this.svg.setAttribute("class", "tm-radar-svg");
    this.svg.setAttribute("role", "img");
    this.svg.setAttribute("preserveAspectRatio", "xMidYMid meet");

    this.plot = document.createElementNS("http://www.w3.org/2000/svg", "g");
    this.svg.append(this.plot);

    this.legend = document.createElement("div");
    this.legend.className = "tm-radar-legend";

    this.note = document.createElement("p");
    this.note.className = "tm-note tm-radar-note";
    this.note.hidden = true;

    // The chart is not the only way to read the numbers: the same values are
    // always present as a table for screen readers and keyboard users.
    this.table = document.createElement("table");
    this.table.className = "tm-radar-table";

    const details = document.createElement("details");
    details.className = "tm-radar-details";
    const summary = document.createElement("summary");
    summary.textContent = "Values";
    details.append(summary, this.table);

    this.element.append(heading, this.svg, this.legend, this.note, details);
  }

  /**
   * Draw one or more profiles on a shared scale.
   *
   * Every profile is plotted against one domain derived from all of them, so
   * the polygons stay comparable. Normalising each to its own peak would make
   * every profile fill the chart and destroy the comparison.
   */
  render(profiles: readonly RadarProfile[]): void {
    const present = profiles.filter((profile) => profile.scores && profile.scores.length > 0);

    if (present.length === 0) {
      this.plot.replaceChildren();
      this.legend.replaceChildren();
      this.table.replaceChildren();
      this.svg.setAttribute("hidden", "hidden");
      this.note.hidden = false;
      this.note.textContent = "No parameter profile available.";
      this.svg.setAttribute("aria-label", `${this.title}: no data`);
      return;
    }

    this.svg.removeAttribute("hidden");
    const domain = computeSharedDomain(present.map((profile) => profile.scores));

    const children: SVGElement[] = [
      ...this.buildRings(domain),
      ...this.buildSpokes(),
      ...this.buildLabels(),
    ];

    for (const profile of present) {
      children.push(...this.buildProfile(profile, domain));
    }

    this.plot.replaceChildren(...children);
    this.renderLegend(present, domain);
    this.renderTable(present);

    const allEmpty = present.every((profile) => isEmptyProfile(profile.scores));
    this.note.hidden = !allEmpty;
    if (allEmpty) {
      // The canonical all-zero document: no positive affinity to any axis.
      // Saying so is more honest than drawing a fake uniform ring.
      this.note.textContent =
        "No positive affinity was detected on any axis, so this profile sits at the centre.";
    }

    this.svg.setAttribute(
      "aria-label",
      `${this.title}. ${present
        .map((profile) => `${profile.label}: ${this.describe(profile)}`)
        .join(". ")}`,
    );
  }

  private describe(profile: RadarProfile): string {
    const ordered = [...(profile.scores ?? [])]
      .filter((score) => Number.isFinite(score.value))
      .sort((a, b) => b.value - a.value)
      .slice(0, 3);

    if (ordered.length === 0) {
      return "no values";
    }
    return ordered.map((s) => `${axisLabel(s.key)} ${formatShare(s.value)}`).join(", ");
  }

  private buildRings(domain: number): SVGElement[] {
    return computeRings(domain).map((_value, index, all) => {
      const circle = svgEl("circle");
      circle.setAttribute("class", "tm-radar-ring");
      circle.setAttribute("r", String((RADIUS * (index + 1)) / all.length));
      circle.setAttribute("cx", "0");
      circle.setAttribute("cy", "0");
      return circle;
    });
  }

  private buildSpokes(): SVGElement[] {
    return this.axes.map((axis) => {
      const line = svgEl("line");
      line.setAttribute("class", "tm-radar-spoke");
      line.setAttribute("x1", "0");
      line.setAttribute("y1", "0");
      line.setAttribute("x2", String(axis.outer.x));
      line.setAttribute("y2", String(axis.outer.y));
      return line;
    });
  }

  private buildLabels(): SVGElement[] {
    return this.axes.map((axis) => {
      const text = svgEl("text");
      text.setAttribute("class", "tm-radar-label");
      text.setAttribute("x", String(axis.labelAnchor.x));
      text.setAttribute("y", String(axis.labelAnchor.y));
      text.setAttribute("text-anchor", axis.textAnchor);
      text.setAttribute("dominant-baseline", "middle");
      text.textContent = axis.label;
      return text;
    });
  }

  private buildProfile(profile: RadarProfile, domain: number): SVGElement[] {
    const points = computePolygon(profile.scores, this.axes, domain, RADIUS);

    const polygon = svgEl("polygon");
    polygon.setAttribute("class", `tm-radar-shape is-${profile.variant}`);
    polygon.setAttribute("points", toPolygonPoints(points));

    const vertices = points.map((point, index) => {
      const dot = svgEl("circle");
      dot.setAttribute("class", `tm-radar-vertex is-${profile.variant}`);
      dot.setAttribute("cx", String(point.x));
      dot.setAttribute("cy", String(point.y));
      dot.setAttribute("r", "2.5");

      const axis = this.axes[index];
      const score = profile.scores?.find((s) => s.key === axis?.key);
      const title = svgEl("title");
      title.textContent = `${profile.label} — ${axis?.label ?? ""}: ${
        score ? formatShare(score.value) : "—"
      }`;
      dot.append(title);
      return dot;
    });

    return [polygon, ...vertices];
  }

  private renderLegend(profiles: readonly RadarProfile[], domain: number): void {
    const items = profiles.map((profile) => {
      const item = document.createElement("span");
      item.className = `tm-radar-legend-item is-${profile.variant}`;

      const swatch = document.createElement("span");
      swatch.className = `tm-radar-swatch is-${profile.variant}`;

      const label = document.createElement("span");
      label.textContent = profile.label;

      item.append(swatch, label);
      return item;
    });

    const scale = document.createElement("span");
    scale.className = "tm-radar-scale";
    // The shared domain is stated, so the chart is never silently rescaled
    // without the reader knowing.
    scale.textContent = `outer ring ${formatShare(domain)}`;

    this.legend.replaceChildren(...items, scale);
  }

  private renderTable(profiles: readonly RadarProfile[]): void {
    const head = document.createElement("tr");
    head.append(th("Axis"), ...profiles.map((profile) => th(profile.label)));

    const rows = PARAMETER_AXIS_ORDER.map((key) => {
      const row = document.createElement("tr");
      row.append(th(axisLabel(key), "row"));
      for (const profile of profiles) {
        const score = profile.scores?.find((s) => s.key === key);
        const cell = document.createElement("td");
        cell.textContent = score ? formatShare(score.value) : "—";
        row.append(cell);
      }
      return row;
    });

    const thead = document.createElement("thead");
    thead.append(head);
    const tbody = document.createElement("tbody");
    tbody.append(...rows);

    this.table.replaceChildren(thead, tbody);
  }
}

function svgEl<K extends keyof SVGElementTagNameMap>(name: K): SVGElementTagNameMap[K] {
  return document.createElementNS("http://www.w3.org/2000/svg", name);
}

function th(text: string, scope: "col" | "row" = "col"): HTMLTableCellElement {
  const cell = document.createElement("th");
  cell.scope = scope;
  cell.textContent = text;
  return cell;
}
