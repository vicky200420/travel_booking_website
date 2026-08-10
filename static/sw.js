/* TravelBooking service worker — network-first with static cache fallback.
   IMPORTANT: '/static/*' is cache-first. When you deploy changes to static
   assets (css/js/images/videos), BUMP CACHE_NAME below (v1 -> v2 -> ...).
   On the next activation the old cache is purged so browsers (especially
   Chrome) reload the updated files instead of serving the stale copy. */
const CACHE_NAME = 'travelbooking-static-v2';
const CACHE_PREFIX = 'travelbooking-static-';
const OFFLINE_PAGE = '/offline/';

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.add(OFFLINE_PAGE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME && key.startsWith(CACHE_PREFIX))
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Cache-first for versioned static assets.
  if (url.origin === self.location.origin && url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then((cached) => {
        const network = fetch(request).then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return response;
        });
        return cached || network;
      })
    );
    return;
  }

  // Network-first for navigation so users always get fresh content.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      }).catch(() =>
        caches.match(request).then((cached) =>
          cached || caches.match(OFFLINE_PAGE)
        )
      )
    );
  }
});
