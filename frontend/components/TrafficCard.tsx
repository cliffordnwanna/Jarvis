import { AlertTriangle, Clock, Navigation } from "lucide-react"

interface TrafficCardProps {
  congestion: string
  eta_now_minutes: number
  usual_eta_minutes: number
  delay_minutes: number
  route_label: string
}

export function TrafficCard(props: TrafficCardProps) {
  const isBad = props.congestion.toLowerCase() === "heavy" || props.delay_minutes > 10
  const badge = isBad ? "border-red-400/30 text-red-200" : "border-emerald-400/30 text-emerald-200"

  return (
    <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-white/[0.02] p-4">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Navigation className="w-4 h-4 text-white/60" />
            <h3 className="text-sm font-semibold text-white truncate">{props.route_label}</h3>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] ${badge}`}>
              {props.congestion.charAt(0).toUpperCase() + props.congestion.slice(1)}
            </span>
            {isBad && <AlertTriangle className="w-4 h-4 text-red-300" />}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-white/10 bg-black/20 p-3">
          <p className="text-xl font-semibold text-white">{props.eta_now_minutes} min</p>
          <p className="text-xs text-white/50 mt-1">ETA now</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/20 p-3">
          <p className="text-xl font-semibold text-white">{props.usual_eta_minutes} min</p>
          <div className="mt-1 flex items-center gap-1 text-white/50">
            <Clock className="w-3 h-3" />
            <p className="text-xs">Usual</p>
          </div>
        </div>
      </div>

      {props.delay_minutes > 0 && (
        <div className="mt-3 flex items-center justify-between rounded-xl border border-white/10 bg-black/20 px-3 py-2">
          <p className="text-xs text-white/70">Delay</p>
          <p className={`text-xs font-semibold ${isBad ? "text-red-200" : "text-white/80"}`}>
            +{props.delay_minutes} min
          </p>
        </div>
      )}
    </div>
  )
}
