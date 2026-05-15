import { Cloud, CloudRain, Droplets, Sun, Wind } from "lucide-react"

interface WeatherCardProps {
  condition: string
  temp_c: number
  feels_like_c: number
  humidity_pct: number
  rain_prob_1h: number
  city: string
}

export function WeatherCard(props: WeatherCardProps) {
  const icon = (() => {
    const c = props.condition.toLowerCase()
    if (c.includes("rain")) return <CloudRain className="w-10 h-10 text-sky-300" />
    if (c.includes("cloud")) return <Cloud className="w-10 h-10 text-slate-300" />
    return <Sun className="w-10 h-10 text-amber-300" />
  })()

  return (
    <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-white/[0.02] p-4">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-white truncate">{props.city}</h3>
          <p className="text-xs text-white/50 truncate">{props.condition}</p>
        </div>
        <div className="opacity-90">{icon}</div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div>
          <p className="text-2xl font-semibold text-white">{Math.round(props.temp_c)}°C</p>
          <p className="text-xs text-white/50">Feels like {Math.round(props.feels_like_c)}°C</p>
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Droplets className="w-4 h-4 text-white/50" />
            <span className="text-sm text-white/80">{props.humidity_pct}% humidity</span>
          </div>
          <div className="flex items-center gap-2">
            <Wind className="w-4 h-4 text-white/50" />
            <span className="text-sm text-white/80">{props.rain_prob_1h}% rain (1h)</span>
          </div>
        </div>
      </div>

      <div className="w-full bg-white/5 rounded-full h-2 overflow-hidden">
        <div className="bg-sky-400 h-full transition-all" style={{ width: `${props.rain_prob_1h}%` }} />
      </div>
    </div>
  )
}
