interface CalEvent {
  title: string
  time: string
  location?: string
}

interface Props {
  events_today_json: string
  events_tomorrow_json: string
  free_blocks_json: string
}

export default function CalendarCard({ events_today_json, events_tomorrow_json, free_blocks_json }: Props) {
  const parse = (s: string): CalEvent[] => { try { return JSON.parse(s) } catch { return [] } }
  const today = parse(events_today_json)
  const tomorrow = parse(events_tomorrow_json)

  return (
    <div className="rounded-xl border border-jarvis-border bg-jarvis-surface p-4 w-72">
      <span className="text-xs text-jarvis-muted uppercase tracking-widest">Calendar</span>

      {today.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-jarvis-text mb-1.5">Today</p>
          {today.map((e, i) => (
            <div key={i} className="flex items-start gap-2 mb-1.5">
              <span className="text-xs text-jarvis-muted w-12 shrink-0">{e.time}</span>
              <span className="text-xs text-jarvis-text">{e.title}</span>
            </div>
          ))}
        </div>
      )}

      {tomorrow.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-jarvis-text mb-1.5">Tomorrow</p>
          {tomorrow.map((e, i) => (
            <div key={i} className="flex items-start gap-2 mb-1.5">
              <span className="text-xs text-jarvis-muted w-12 shrink-0">{e.time}</span>
              <span className="text-xs text-jarvis-text">{e.title}</span>
            </div>
          ))}
        </div>
      )}

      {today.length === 0 && tomorrow.length === 0 && (
        <p className="text-xs text-jarvis-muted mt-3">No events — calendar sync coming in Phase 2.</p>
      )}
    </div>
  )
}
