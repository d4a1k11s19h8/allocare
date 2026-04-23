/* ═══════════════════════════════════════════════════════════
   AlloCare — Service Worker (PWA Offline Support)
   Caches HTML, CSS, JS, and API responses for offline use
   ═════════════════════════════════════════════════════════ */

const CACHE_NAME = "allocare-v4";
const STATIC_ASSETS = [
  "/",
  "/index.html",
  "/css/design-system.css",
  "/css/dashboard.css",
  "/css/components.css",
  "/css/animations.css",
  "/js/config.js",
  "/js/auth.js",
  "/js/api-service.js",
  "/js/offline.js",
  "/js/map.js",
  "/js/dashboard.js",
  "/js/upload.js",
  "/js/matching.js",
  "/manifest.json",
];

const API_CACHE = "allocare-api-v4";
const CACHEABLE_API = ["/api/needs", "/api/volunteers", "/api/health", "/api/analytics"];

// ── Install: Pre-cache static assets ────────────────────────
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// ── Activate: Clean old caches ──────────────────────────────
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME && k !== API_CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// ── Fetch: Network-first for API, Cache-first for static ────
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET and external requests
  if (event.request.method !== "GET") return;
  if (url.origin !== self.location.origin) return;

  // API requests: network-first with cache fallback
  if (CACHEABLE_API.some(api => url.pathname.startsWith(api))) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const clone = response.clone();
          caches.open(API_CACHE).then(cache => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Static assets: cache-first with network fallback
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      });
    }).catch(() => {
      if (event.request.destination === "document") {
        return caches.match("/index.html");
      }
    })
  );
});
