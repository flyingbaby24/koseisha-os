import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../src/api/errors";
import { buildSearchParams, ThoughtMapApiClient } from "../src/api/ThoughtMapApiClient";
import type { SearchResponse } from "../src/api/types";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function textResponse(body: string, status: number): Response {
  return new Response(body, { status });
}

const EMPTY: SearchResponse = { results: [] };

function clientWith(fetchImpl: typeof fetch, baseUrl = "/api"): ThoughtMapApiClient {
  return new ThoughtMapApiClient({ baseUrl, fetchImpl });
}

/** Capture the URL the client requested. */
function recordingClient(response: Response = jsonResponse(EMPTY)) {
  const urls: string[] = [];
  const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
    urls.push(String(input));
    return response.clone();
  }) as unknown as typeof fetch;
  return { client: clientWith(fetchImpl), urls, fetchImpl };
}

describe("buildSearchParams", () => {
  it("sends the semantic mode with query and top", () => {
    const params = buildSearchParams({ q: "Plato", mode: "semantic", top: 10 });
    expect(params.get("q")).toBe("Plato");
    expect(params.get("mode")).toBe("semantic");
    expect(params.get("top")).toBe("10");
  });

  it("sends the keyword mode", () => {
    expect(buildSearchParams({ q: "Plato", mode: "keyword" }).get("mode")).toBe("keyword");
  });

  it("sends the hybrid mode", () => {
    expect(buildSearchParams({ q: "Plato", mode: "hybrid" }).get("mode")).toBe("hybrid");
  });

  it("includes source and filter when set", () => {
    const params = buildSearchParams({ q: "Plato", source: "gutendex", filter: "philosophy" });
    expect(params.get("source")).toBe("gutendex");
    expect(params.get("filter")).toBe("philosophy");
  });

  it("omits empty source and filter rather than sending blanks", () => {
    const params = buildSearchParams({ q: "Plato", source: "", filter: "  " });
    expect(params.has("source")).toBe(false);
    expect(params.has("filter")).toBe(false);
  });

  it("omits 'all', matching what the backend treats as no filter", () => {
    const params = buildSearchParams({ q: "Plato", source: "all", filter: "ALL" });
    expect(params.has("source")).toBe(false);
    expect(params.has("filter")).toBe(false);
  });

  it("passes optional target_doc_id and user_email through", () => {
    const params = buildSearchParams({
      q: "Plato",
      target_doc_id: "gutendex:doc_000631",
      user_email: "reader@example.com",
    });
    expect(params.get("target_doc_id")).toBe("gutendex:doc_000631");
    expect(params.get("user_email")).toBe("reader@example.com");
  });

  it("percent-encodes values that would otherwise break the query string", () => {
    const encoded = buildSearchParams({
      q: "Plato & Aristotle?",
      source: "user_suno",
      target_doc_id: "gutendex:doc_1",
    }).toString();

    expect(encoded).toContain("q=Plato+%26+Aristotle%3F");
    expect(encoded).toContain("target_doc_id=gutendex%3Adoc_1");
  });

  it("encodes non-ASCII queries", () => {
    expect(buildSearchParams({ q: "哲学" }).toString()).toBe("q=%E5%93%B2%E5%AD%A6");
  });
});

describe("ThoughtMapApiClient", () => {
  it("requests /search under the configured base URL", async () => {
    const { client, urls } = recordingClient();
    await client.search({ q: "Plato", mode: "semantic" });
    expect(urls[0]).toBe("/api/search?q=Plato&mode=semantic");
  });

  it("strips a trailing slash from the base URL", async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(EMPTY)) as unknown as typeof fetch;
    const client = clientWith(fetchImpl, "http://127.0.0.1:8000/");
    expect(client.buildUrl("/health", new URLSearchParams())).toBe("http://127.0.0.1:8000/health");
  });

  it("returns the parsed response", async () => {
    const payload: SearchResponse = {
      results: [
        {
          doc_id: "gutendex:doc_1",
          title: "The Republic",
          author: "Plato",
          source: "gutendex",
          similarity: 0.736,
        },
      ],
      query_parameters: [{ key: "philosophy", value: 0.1392 }],
    };
    const fetchImpl = vi.fn(async () => jsonResponse(payload)) as unknown as typeof fetch;

    const response = await clientWith(fetchImpl).search({ q: "Plato" });
    expect(response.results).toHaveLength(1);
    expect(response.results[0]?.similarity).toBe(0.736);
    expect(response.query_parameters?.[0]?.value).toBe(0.1392);
  });

  it("reads /health", async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({ status: "ok", backend: "csv" }),
    ) as unknown as typeof fetch;
    await expect(clientWith(fetchImpl).health()).resolves.toEqual({ status: "ok", backend: "csv" });
  });

  it("translates 422 into a validation error carrying the API detail", async () => {
    const body = { detail: [{ msg: "String should have at least 1 character" }] };
    const fetchImpl = vi.fn(async () => jsonResponse(body, 422)) as unknown as typeof fetch;

    const error = await clientWith(fetchImpl)
      .search({ q: "" })
      .catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).kind).toBe("validation");
    expect((error as ApiError).status).toBe(422);
    expect((error as ApiError).message).toContain("at least 1 character");
  });

  it("translates 503 into the semantic-unavailable message", async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({ detail: "sentence-transformers is not installed" }, 503),
    ) as unknown as typeof fetch;

    const error = (await clientWith(fetchImpl)
      .search({ q: "Plato", mode: "semantic" })
      .catch((caught: unknown) => caught)) as ApiError;

    expect(error.kind).toBe("unavailable");
    expect(error.message).toContain("Semantic search is unavailable");
    expect(error.message).toContain("keyword search still works");
  });

  it("translates 500 into a server error without leaking the body", async () => {
    const fetchImpl = vi.fn(async () =>
      textResponse("Traceback (most recent call last): ...", 500),
    ) as unknown as typeof fetch;

    const error = (await clientWith(fetchImpl)
      .search({ q: "Plato" })
      .catch((caught: unknown) => caught)) as ApiError;

    expect(error.kind).toBe("server");
    expect(error.message).not.toContain("Traceback");
    // The raw body is still available for the console.
    expect(error.detail).toContain("Traceback");
  });

  it("translates a transport failure into a network error", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }) as unknown as typeof fetch;

    const error = (await clientWith(fetchImpl)
      .search({ q: "Plato" })
      .catch((caught: unknown) => caught)) as ApiError;

    expect(error.kind).toBe("network");
    expect(error.message).toContain("Could not reach the ThoughtMap API");
  });

  it("rejects a response that is not valid JSON", async () => {
    const fetchImpl = vi.fn(async () => textResponse("<html>gateway</html>", 200)) as unknown as typeof fetch;

    const error = (await clientWith(fetchImpl)
      .search({ q: "Plato" })
      .catch((caught: unknown) => caught)) as ApiError;

    expect(error.kind).toBe("parse");
  });

  it("rejects a 200 response missing the results array", async () => {
    const fetchImpl = vi.fn(async () => jsonResponse({ query_parameters: [] })) as unknown as typeof fetch;

    const error = (await clientWith(fetchImpl)
      .search({ q: "Plato" })
      .catch((caught: unknown) => caught)) as ApiError;

    expect(error.kind).toBe("parse");
  });

  it("reports an aborted request as an abort, not a network failure", async () => {
    const controller = new AbortController();
    const fetchImpl = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      init?.signal?.throwIfAborted();
      throw new DOMException("The operation was aborted.", "AbortError");
    }) as unknown as typeof fetch;

    controller.abort();
    const error = (await clientWith(fetchImpl)
      .search({ q: "Plato" }, { signal: controller.signal })
      .catch((caught: unknown) => caught)) as ApiError;

    expect(error.isAborted).toBe(true);
    expect(error.kind).toBe("aborted");
  });

  it("forwards the abort signal to fetch", async () => {
    const controller = new AbortController();
    const fetchImpl = vi.fn(async () => jsonResponse(EMPTY)) as unknown as typeof fetch;

    await clientWith(fetchImpl).search({ q: "Plato" }, { signal: controller.signal });

    const init = vi.mocked(fetchImpl).mock.calls[0]?.[1] as RequestInit;
    expect(init.signal).toBe(controller.signal);
  });
});
