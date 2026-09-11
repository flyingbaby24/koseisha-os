import { defineConfig } from "vitest/config";

// The Python FastAPI adapter stays the backend. In dev we proxy to it so the
// browser talks to one origin and the API's CORS settings do not have to change.
const API_TARGET = process.env.THOUGHTMAP_API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  // Relative asset URLs, so `dist/` can be served from a subpath
  // (https://host/thoughtmap/) as readily as from a domain root, without a
  // rebuild (T6 §31).
  base: "./",
  server: {
    port: 5273,
    proxy: {
      "/api": {
        target: API_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  preview: {
    port: 5274,
    proxy: {
      // `vite preview` serves the real production bundle. Without the same
      // proxy the deployment-like check would have to run against a different
      // origin than production does, which is the configuration most likely to
      // hide a CORS mistake.
      "/api": {
        target: API_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  build: {
    outDir: "dist",
    // Source maps are emitted but not referenced from the minified bundle, so
    // browsers never fetch 3 MB of map on a normal load while the files remain
    // available for debugging a deployed build.
    sourcemap: "hidden",
    // The entry chunk is now well under the default 500 kB; three.js is a
    // separate chunk fetched with the scene, so this stays a real warning
    // rather than one that is always on.
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        manualChunks: {
          // One stable vendor chunk for three.js. It changes only when the
          // dependency is upgraded, so a returning visitor keeps it cached
          // across application deploys — which matters more than its size,
          // since it is the largest single asset (T6 §28).
          three: ["three"],
        },
      },
    },
  },
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
  },
});
