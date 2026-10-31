import type { AppStateSnapshot } from "./AppState";

/**
 * doc_ids that have a node in the loaded projection.
 *
 * A search result can exist without a map position (the projection may
 * predate it); the list and the detail view say so instead of offering a
 * camera move to nowhere. Built once per loaded map — keyed on the node array
 * itself, which is replaced, never mutated — so panels can ask on every
 * render for free.
 *
 * Null while no map is loaded: "not in the map" is then unknown, and nothing
 * should be labelled as missing from a map that has not arrived.
 */
const cache = new WeakMap<object, ReadonlySet<string>>();

export function mapMembership(snapshot: AppStateSnapshot): ReadonlySet<string> | null {
  const nodes = snapshot.mapNodes;
  if (nodes.length === 0) {
    return null;
  }
  let ids = cache.get(nodes);
  if (!ids) {
    ids = new Set(nodes.map((node) => node.doc_id));
    cache.set(nodes, ids);
  }
  return ids;
}
