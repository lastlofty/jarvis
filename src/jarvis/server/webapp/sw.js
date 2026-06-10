// Service worker для PWA Jarvis.
// Кэшируем оболочку приложения; API/WebSocket всегда идут в сеть.
const CACHE = "jarvis-pwa-v1";
const SHELL = ["./index.html", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // Никогда не кэшируем API и сокеты
  if (["/command", "/screenshot", "/ws", "/health"].some((p) => url.pathname.startsWith(p))) {
    return; // пусть идёт в сеть как обычно
  }
  // Оболочку — сначала из кэша, потом сеть
  e.respondWith(
    caches.match(e.request).then((hit) => hit || fetch(e.request))
  );
});
