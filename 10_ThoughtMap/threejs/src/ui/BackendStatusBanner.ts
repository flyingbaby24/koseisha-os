import type { AppStateSnapshot } from "../app/AppState";

/**
 * One line above the search form saying what the backend is doing.
 *
 * Exists to keep three situations apart that a person would otherwise read as
 * "it's broken" (T6 #36, #37):
 *
 *   warming      the service is starting; semantic search works shortly
 *   unavailable  the service cannot be reached or cannot serve the corpus
 *   public demo  everything is fine, but the Personal Library is off here
 *
 * It never shows a progress percentage. The backend reports which check it is
 * waiting on, not how far through it is, and inventing a number would be
 * making one up.
 */
export class BackendStatusBanner {
  readonly element: HTMLElement;
  private readonly text: HTMLElement;
  private lastKey = "";

  constructor() {
    this.element = document.createElement("div");
    this.element.className = "tm-backend-banner";
    this.element.setAttribute("role", "status");
    this.element.hidden = true;

    this.text = document.createElement("span");
    this.text.className = "tm-backend-banner-text";
    this.element.append(this.text);
  }

  render(snapshot: AppStateSnapshot): void {
    const message = messageFor(snapshot);
    const key = message ? `${message.tone}:${message.text}` : "";

    // Cheap guard: this renders on every state change, and rewriting an
    // unchanged live region would make screen readers re-announce it.
    if (key === this.lastKey) {
      return;
    }
    this.lastKey = key;

    if (!message) {
      this.element.hidden = true;
      this.text.textContent = "";
      return;
    }

    this.element.hidden = false;
    this.element.dataset["tone"] = message.tone;
    this.text.textContent = message.text;
  }
}

export type BannerTone = "info" | "warning";

export interface BannerMessage {
  tone: BannerTone;
  text: string;
}

/** The banner's whole decision, extracted so it can be tested without a DOM. */
export function messageFor(snapshot: AppStateSnapshot): BannerMessage | null {
  if (snapshot.backendStatus === "warming") {
    return {
      tone: "info",
      text: snapshot.backendDetail
        ? `ThoughtMap is starting up. ${snapshot.backendDetail} Keyword search may be slower until it finishes.`
        : "ThoughtMap is starting up. Semantic search will be available shortly.",
    };
  }

  if (snapshot.backendStatus === "unavailable") {
    return {
      tone: "warning",
      text: snapshot.backendDetail
        ? `ThoughtMap is not fully available. ${snapshot.backendDetail}`
        : "ThoughtMap is not fully available right now.",
    };
  }

  if (snapshot.features.deployment_mode === "public-demo" && !snapshot.features.library_enabled) {
    return {
      tone: "info",
      text:
        "Public demo. Explore and search the full corpus; " +
        "saving to a Personal Library is disabled here.",
    };
  }

  return null;
}
