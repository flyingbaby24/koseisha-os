import type { PointTuple } from "leaflet";

/**
 * Padding for fitBounds that keeps a focused area clear of the legend and the
 * selection card when they span the map like a band (narrow/phone maps). Corner
 * overlays on wide maps only cover open sea in the national view, so they are ignored.
 */
export function fitPadding(
  map: HTMLElement | null,
  base: number,
): { paddingTopLeft: PointTuple; paddingBottomRight: PointTuple } {
  let top = base,
    bottom = base;
  const wrap = map?.parentElement;
  if (map && wrap) {
    const box = map.getBoundingClientRect();
    const band = (selector: string) => {
      const element = wrap.querySelector<HTMLElement>(selector);
      if (!element) return null;
      const rect = element.getBoundingClientRect();
      return rect.width > box.width * 0.75 ? rect : null;
    };
    const key = band(".map-key");
    if (key) top = Math.max(top, key.bottom - box.top + 10);
    const card = band(".map-selection-info");
    if (card) bottom = Math.max(bottom, box.bottom - card.top + 10);
    // Never let overlays leave less than 40% of the map height for the area itself.
    const limit = box.height * 0.6;
    if (top + bottom > limit) {
      const scale = limit / (top + bottom);
      top *= scale;
      bottom *= scale;
    }
  }
  return {
    paddingTopLeft: [base, Math.round(top)],
    paddingBottomRight: [base, Math.round(bottom)],
  };
}
