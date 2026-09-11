import type { ParameterScore } from "../api/types";
import { axisLabel } from "../config/searchOptions";
import { formatShare, maxParameterValue, orderParameters } from "./format";

/**
 * Compact Thought Composition readout: axis, bar, percentage.
 *
 * A deliberate T2 placeholder. The radar is T5 — this exists to prove the
 * restored `query_parameters` and `results[].parameters` data path end to end.
 *
 * Bars are scaled to the largest value in the set rather than to 1.0: ten axes
 * summing to 1.0 means a dominant axis still sits near 0.14, which against a
 * fixed 0-1 scale would render as ten near-invisible slivers.
 */
export class ParameterList {
  readonly element: HTMLElement;

  private readonly body: HTMLElement;
  private readonly emptyNote: HTMLElement;

  constructor(title: string, emptyMessage: string) {
    this.element = document.createElement("section");
    this.element.className = "tm-params";

    const heading = document.createElement("h3");
    heading.className = "tm-params-title";
    heading.textContent = title;

    this.body = document.createElement("div");
    this.body.className = "tm-params-body";

    this.emptyNote = document.createElement("p");
    this.emptyNote.className = "tm-note";
    this.emptyNote.textContent = emptyMessage;

    this.element.append(heading, this.emptyNote, this.body);
    this.render(null);
  }

  render(parameters: readonly ParameterScore[] | null | undefined): void {
    const ordered = orderParameters(parameters);

    if (ordered.length === 0) {
      this.body.replaceChildren();
      this.body.hidden = true;
      this.emptyNote.hidden = false;
      return;
    }

    this.emptyNote.hidden = true;
    this.body.hidden = false;

    const max = maxParameterValue(ordered);
    const rows = ordered.map((parameter) => this.buildRow(parameter, max));
    this.body.replaceChildren(...rows);
  }

  private buildRow(parameter: ParameterScore, max: number): HTMLElement {
    const row = document.createElement("div");
    row.className = "tm-param-row";

    const label = document.createElement("span");
    label.className = "tm-param-label";
    label.textContent = axisLabel(parameter.key);

    const track = document.createElement("span");
    track.className = "tm-param-track";

    const fill = document.createElement("span");
    fill.className = "tm-param-fill";
    const ratio = max > 0 ? parameter.value / max : 0;
    fill.style.width = `${Math.max(0, Math.min(1, ratio)) * 100}%`;
    track.append(fill);

    const value = document.createElement("span");
    value.className = "tm-param-value";
    // Display is a percentage; state keeps the 0.0-1.0 share.
    value.textContent = formatShare(parameter.value);

    row.append(label, track, value);
    return row;
  }
}
