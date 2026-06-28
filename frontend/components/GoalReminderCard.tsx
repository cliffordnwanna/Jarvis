interface Props {
  goal_name: string
  days_stale: number
  urgency: string
  suggested_action: string
}

const urgencyColor: Record<string, string> = {
  high: 'text-red-400 border-red-500/30',
  medium: 'text-yellow-400 border-yellow-500/30',
  low: 'text-jarvis-muted border-jarvis-border',
}

export default function GoalReminderCard({ goal_name, days_stale, urgency, suggested_action }: Props) {
  return (
    <div className={`rounded-xl border bg-jarvis-surface p-4 w-72 ${urgencyColor[urgency] || urgencyColor.low}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-jarvis-muted uppercase tracking-widest">Goal</span>
        <span className={`text-xs font-medium capitalize ${urgencyColor[urgency]?.split(' ')[0]}`}>{urgency}</span>
      </div>
      <p className="text-sm font-medium text-jarvis-text mb-1">{goal_name}</p>
      <p className="text-xs text-jarvis-muted mb-3">Not touched in {days_stale} days</p>
      {suggested_action && (
        <p className="text-xs text-jarvis-text/80 italic">→ {suggested_action}</p>
      )}
    </div>
  )
}
