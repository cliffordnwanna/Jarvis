export interface DevicePayload {
  battery_pct: number
  charging: boolean
  headphones_connected: boolean
  network_type: string
  platform: string
  screen_on: boolean
}

export interface SensorPayload {
  lat?: number
  lng?: number
  device: DevicePayload
  gps_available: boolean
  timezone?: string
}

// Home coordinates — used only when GPS is unavailable and no cached fix exists.
// Change these if your primary base changes.
const HOME_LAT = 6.5244   // Lagos, Nigeria
const HOME_LNG = 3.3792

const LOCATION_CACHE_KEY = "jarvis_last_location"

function saveLocationCache(lat: number, lng: number) {
  try {
    localStorage.setItem(LOCATION_CACHE_KEY, JSON.stringify({ lat, lng, ts: Date.now() }))
  } catch {}
}

function loadLocationCache(): { lat: number; lng: number } | null {
  try {
    const raw = localStorage.getItem(LOCATION_CACHE_KEY)
    if (!raw) return null
    const { lat, lng } = JSON.parse(raw)
    if (typeof lat === "number" && typeof lng === "number") return { lat, lng }
  } catch {}
  return null
}

export async function collectSensors(options?: { allowGpsPrompt?: boolean; gpsTimeoutMs?: number }): Promise<SensorPayload> {
  const allowGpsPrompt = options?.allowGpsPrompt ?? false
  const gpsTimeoutMs = options?.gpsTimeoutMs ?? 8000
  // GPS — three-tier fallback, never uses IP geolocation (VPN-poisoned).
  // Tier 1: live GPS from device
  // Tier 2: last cached GPS fix from localStorage
  // Tier 3: hardcoded home coordinates (Lagos)
  let lat: number | undefined
  let lng: number | undefined
  let gps_available = false

  try {
    if (!allowGpsPrompt) {
      try {
        const result = await navigator.permissions.query({ name: "geolocation" })
        if (result.state !== "granted") throw new Error("gps_not_granted")
      } catch {
        throw new Error("gps_not_granted")
      }
    }

    const position = await new Promise<GeolocationPosition>((resolve, reject) =>
      navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: gpsTimeoutMs, enableHighAccuracy: true })
    )
    lat = position.coords.latitude
    lng = position.coords.longitude
    gps_available = true
    saveLocationCache(lat, lng)
  } catch {
    // GPS unavailable — use cached real location or hardcoded home.
    // Never call IP geolocation: VPN routes it to the VPN server's country.
    const cached = loadLocationCache()
    if (cached) {
      lat = cached.lat
      lng = cached.lng
    } else {
      lat = HOME_LAT
      lng = HOME_LNG
    }
  }

  // Battery
  const battery = await (navigator as any).getBattery?.() ?? { level: 1, charging: false }

  // Network
  const conn = (navigator as any).connection ?? {}

  // Headphones (check audio output labels)
  let headphones = false
  try {
    const devices = await navigator.mediaDevices.enumerateDevices()
    headphones = devices.some(d => d.kind === "audiooutput" && d.label.toLowerCase().includes("airpod"))
  } catch {}

  return {
    ...(lat !== undefined && lng !== undefined ? { lat, lng } : {}),
    gps_available,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    device: {
      battery_pct: Math.round((battery.level ?? 1) * 100),
      charging: battery.charging ?? false,
      headphones_connected: headphones,
      network_type: conn.type ?? "unknown",
      platform: /iPhone|iPad/.test(navigator.userAgent) ? "ios" : /Android/.test(navigator.userAgent) ? "android" : "web",
      screen_on: !document.hidden,
    },
  }
}

/**
 * Push sensor data to backend. Returns true if GPS was available.
 * Call this whenever you want to refresh location — it triggers a browser
 * permission prompt if the user hasn't decided yet.
 */
export async function pushSensors(
  backendUrl: string,
  options?: { allowGpsPrompt?: boolean; gpsTimeoutMs?: number },
): Promise<{ gpsAvailable: boolean; locationAvailable: boolean; error?: string }> {
  try {
    const payload = await collectSensors(options)
    await fetch(`${backendUrl}/context`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    const locationAvailable = typeof payload.lat === "number" && typeof payload.lng === "number"
    return { gpsAvailable: payload.gps_available, locationAvailable }
  } catch (e) {
    console.warn("Sensor push failed:", e)
    return { gpsAvailable: false, locationAvailable: false, error: e instanceof Error ? e.message : String(e) }
  }
}

/** Check current GPS permission state without triggering a prompt. */
export async function getGpsPermissionState(): Promise<PermissionState | "unsupported"> {
  try {
    const result = await navigator.permissions.query({ name: "geolocation" })
    return result.state
  } catch {
    return "unsupported"
  }
}
