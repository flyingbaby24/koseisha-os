import { cp, mkdir, readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const webDir = path.join(root, "www");
const docsDir = path.resolve(root, "..", "..", "docs", "jinnsp");

await mkdir(webDir, { recursive: true });

for (const name of ["manifest.webmanifest", "service-worker.js"]) {
  const source = path.join(docsDir, name);
  if (existsSync(source)) await cp(source, path.join(webDir, name));
}

for (const dir of ["data", "icons"]) {
  const source = path.join(docsDir, dir);
  if (existsSync(source)) {
    await cp(source, path.join(webDir, dir), { recursive: true });
  }
}

const html = await readFile(path.join(root, "src", "index.html"), "utf8");
const css = await readFile(path.join(root, "src", "styles.css"), "utf8");
const js = await readFile(path.join(root, "src", "app.js"), "utf8");

await writeFile(path.join(webDir, "index.html"), html);
await writeFile(path.join(webDir, "styles.css"), css);
await writeFile(path.join(webDir, "app.js"), js);

console.log(`Built JinnSP Android web assets: ${webDir}`);
