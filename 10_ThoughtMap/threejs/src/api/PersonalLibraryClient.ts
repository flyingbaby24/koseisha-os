import { ApiError, extractDetail, messageForStatus } from "./errors";
import type {
  DeleteSavedDocumentResponse,
  SaveDocumentRequest,
  SaveDocumentResponse,
  SavedDocument,
  SavedWorksResponse,
} from "./libraryTypes";
import { isSavedDocument } from "./libraryTypes";
import { DEFAULT_API_BASE_URL } from "./ThoughtMapApiClient";

export interface LibraryClientOptions {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
}

export interface LibraryRequestOptions {
  signal?: AbortSignal;
}

/**
 * Personal Library HTTP access, kept separate from the search client.
 *
 * The two have independent failure modes: the Personal database can be down
 * while search and the map are perfectly healthy, and vice versa. Separate
 * clients keep that distinction visible instead of collapsing it into one
 * "the API is broken" state.
 *
 * All identity handling stays here; UI components never build request bodies.
 */
export class PersonalLibraryClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;

  constructor(options: LibraryClientOptions = {}) {
    this.baseUrl = stripTrailingSlash(options.baseUrl ?? DEFAULT_API_BASE_URL);
    this.fetchImpl = options.fetchImpl ?? globalThis.fetch.bind(globalThis);
  }

  async loadSaved(identity: string, options: LibraryRequestOptions = {}): Promise<SavedDocument[]> {
    const email = requireIdentity(identity);
    const params = new URLSearchParams({ email });

    const response = await this.request<SavedWorksResponse>(
      `${this.baseUrl}/users/by-email/saved?${params.toString()}`,
      { method: "GET" },
      options,
    );

    // The contract calls this `works`; tolerate `items` too, which older
    // responses used, rather than showing an empty library on a shape change.
    const raw = response?.works ?? (response as unknown as { items?: SavedDocument[] })?.items;

    if (!Array.isArray(raw)) {
      throw new ApiError(
        "parse",
        "The Personal Library returned an unexpected response.",
        undefined,
        JSON.stringify(response)?.slice(0, 400),
      );
    }

    return raw.filter(isSavedDocument);
  }

  async saveDocument(
    request: SaveDocumentRequest,
    options: LibraryRequestOptions = {},
  ): Promise<SaveDocumentResponse> {
    const body: SaveDocumentRequest = {
      ...request,
      email: requireIdentity(request.email),
      source_type: request.source_type ?? "upload",
    };

    if (!body.doc_id?.trim()) {
      throw new ApiError("validation", "This document has no identifier to save.");
    }

    const response = await this.request<SaveDocumentResponse>(
      `${this.baseUrl}/users/by-email/save`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
      options,
    );

    if (!response || typeof response.saved !== "boolean") {
      throw new ApiError("parse", "The Personal Library returned an unexpected save response.");
    }

    return response;
  }

  async deleteSaved(
    identity: string,
    docId: string,
    options: LibraryRequestOptions = {},
  ): Promise<DeleteSavedDocumentResponse> {
    const email = requireIdentity(identity);
    const id = String(docId ?? "").trim();

    if (!id) {
      throw new ApiError("validation", "This document has no identifier to remove.");
    }

    // doc_ids contain a colon (`gutendex:doc_000446`), which must be percent
    // encoded in a path segment or the route will not match.
    const params = new URLSearchParams({ email });
    const response = await this.request<DeleteSavedDocumentResponse>(
      `${this.baseUrl}/users/by-email/saved/${encodeURIComponent(id)}?${params.toString()}`,
      { method: "DELETE" },
      options,
    );

    if (!response || typeof response.deleted !== "boolean") {
      throw new ApiError("parse", "The Personal Library returned an unexpected delete response.");
    }

    return response;
  }

  private async request<T>(
    url: string,
    init: RequestInit,
    options: LibraryRequestOptions,
  ): Promise<T> {
    let response: Response;

    try {
      const withSignal: RequestInit = { ...init, headers: { Accept: "application/json", ...(init.headers ?? {}) } };
      if (options.signal) {
        withSignal.signal = options.signal;
      }
      response = await this.fetchImpl(url, withSignal);
    } catch (cause) {
      if (isAbortError(cause, options.signal)) {
        throw new ApiError("aborted", "The Personal Library request was cancelled.");
      }
      throw new ApiError(
        "network",
        "Could not reach the Personal Library. Check that the backend is running.",
        undefined,
        String(cause),
      );
    }

    const text = await safeText(response);

    if (!response.ok) {
      const detail = extractDetail(text);
      const { kind } = messageForStatus(response.status, detail);
      throw new ApiError(kind, libraryMessage(response.status, detail), response.status, detail);
    }

    try {
      return JSON.parse(text) as T;
    } catch (cause) {
      throw new ApiError(
        "parse",
        "The Personal Library returned a response that could not be read.",
        response.status,
        `${String(cause)} :: ${text.slice(0, 300)}`,
      );
    }
  }
}

/** Library-specific wording; a 503 here is the Personal database, not the model. */
function libraryMessage(status: number, detail?: string): string {
  if (status === 400 || status === 422) {
    return detail
      ? `The Personal Library rejected the request: ${detail.split("\n")[0]}`
      : "The Personal Library rejected the request.";
  }
  if (status === 404) {
    return "That document is not in your Personal Library.";
  }
  if (status === 503) {
    return "The Personal Library is unavailable on this server.";
  }
  if (status >= 500) {
    return "The Personal Library could not complete that request.";
  }
  return `The Personal Library returned an unexpected status (${status}).`;
}

function requireIdentity(identity: string): string {
  const value = String(identity ?? "").trim();
  if (!value) {
    throw new ApiError("validation", "Set a Personal Library ID first.");
  }
  return value;
}

function isAbortError(cause: unknown, signal: AbortSignal | undefined): boolean {
  if (signal?.aborted) {
    return true;
  }
  return Boolean(cause && typeof cause === "object" && (cause as { name?: string }).name === "AbortError");
}

async function safeText(response: Response): Promise<string> {
  try {
    return await response.text();
  } catch {
    return "";
  }
}

function stripTrailingSlash(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}
