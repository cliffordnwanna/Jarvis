const LAST_GPS_KEY = 'jarvis_last_gps'

interface GpsResult {
  lat: number
  lng: number
  accurate: boolean
  error: string | null
}

interface SensorPayload {
  lat?: number
  lng?: number
  timezone: string
  location_accurate?: boolean
  device: {
    network_type: string
    platform: string
    headphones_connected: boolean
    screen_on: boolean
  }
}

async function getGps(): Promise<GpsResult> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve({ lat: 6.5244, lng: 3.3792, accurate: false, error: 'Geolocation not supported' })
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coords = { lat: pos.coords.latitude, lng: pos.coords.longitude }
        localStorage.setItem(LAST_GPS_KEY, JSON.stringify(coords))
        resolve({ ...coords, accurate: true, error: null })
      },
      (err) => {
        const cached = localStorage.getItem(LAST_GPS_KEY)
        if (cached) {
          try {
            const coords = JSON.parse(cached)
            resolve({ ...coords, accurate: true, error: `Using last known location: ${err.message}` })
            return
          } catch (_) {}
        }
        resolve({ lat: 6.5244, lng: 3.3792, accurate: false, error: err.message })
      },
      { timeout: 8000, maximumAge: 60000, enableHighAccuracy: false }
    )
  })
}

export async function collectSensors(): Promise<SensorPayload> {
  const gps = await getGps()

  const connection = (navigator as any).connection || {}
  const platform = navigator.platform || 'web'

  return {
    lat: gps.lat,
    lng: gps.lng,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    location_accurate: gps.accurate,
    device: {
      network_type: connection.type || 'unknown',
      platform:
        platform.toLowerCase().includes('mac') || platform.toLowerCase().includes('win')
          ? 'desktop'
          : 'mobile',
      headphones_connected: false,
      screen_on: !document.hidden,
    },
  }
}
