import { buildWww, wwwDir } from "./build-common.mjs";

await buildWww();
console.log(`Built Android web assets: ${wwwDir}`);
