const LAST_GPS_KEY = 'jarvis_last_gps'

interface SensorPayload {
  lat?: number
  lng?: number
  timezone: string
  device: {
    network_type: string
    platform: string
    headphones_connected: boolean
    screen_on: boolean
  }
}

async function getGps(): Promise<{ lat: number; lng: number } | null> {
  // 1. Try live GPS
  if (navigator.geolocation) {
    try {
      const pos = await new Promise<GeolocationPosition>((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          timeout: 5000,
          maximumAge: 60000,
          enableHighAccuracy: false,
        })
      )
      const coords = { lat: pos.coords.latitude, lng: pos.coords.longitude }
      localStorage.setItem(LAST_GPS_KEY, JSON.stringify(coords))
      return coords
    } catch (_) {}
  }

  // 2. Cached
  const cached = localStorage.getItem(LAST_GPS_KEY)
  if (cached) {
    try { return JSON.parse(cached) } catch (_) {}
  }

  // 3. Hardcoded Lagos default
  return { lat: 6.5244, lng: 3.3792 }
}

export async function collectSensors(): Promise<SensorPayload> {
  const [gps] = await Promise.allSettled([getGps()])
  const coords = gps.status === 'fulfilled' ? gps.value : null

  const connection = (navigator as any).connection || {}
  const platform = navigator.platform || 'web'

  return {
    lat: coords?.lat,
    lng: coords?.lng,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    device: {
      network_type: connection.type || 'unknown',
      platform: platform.toLowerCase().includes('mac') || platform.toLowerCase().includes('win')
        ? 'desktop'
        : 'mobile',
      headphones_connected: false,
      screen_on: !document.hidden,
    },
  }
}
