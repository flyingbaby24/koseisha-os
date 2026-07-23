const CACHE_NAME = "jinnsp-android-pwa-v3-icons";
const ASSETS = [
  "./",
  "./index.html",
  "./app.js",
  "./styles.css",
  "./manifest.webmanifest",
  "./data/library.json",
  "./data/playlists.json",
  "./icons/icon-jinnsp-v3-192.png",
  "./icons/icon-jinnsp-v3-512.png",
  "./icons/apple-touch-icon-v3.png",
  "./assets/mascot/idle.svg"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))));
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request)));
});

