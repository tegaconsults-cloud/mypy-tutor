/**
 * MyPy Tutor — Service Worker v3
 *
 * Cache strategy:
 *  - App shell (HTML, manifest, icons, CDN assets) → Cache-first, update in background
 *  - API calls (POST/GET to backend routes) → Network-first, offline JSON fallback
 *  - Navigation requests → Cache-first, serve cached shell if offline
 */

const CACHE_VERSION = 'mypy-tutor-v3';
const OFFLINE_URL   = '/';

// App shell to pre-cache on install
const PRECACHE_URLS = [
  '/',
  '/manifest.json',
  '/sw.js',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  'https://cdn.jsdelivr.net/npm/marked/marked.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/python.min.js',
];

// All backend API prefixes — always network-first
const API_PREFIXES = [
  '/chat', '/quiz', '/course', '/progress', '/topics',
  '/health', '/exercise', '/feedback', '/auth', '/certificate',
  '/courses',
];

function isApiRequest(pathname) {
  return API_PREFIXES.some(p => pathname.startsWith(p));
}

// ── Install ───────────────────────────────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_VERSION)
      .then(cache => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

// ── Activate: purge old caches ────────────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE_VERSION).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// ── Fetch ─────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-http(s) requests (chrome-extension, etc.)
  if (!url.protocol.startsWith('http')) return;

  if (isApiRequest(url.pathname)) {
    // API: always try network first
    if (request.method === 'POST') {
      event.respondWith(networkOnlyWithFallback(request));
    } else {
      event.respondWith(networkFirst(request));
    }
  } else if (request.mode === 'navigate') {
    // Page navigation: cache-first → fallback to cached shell
    event.respondWith(navigationHandler(request));
  } else {
    // Static assets: cache-first → fetch and cache
    event.respondWith(cacheFirst(request));
  }
});

// ── Strategies ────────────────────────────────────────────────────────────────

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok && response.status < 400) {
      const cache = await caches.open(CACHE_VERSION);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const fallback = await caches.match(OFFLINE_URL);
    return fallback || new Response('Offline', { status: 503 });
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_VERSION);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(
      JSON.stringify({ error: "You're offline. Please reconnect to continue learning." }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

async function networkOnlyWithFallback(request) {
  try {
    return await fetch(request);
  } catch {
    return new Response(
      JSON.stringify({ error: "You're offline. Please reconnect to send messages." }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

async function navigationHandler(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_VERSION);
      cache.put(request, response.clone());
      return response;
    }
  } catch { /* offline */ }
  const cached = await caches.match(OFFLINE_URL);
  return cached || new Response('<h1>Offline</h1><p>Please reconnect to use MyPy Tutor.</p>',
    { status: 503, headers: { 'Content-Type': 'text/html' } });
}
