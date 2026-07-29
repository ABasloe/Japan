// Bump this whenever the cached shell should be thrown away.
const CACHE_NAME = 'trip-map-v5';

// Only the entry point is pre-cached, as an OFFLINE FALLBACK. The generated
// pages (index/iceland/spain/japan) are deliberately NOT pre-cached: they change on
// every deploy, and a stale copy of them is exactly the bug this avoids.
// Resolve the shell relative to the worker so project-site deployments such as
// https://user.github.io/Japan/ do not fall back to the account root.
const APP_ROOT = new URL('./', self.location).pathname;
const ASSETS_TO_CACHE = [APP_ROOT];

self.addEventListener('install', event => {
    // Take over immediately instead of waiting for every tab to close — without
    // this an updated worker sits in "waiting" and the old one keeps serving the
    // previous build indefinitely.
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(ASSETS_TO_CACHE))
            .catch(err => console.error('Pre-cache failed', err))
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys()
            .then(names => Promise.all(
                names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n))
            ))
            .then(() => self.clients.claim())   // control open pages right away
    );
});

self.addEventListener('fetch', event => {
    const req = event.request;
    if (req.method !== 'GET') return;
    const url = new URL(req.url);

    // Map tiles: cache-first (they don't change and are expensive to refetch).
    if (url.hostname.includes('tile.openstreetmap.org') ||
        url.hostname.includes('basemaps.cartocdn.com') ||
        url.hostname.includes('arcgisonline.com')) {
        event.respondWith(
            caches.match(req).then(hit => hit || fetch(req).then(res => {
                if (res && res.status === 200) {
                    const copy = res.clone();
                    caches.open(CACHE_NAME).then(c => c.put(req, copy));
                }
                return res;
            }).catch(() => undefined))
        );
        return;
    }

    // HTML documents: always go to the network, and only fall back to a cached
    // copy when genuinely offline.
    const isDoc = req.mode === 'navigate' ||
                  (req.headers.get('accept') || '').includes('text/html');
    if (isDoc) {
        event.respondWith(
            fetch(req, { cache: 'no-store' })
                .then(res => {
                    if (res && res.status === 200) {
                        const copy = res.clone();
                        caches.open(CACHE_NAME).then(c => c.put(req, copy));
                    }
                    return res;
                })
                .catch(() => caches.match(req).then(hit => hit || caches.match(APP_ROOT)))
        );
        return;
    }

    // Everything else: network-first, cache as a fallback.
    event.respondWith(
        fetch(req).then(res => {
            if (res && res.status === 200) {
                const copy = res.clone();
                caches.open(CACHE_NAME).then(c => c.put(req, copy));
            }
            return res;
        }).catch(() => caches.match(req))
    );
});
