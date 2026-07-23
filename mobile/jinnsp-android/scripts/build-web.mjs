import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildWww, copyWebPublic, projectRoot, wwwDir } from "./build-common.mjs";

const repoRoot = path.resolve(projectRoot, "..", "..");
const docsTarget = path.join(repoRoot, "docs", "jinnsp-android");

await buildWww();
await copyWebPublic(docsTarget);
console.log(`Built shared web assets: ${wwwDir}`);
console.log(`Published GitHub Pages bundle: ${docsTarget}`);
