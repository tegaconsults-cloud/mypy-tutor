/**
 * MyPy Tutor — Service Worker
 *
 * Strategy:
 *  - App shell (HTML, manifest, sw.js, CDN assets) → Cache-first
 *  - API calls (/chat, /quiz/*, /course/*, /progress/*, /topics) → Network-first
 *    with a friendly offline fallback so the UI never shows a blank error.
 */

const CACHE_NAME    = 'mypy-tutor-v1';
const OFFLINE_URL   = '/';

// Resources to pre-cache on install (app shell)
const PRECACHE_URLS = [
  '/',
  '/manifest.json',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  // CDN assets — cached on first fetch, listed here for offline resilience
  'https://cdn.jsdelivr.net/npm/marked/marked.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/python.min.js',
];

// API path prefixes — always network-first
const API_PATHS = ['/chat', '/quiz', '/course', '/progress', '/topics', '/health', '/exercise'];

// ── Install: pre-cache app shell ─────────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS)).then(() => self.skipWaiting())
  );
});

// ── Activate: remove old caches ──────────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// ── Fetch: route requests ────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin + CDN requests
  if (request.method !== 'GET' && !isApiRequest(url.pathname)) {
    // POST/non-GET API calls: network-only with offline JSON fallback
    if (request.method === 'POST') {
      event.respondWith(networkWithOfflineFallback(request));
      return;
    }
    return;
  }

  if (isApiRequest(url.pathname)) {
    // Network-first for API
    event.respondWith(networkFirst(request));
  } else {
    // Cache-first for app shell & static assets
    event.respondWith(cacheFirst(request));
  }
});

// ── Strategies ───────────────────────────────────────────────────────────────

function isApiRequest(pathname) {
  return API_PATHS.some(p => pathname.startsWith(p));
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    // Return cached index as fallback for navigation
    const fallback = await caches.match(OFFLINE_URL);
    return fallback || new Response('Offline', { status: 503 });
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
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

async function networkWithOfflineFallback(request) {
  try {
    return await fetch(request);
  } catch {
    return new Response(
      JSON.stringify({ error: "You're offline. Please reconnect to send messages." }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
