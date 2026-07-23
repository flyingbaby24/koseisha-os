import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const projectRoot = path.resolve(__dirname, "..");
export const srcDir = path.join(projectRoot, "src");
export const wwwDir = path.join(projectRoot, "www");

const jsInputs = [
  "core/constants.js",
  "core/csv.js",
  "core/backup.js",
  "core/library.js",
  "platform/adapter.js",
  "playback/playback.js",
  "app.js"
];

const copyEntries = [
  "index.html",
  "styles.css",
  "manifest.webmanifest",
  "service-worker.js",
  "assets",
  "icons",
  "data"
];

export async function pathExists(target) {
  try {
    await fs.access(target);
    return true;
  } catch {
    return false;
  }
}

async function copyIfExists(from, to) {
  if (!(await pathExists(from))) return;
  const stat = await fs.stat(from);
  if (stat.isDirectory()) {
    await fs.cp(from, to, { recursive: true });
  } else {
    await fs.copyFile(from, to);
  }
}

export async function buildWww() {
  await fs.rm(wwwDir, { recursive: true, force: true });
  await fs.mkdir(wwwDir, { recursive: true });

  for (const entry of copyEntries) {
    await copyIfExists(path.join(srcDir, entry), path.join(wwwDir, entry));
  }

  const chunks = [];
  for (const input of jsInputs) {
    const file = path.join(srcDir, input);
    chunks.push(`/* ${input} */\n${await fs.readFile(file, "utf8")}`);
  }
  await fs.writeFile(path.join(wwwDir, "app.js"), `${chunks.join("\n\n")}\n`, "utf8");

  return wwwDir;
}

export async function copyWebPublic(targetDir) {
  await fs.rm(targetDir, { recursive: true, force: true });
  await fs.mkdir(targetDir, { recursive: true });
  const allowed = [
    "index.html",
    "app.js",
    "styles.css",
    "manifest.webmanifest",
    "service-worker.js",
    "assets",
    "icons",
    "data"
  ];
  for (const entry of allowed) {
    await copyIfExists(path.join(wwwDir, entry), path.join(targetDir, entry));
  }
}
