import type { AppState } from "./AppState";

/**
 * The only path by which anything becomes selected.
 *
 * The result list routes through here today; from T4 the 3D scene routes
 * through the same object, so a node click and a list click cannot disagree.
 */
export class SelectionController {
  constructor(private readonly state: AppState) {}

  select(docId: string): void {
    this.state.select(docId);
  }

  clear(): void {
    this.state.select(null);
  }

  toggle(docId: string): void {
    const current = this.state.getState().selectedDocId;
    this.state.select(current === docId ? null : docId);
  }

  get selectedDocId(): string | null {
    return this.state.getState().selectedDocId;
  }
}
