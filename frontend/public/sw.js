// Service worker for Marea Alta (ticket #31).
//
// The site is a small two-document app. The service worker keeps the app shell,
// the last visited pages, hashed build assets and the public API reads so a bad
// connection still shows the hours and menu. It is intentionally conservative:
//
// * only GET requests are handled, so forms and admin writes pass straight
//   through and are never replayed from a cache;
// * `/admin` is never cached, and only the five public API reads are cached;
// * navigations and API reads are network-first, so an online visitor always
//   gets live data and the cache is only a fallback;
// * hashed assets and uploaded images are cache-first because their URLs are
//   immutable.
//
// Bump VERSION when the shell or caching rules change. Activate deletes every
// cache from an older version, which also drops stale HTML after a deploy.

const VERSION = 'v1';

const SHELL_CACHE = `marea-alta-shell-${VERSION}`;
const PAGE_CACHE = `marea-alta-pages-${VERSION}`;
const ASSET_CACHE = `marea-alta-assets-${VERSION}`;
const API_CACHE = `marea-alta-api-${VERSION}`;

const OFFLINE_URL = '/offline.html';
const SHELL_URLS = [
  '/',
  '/menu',
  OFFLINE_URL,
  '/manifest.json',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

// The only API reads the homepage uses. Admin reads such as `/api/rsvps` and
// `/api/logs/*` are deliberately absent: they must never land on disk.
const PUBLIC_API = new Set([
  '/api/schedule',
  '/api/closed-days',
  '/api/menu',
  '/api/notices',
  '/api/special-events',
]);

const IMMUTABLE_PREFIXES = ['/assets/', '/icons/', '/uploads/'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(SHELL_CACHE);
      // One failed URL (for example the API is up but a route is not) must not
      // fail the whole install.
      await Promise.allSettled(SHELL_URLS.map((url) => cache.add(url)));
      await self.skipWaiting();
    })()
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keep = new Set([SHELL_CACHE, PAGE_CACHE, ASSET_CACHE, API_CACHE]);
      const names = await caches.keys();
      await Promise.all(names.filter((name) => !keep.has(name)).map((name) => caches.delete(name)));
      await self.clients.claim();
    })()
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Never let the worker sit between the admin panel and the server.
  if (url.pathname === '/sw.js' || url.pathname.startsWith('/admin')) return;

  if (request.mode === 'navigate') {
    event.respondWith(navigation(request));
    return;
  }

  if (url.pathname.startsWith('/api/')) {
    if (PUBLIC_API.has(url.pathname)) {
      event.respondWith(networkFirst(request, API_CACHE));
    }
    return;
  }

  if (IMMUTABLE_PREFIXES.some((prefix) => url.pathname.startsWith(prefix))) {
    event.respondWith(cacheFirst(request, ASSET_CACHE));
    return;
  }

  event.respondWith(staleWhileRevalidate(request, ASSET_CACHE));
});

async function navigation(request) {
  const cache = await caches.open(PAGE_CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) await cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached =
      (await cache.match(request)) ||
      (await caches.match(request)) ||
      (await caches.match(OFFLINE_URL));
    if (cached) return cached;
    throw err;
  }
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response.ok) await cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw err;
  }
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  if (response.ok) await cache.put(request, response.clone());
  return response;
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  const network = fetch(request)
    .then((response) => {
      if (response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => null);

  return cached || (await network) || Response.error();
}
