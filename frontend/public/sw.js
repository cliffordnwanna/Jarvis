// Service Worker for JARVIS PWA
const CACHE_NAME = "jarvis-v2-1.0.0"
const urlsToCache = [
  "/",
  "/manifest.json",
]

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(urlsToCache)
    })
  )
})

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName)
          }
        })
      )
    })
  )
})

self.addEventListener("fetch", (event) => {
  // For API calls, always fetch from network
  if (event.request.url.includes("/agent") || event.request.url.includes("/context") || event.request.url.includes("/memory")) {
    event.respondWith(fetch(event.request))
    return
  }

  // For everything else, use cache-first strategy
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request)
    })
  )
})
