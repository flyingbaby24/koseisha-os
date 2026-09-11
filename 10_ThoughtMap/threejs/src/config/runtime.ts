/**
 * Where this build points and what it is allowed to show.
 *
 * Two different things, deliberately separated:
 *
 * - **Build-time** (`VITE_*`): the API base URL. It has to be baked in because
 *   the page needs it before it can ask anything.
 * - **Run-time** (`GET /config`): what the *server* offers — deployment mode,
 *   whether the Personal Library exists. The server is the authority on that,
 *   so the frontend asks rather than assuming (T6 §45).
 *
 * Nothing here hard-codes localhost. A deployment sets the variable; it never
 * edits a source file (T6 §32).
 */

export type DeploymentMode = "development" | "public-demo" | "production";

export interface DeploymentFeatures {
  deployment_mode: DeploymentMode;
  library_enabled: boolean;
  diagnostics_enabled: boolean;
  semantic_search_enabled: boolean;
  corpus_version: string;
}

/**
 * Same-origin `/api` by default.
 *
 * In dev, Vite proxies it to the FastAPI adapter. In a same-origin production
 * deployment the reverse proxy does the same thing, so the common case needs
 * no configuration at all. A separately hosted API sets
 * `VITE_THOUGHTMAP_API_BASE_URL` to its absolute origin.
 */
export const API_BASE_URL: string = readEnv("VITE_THOUGHTMAP_API_BASE_URL", "/api");

/**
 * What to assume before `/config` answers.
 *
 * The library defaults to **off**. If the request fails we would rather hide a
 * feature that exists than offer one that does not: a Save button that 404s is
 * a worse first impression than no Save button, and on a public deployment the
 * library is off anyway.
 */
export const DEFAULT_FEATURES: DeploymentFeatures = {
  deployment_mode: "production",
  library_enabled: false,
  diagnostics_enabled: false,
  semantic_search_enabled: true,
  corpus_version: "",
};

function readEnv(key: string, fallback: string): string {
  // import.meta.env is statically replaced at build time; the guard keeps this
  // usable from Node-based tests where it is undefined.
  const env = (import.meta as { env?: Record<string, string | undefined> }).env;
  const value = env?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

/** Narrow an untrusted `/config` payload to the shape the UI relies on. */
export function parseFeatures(payload: unknown): DeploymentFeatures {
  if (!payload || typeof payload !== "object") {
    return DEFAULT_FEATURES;
  }

  const record = payload as Record<string, unknown>;
  const mode = record["deployment_mode"];

  return {
    deployment_mode: isDeploymentMode(mode) ? mode : DEFAULT_FEATURES.deployment_mode,
    library_enabled: record["library_enabled"] === true,
    diagnostics_enabled: record["diagnostics_enabled"] === true,
    // Absent means available: an older API that predates this field still
    // serves semantic search.
    semantic_search_enabled: record["semantic_search_enabled"] !== false,
    corpus_version:
      typeof record["corpus_version"] === "string" ? record["corpus_version"] : "",
  };
}

function isDeploymentMode(value: unknown): value is DeploymentMode {
  return value === "development" || value === "public-demo" || value === "production";
}
