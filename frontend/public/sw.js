// Service worker — Phase 2 will add push notification support
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))
self.addEventListener('fetch', (event) => {
  // Pass through all requests for now
  event.respondWith(fetch(event.request))
})
