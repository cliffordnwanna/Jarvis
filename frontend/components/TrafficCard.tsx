interface Props {
  congestion: string
  eta_now_minutes: number
  usual_eta_minutes: number
  delay_minutes: number
  route_label: string
}

const congestionColor: Record<string, string> = {
  low: 'text-green-400',
  moderate: 'text-yellow-400',
  heavy: 'text-orange-400',
  severe: 'text-red-400',
}

export default function TrafficCard({ congestion, eta_now_minutes, usual_eta_minutes, delay_minutes, route_label }: Props) {
  return (
    <div className="rounded-xl border border-jarvis-border bg-jarvis-surface p-4 w-72">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-jarvis-muted uppercase tracking-widest">Traffic</span>
        <span className={`text-xs font-medium capitalize ${congestionColor[congestion] || 'text-jarvis-muted'}`}>
          {congestion}
        </span>
      </div>
      <p className="text-xs text-jarvis-muted mb-3">{route_label}</p>
      <div className="space-y-1.5 text-xs">
        <div className="flex justify-between">
          <span className="text-jarvis-muted">ETA now</span>
          <span className="text-jarvis-text font-medium">{eta_now_minutes} min</span>
        </div>
        <div className="flex justify-between">
          <span className="text-jarvis-muted">Usual</span>
          <span className="text-jarvis-text">{usual_eta_minutes} min</span>
        </div>
        {delay_minutes > 0 && (
          <div className="flex justify-between">
            <span className="text-jarvis-muted">Delay</span>
            <span className="text-orange-400">+{delay_minutes} min</span>
          </div>
        )}
      </div>
    </div>
  )
}
