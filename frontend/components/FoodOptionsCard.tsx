import { Clock, ExternalLink, MapPin } from "lucide-react"

interface FoodOption {
  name: string
  distance_m: number
  estimated_delivery_min: number
  open_until?: string
}

interface FoodOptionsCardProps {
  reason: string
  time_context: string
  options: FoodOption[]
}

export function FoodOptionsCard(props: FoodOptionsCardProps) {
  return (
    <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-white/[0.02] p-4">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-white">{props.reason}</h3>
        <p className="text-xs text-white/50">{props.time_context}</p>
      </div>

      <div className="space-y-2">
        {props.options.slice(0, 3).map((option, idx) => (
          <div
            key={idx}
            className="rounded-xl border border-white/10 bg-black/20 p-3 flex items-start justify-between hover:border-white/20 transition-colors"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{option.name}</p>
              <div className="flex items-center gap-3 mt-1 text-xs text-white/50">
                <div className="flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {(option.distance_m / 1000).toFixed(1)} km
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {option.estimated_delivery_min} min
                </div>
              </div>
              {option.open_until && <p className="text-xs text-white/40 mt-1">Open until {option.open_until}</p>}
            </div>
            <button className="text-white/50 hover:text-white ml-2" aria-label="Open option">
              <ExternalLink className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
