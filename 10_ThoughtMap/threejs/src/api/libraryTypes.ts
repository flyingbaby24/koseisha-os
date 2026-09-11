/**
 * Mirrors the Personal Library half of `web/api/schemas.py`.
 *
 * The email in these calls is a **lookup key, not authentication**. The backend
 * trims, lowercases and SHA-256 hashes it to derive a user key; possessing an
 * address proves nothing. The UI must not present it as a sign-in.
 */

import type { ParameterScore } from "./types";

export interface SavedDocument {
  doc_id: string;
  title: string;
  author: string;
  source: string;
  category?: string;
  url?: string | null;
  source_url?: string | null;
  saved_at?: string;
  original_doc_id?: string;
  model_name?: string;
  parameters?: ParameterScore[] | null;
}

/** `GET /users/by-email/saved` — the key is `works`, kept stable for Unity. */
export interface SavedWorksResponse {
  works: SavedDocument[];
}

export interface SaveDocumentResponse {
  saved: boolean;
  duplicate?: boolean;
  item: SavedDocument;
}

export interface DeleteSavedDocumentResponse {
  deleted: boolean;
  doc_id: string;
}

/**
 * What the client sends to save a document.
 *
 * `source_type` stays `"upload"` — the default — so the backend stores the
 * metadata as sent. Setting `"official"` would make it re-look-up the doc_id in
 * the official database, which is a slower path and unnecessary here because
 * the frontend already holds the canonical metadata.
 */
export interface SaveDocumentRequest {
  email: string;
  doc_id: string;
  title: string;
  author: string;
  source: string;
  category?: string;
  url?: string;
  source_url?: string;
  original_doc_id?: string;
  parameters?: ParameterScore[] | null;
  source_type?: string;
}

export function isSavedDocument(value: unknown): value is SavedDocument {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<SavedDocument>;
  return typeof candidate.doc_id === "string" && candidate.doc_id.length > 0;
}
