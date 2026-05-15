import { AlertCircle, Target } from "lucide-react"

interface GoalReminderCardProps {
  goal_name: string
  days_stale: number
  urgency: string
  suggested_action: string
}

export function GoalReminderCard(props: GoalReminderCardProps) {
  const isHigh = props.urgency.toLowerCase() === "high"
  const badge = isHigh ? "border-red-400/30 text-red-200" : "border-amber-400/30 text-amber-200"

  return (
    <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-white/[0.02] p-4">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <Target className="w-4 h-4 text-white/60" />
          <h3 className="text-sm font-semibold text-white truncate">{props.goal_name}</h3>
        </div>
        {isHigh && <AlertCircle className="w-4 h-4 text-red-300" />}
      </div>

      <div className="flex items-center gap-2 mb-3">
        <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${badge}`}>
          {props.days_stale}d stale
        </span>
        <span className="text-[11px] px-2.5 py-1 rounded-full border border-white/10 text-white/60 capitalize">
          {props.urgency}
        </span>
      </div>

      <p className="text-sm text-white/80 leading-relaxed">{props.suggested_action}</p>
    </div>
  )
}
