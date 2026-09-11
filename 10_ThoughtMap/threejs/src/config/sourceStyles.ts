/**
 * Visual identity per source namespace, defined once.
 *
 * The map renders every projected document, including sources the T2 search
 * selector does not list. An unrecognised source must still draw — a new
 * namespace appearing in the corpus is a data event, not an error — so lookups
 * always fall back rather than throwing.
 */

export interface SourceStyle {
  /** Linear-ish sRGB triple in 0..1, ready for a Three.js color attribute. */
  color: [number, number, number];
  label: string;
}

/** Restrained palette: distinguishable at point size, none overwhelming. */
const SOURCE_STYLES: Readonly<Record<string, SourceStyle>> = {
  gutendex: { color: [0.42, 0.76, 1.0], label: "Gutendex" },
  user_suno: { color: [1.0, 0.62, 0.42], label: "Suno" },
  user_note: { color: [0.62, 0.94, 0.7], label: "Note" },
  zip: { color: [0.83, 0.66, 1.0], label: "Zip import" },
};

/** Anything not listed above. Neutral, still clearly a document. */
export const FALLBACK_SOURCE_STYLE: SourceStyle = {
  color: [0.72, 0.76, 0.84],
  label: "Other",
};

export function sourceStyle(source: string | undefined | null): SourceStyle {
  const key = (source ?? "").trim().toLowerCase();
  return SOURCE_STYLES[key] ?? FALLBACK_SOURCE_STYLE;
}

export function knownSources(): string[] {
  return Object.keys(SOURCE_STYLES);
}

/** Count documents per source, for the map legend. */
export function summariseSources(
  nodes: ReadonlyArray<{ source: string }>,
): Array<{ source: string; label: string; count: number; color: [number, number, number] }> {
  const counts = new Map<string, number>();
  for (const node of nodes) {
    const key = (node.source ?? "").trim().toLowerCase() || "unknown";
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([source, count]) => {
      const style = sourceStyle(source);
      return { source, label: style.label, count, color: style.color };
    });
}
