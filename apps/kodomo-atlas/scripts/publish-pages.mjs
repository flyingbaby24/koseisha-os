/** Copy only this app's build into the existing repository's Pages directory. */
import assert from "node:assert/strict";
import { cp, lstat, realpath, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const app = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repository = path.resolve(app, "../..");
const docs = path.join(repository, "docs");
const target = path.join(docs, "kodomo-atlas");
assert.equal(path.relative(repository, app).replaceAll(path.sep, "/"), "apps/kodomo-atlas", "Run pages:build from apps/kodomo-atlas in koseisha-os");
await lstat(path.join(repository, ".git"));
await lstat(path.join(docs, "index.html"));
await lstat(path.join(app, "dist/index.html"));
assert.equal(path.resolve(target), path.resolve(docs, "kodomo-atlas"));
assert.equal(await realpath(docs), docs, "Refuse a symlinked publication directory");
const existing = await lstat(target).catch(error => { if (error.code === "ENOENT") return null; throw error; });
if (existing) {
  assert(!existing.isSymbolicLink(), "Refuse a symlinked app publication directory");
  assert.equal(await realpath(target), target);
  // The resolved, checked target is exclusively docs/kodomo-atlas, never the docs root.
  await rm(target, { recursive: true, force: true });
}
await cp(path.join(app, "dist"), target, { recursive: true });
console.log("Published this app's static build to docs/kodomo-atlas/");
