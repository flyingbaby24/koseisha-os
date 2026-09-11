/**
 * HTTP failures translated into something the UI can show a person.
 *
 * The raw detail is kept on the error for the console; `message` is what
 * reaches the screen. Stack traces and backend tracebacks never do.
 */

export type ApiErrorKind =
  | "network"
  | "aborted"
  | "validation"
  | "unavailable"
  | "server"
  | "parse"
  | "unknown";

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | undefined;
  /** Raw body or cause, for the developer console only. */
  readonly detail: string | undefined;

  constructor(kind: ApiErrorKind, message: string, status?: number, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.detail = detail;
  }

  get isAborted(): boolean {
    return this.kind === "aborted";
  }
}

/**
 * Which endpoint failed. 503 in particular means two entirely different things
 * — no embedding model for `/search`, no generated projection for `/map` — so
 * the message has to know which one it is describing.
 */
export type ApiContext = "search" | "map";

/** Map an HTTP status onto a message that means something to a person. */
export function messageForStatus(
  status: number,
  detail?: string,
  context: ApiContext = "search",
): { kind: ApiErrorKind; message: string } {
  const isMap = context === "map";
  const subject = isMap ? "thought space request" : "search request";

  if (status === 422 || status === 400) {
    return {
      kind: "validation",
      message: detail
        ? `The ${subject} was rejected: ${firstLine(detail)}`
        : `The ${subject} was rejected. Check the query and options.`,
    };
  }

  if (status === 503) {
    return {
      kind: "unavailable",
      message: isMap
        ? "The thought space has not been generated on this server yet."
        : "Semantic search is unavailable on this server. " +
          "The embedding model is not installed — keyword search still works.",
    };
  }

  if (status === 404) {
    return {
      kind: "server",
      message: isMap
        ? "This API address does not serve a thought space."
        : "The search endpoint was not found at this API address.",
    };
  }

  if (status >= 500) {
    return {
      kind: "server",
      message: isMap
        ? "The ThoughtMap API could not return the thought space."
        : "The ThoughtMap API failed to complete the search.",
    };
  }

  return { kind: "unknown", message: `The API returned an unexpected status (${status}).` };
}

/**
 * FastAPI returns `{"detail": ...}` on error, where detail is a string for
 * HTTPException and a list of field errors for validation failures.
 */
export function extractDetail(body: string): string | undefined {
  const trimmed = body.trim();
  if (!trimmed) {
    return undefined;
  }

  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (parsed && typeof parsed === "object" && "detail" in parsed) {
      const detail = (parsed as { detail: unknown }).detail;
      if (typeof detail === "string") {
        return detail;
      }
      if (Array.isArray(detail)) {
        const messages = detail
          .map((item) =>
            item && typeof item === "object" && "msg" in item
              ? String((item as { msg: unknown }).msg)
              : null,
          )
          .filter((msg): msg is string => Boolean(msg));
        if (messages.length > 0) {
          return messages.join("; ");
        }
      }
      return JSON.stringify(detail);
    }
  } catch {
    // Not JSON — fall through and use the raw text.
  }

  return trimmed;
}

function firstLine(text: string): string {
  const line = text.split("\n", 1)[0] ?? text;
  return line.length > 200 ? `${line.slice(0, 200)}...` : line;
}
