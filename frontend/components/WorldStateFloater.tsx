"use client"
import { RefreshCw, X } from "lucide-react"

interface WorldStateFloaterProps {
  worldState: Record<string, any>
  lastUpdated: Date | null
  onRefresh: () => void
  onClose: () => void
}

function SignalRow({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null
  return (
    <div className="flex items-center justify-between gap-4 py-1.5 border-b border-white/5 last:border-0">
      <span className="text-white/40 text-xs">{label}</span>
      <span className="text-white/80 text-xs font-medium text-right">{value}</span>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <p className="text-white/25 text-[10px] uppercase tracking-widest mb-1 font-semibold">{title}</p>
      {children}
    </div>
  )
}

export function WorldStateFloater({ worldState, lastUpdated, onRefresh, onClose }: WorldStateFloaterProps) {
  const ws = worldState as any
  const loc = ws?.location ?? {}
  const temp = ws?.temporal ?? {}
  const env = ws?.environment?.weather ?? {}
  const dev = ws?.device ?? {}
  const cog = ws?.cognition ?? {}

  const city = loc.city ?? loc.city_name ?? loc.town ?? loc.district
  const country = loc.country ?? loc.country_code
  const lat = typeof loc.latitude === "number" ? loc.latitude?.toFixed(4) : null
  const lng = typeof loc.longitude === "number" ? loc.longitude?.toFixed(4) : null

  const ts = temp.timestamp ?? temp.iso ?? temp.local_time
  const timezone = temp.timezone

  const condition = env.condition ?? env.description
  const tempC = typeof env.temp_c === "number" ? `${Math.round(env.temp_c)}°C` : null
  const feelsLike = typeof env.feels_like_c === "number" ? `${Math.round(env.feels_like_c)}°C` : null
  const humidity = typeof env.humidity_pct === "number" ? `${Math.round(env.humidity_pct)}%` : null
  // forecast_1h_rain_prob is stored as 0-1 fraction; rain_prob_1h (if ever present) is 0-100
  const rainVal = env.forecast_1h_rain_prob ?? env.rain_prob_1h
  const rain = typeof rainVal === "number"
    ? `${Math.round(env.forecast_1h_rain_prob != null ? rainVal * 100 : rainVal)}%`
    : null

  const battery = typeof dev.battery_pct === "number" ? `${Math.round(dev.battery_pct)}%` : null
  const charging = typeof dev.charging === "boolean" ? (dev.charging ? "Yes" : "No") : null

  const cogLoad = cog.cognitive_load ?? cog.load
  const focus = cog.focus_score

  const updatedStr = lastUpdated
    ? new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit", second: "2-digit" }).format(lastUpdated)
    : "Never"

  return (
    <div className="fixed bottom-6 right-6 z-50 w-72 rounded-2xl border border-white/10 bg-[#0b1120]/95 backdrop-blur-xl shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <span className="text-xs font-semibold text-white/70 tracking-wide">WORLD STATE</span>
        <div className="flex items-center gap-1">
          <button
            onClick={onRefresh}
            title="Refresh"
            className="p-1.5 rounded-lg text-white/40 hover:text-white/70 hover:bg-white/[0.05] transition-colors"
          >
            <RefreshCw size={12} />
          </button>
          <button
            onClick={onClose}
            title="Close"
            className="p-1.5 rounded-lg text-white/40 hover:text-white/70 hover:bg-white/[0.05] transition-colors"
          >
            <X size={12} />
          </button>
        </div>
      </div>

      {/* Signals */}
      <div className="px-4 py-3 max-h-96 overflow-y-auto">
        {Object.keys(worldState).length === 0 ? (
          <p className="text-white/30 text-xs text-center py-4">No data yet — waiting for context push</p>
        ) : (
          <>
            <Section title="Location">
              <SignalRow label="City" value={city} />
              <SignalRow label="Country" value={country} />
              <SignalRow label="Coords" value={lat && lng ? `${lat}, ${lng}` : null} />
            </Section>

            <Section title="Time">
              <SignalRow label="Local time" value={ts ? new Date(ts).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" }) : null} />
              <SignalRow label="Timezone" value={timezone} />
            </Section>

            <Section title="Weather">
              <SignalRow label="Condition" value={condition} />
              <SignalRow label="Temperature" value={tempC} />
              <SignalRow label="Feels like" value={feelsLike} />
              <SignalRow label="Humidity" value={humidity} />
              <SignalRow label="Rain (1h)" value={rain} />
            </Section>

            <Section title="Device">
              <SignalRow label="Battery" value={battery} />
              <SignalRow label="Charging" value={charging} />
            </Section>

            {(cogLoad || focus) && (
              <Section title="Cognition">
                <SignalRow label="Cognitive load" value={cogLoad != null ? String(cogLoad) : null} />
                <SignalRow label="Focus score" value={focus != null ? String(focus) : null} />
              </Section>
            )}
          </>
        )}
      </div>

      {/* Footer — last updated */}
      <div className="px-4 py-2 border-t border-white/5">
        <p className="text-white/25 text-[10px]">Updated {updatedStr}</p>
      </div>
    </div>
  )
}
