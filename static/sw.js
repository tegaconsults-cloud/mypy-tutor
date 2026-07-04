/**
 * MyPy Tutor — Service Worker v7
 *
 * Cache strategy:
 *  - Same-origin static assets (HTML, CSS, icons, manifest) → Cache-first
 *  - Same-origin API calls → Network-first (POST = network-only)
 *  - Navigation requests → Network-first, cached shell offline fallback
 *  - Cross-origin requests (Google, CDN, analytics) → PASS THROUGH (never cache)
 *    Caching cross-origin URLs would violate CSP connect-src and cause console errors.
 */

const CACHE_VERSION = 'mypy-tutor-v7';
const OFFLINE_URL   = '/';

// Only pre-cache same-origin assets we fully control
const PRECACHE_URLS = [
  '/',
  '/manifest.json',
  '/premium.css',
  '/icons/logo-mpt.png',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

// Same-origin API path prefixes — always network-first
const API_PREFIXES = [
  '/chat', '/quiz', '/course', '/progress', '/topics',
  '/health', '/exercise', '/feedback', '/auth', '/certificate',
  '/courses', '/referral', '/coupons', '/invoices', '/conversations',
  '/assignments', '/lessons', '/admin', '/webhooks', '/supabase',
  '/history',
];

// Domains the SW must NEVER intercept — pass straight through to the browser
// (these are external resources that violate CSP if fetched via SW)
const PASSTHROUGH_ORIGINS = new Set([
  'accounts.google.com',
  'oauth2.googleapis.com',
  'www.googletagmanager.com',
  'www.google-analytics.com',
  'analytics.google.com',
  'region1.google-analytics.com',
  'lh3.googleusercontent.com',
  'fonts.googleapis.com',
  'fonts.gstatic.com',
  'cdn.jsdelivr.net',
  'cdnjs.cloudflare.com',
]);

const APP_ORIGIN = self.location.origin;

function isApiRequest(pathname) {
  return API_PREFIXES.some(p => pathname.startsWith(p));
}

function isSameOrigin(url) {
  return url.origin === APP_ORIGIN;
}

function isPassthrough(url) {
  return PASSTHROUGH_ORIGINS.has(url.hostname) || !isSameOrigin(url);
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

  // Skip non-http(s) requests (chrome-extension, data:, etc.)
  if (!request.url.startsWith('http')) return;

  const url = new URL(request.url);

  // ── RULE 1: Always pass through external/cross-origin requests ────────────
  // Never intercept Google Auth, Analytics, CDN, profile images, fonts, etc.
  // Doing so triggers CSP connect-src violations in the console.
  if (isPassthrough(url)) return;

  // ── RULE 2: API calls (same-origin) ──────────────────────────────────────
  if (isApiRequest(url.pathname)) {
    if (request.method === 'POST') {
      event.respondWith(networkOnlyWithFallback(request));
    } else {
      event.respondWith(networkFirst(request));
    }
    return;
  }

  // ── RULE 3: Page navigations ──────────────────────────────────────────────
  if (request.mode === 'navigate') {
    event.respondWith(navigationHandler(request));
    return;
  }

  // ── RULE 4: Same-origin static assets ────────────────────────────────────
  event.respondWith(cacheFirst(request));
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
  return cached || new Response(
    '<h1>Offline</h1><p>Please reconnect to use MyPy Tutor.</p>',
    { status: 503, headers: { 'Content-Type': 'text/html' } }
  );
}
