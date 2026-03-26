const CACHE = 'mamacare-v4';

const STATIC_ASSETS = [
  '/',
  '/static/manifest.json',
  '/static/js/marked.min.js',
  '/static/icons/icon-48.png',
  '/static/icons/icon-72.png',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

// Install — cache core assets
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activate — delete old caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// ── Push notifications ──────────────────────────────────────────────────────
self.addEventListener('push', e => {
  let data = {};
  if (e.data) {
    try { data = e.data.json(); }
    catch (_) { data = { title: 'MamaCare', body: e.data.text() }; }
  }
  e.waitUntil(
    self.registration.showNotification(data.title || 'MamaCare', {
      body:  data.body  || '',
      icon:  '/static/icons/icon-192.png',
      badge: '/static/icons/icon-48.png',
      data:  { url: data.url || '/' },
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = e.notification.data?.url || '/';
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(wins => {
      for (const win of wins) {
        if (win.url.includes(url) && 'focus' in win) return win.focus();
      }
      return clients.openWindow(url);
    })
  );
});

// Fetch strategy:
// - Static assets (JS/CSS/images/fonts) → cache-first
// - HTML pages & API calls → network-first with cache fallback
self.addEventListener('fetch', e => {
  const { request } = e;
  const url = new URL(request.url);

  // Skip non-GET and cross-origin
  if (request.method !== 'GET' || url.origin !== location.origin) return;

  // Skip admin and API polling routes
  if (url.pathname.startsWith('/admin') || url.pathname.includes('/poll/')) return;

  const isStatic = url.pathname.startsWith('/static/');

  if (isStatic) {
    // Cache-first for static assets
    e.respondWith(
      caches.match(request).then(cached => cached || fetch(request).then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(request, clone));
        return res;
      }))
    );
  } else {
    // Network-first for pages
    e.respondWith(
      fetch(request)
        .then(res => {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(request, clone));
          return res;
        })
        .catch(() => caches.match(request).then(cached => cached || caches.match('/')))
    );
  }
});
