'use client'

import { useEffect, useState } from 'react'
import { Sun, Users, Gift, Target, ChevronRight } from 'lucide-react'

interface BriefingData {
  briefing: string
  birthdays_soon: Array<{ name: string; days_until: number; person_id: string }>
  overdue_contacts: Array<{ name: string; strength: string; person_id: string }>
  events_today: Array<{ title: string; event_type: string }>
  stale_goals: string[]
  generated_at: string
}

interface MorningBriefCardProps {
  token?: string
  onPersonClick?: (personId: string) => void
  // Legacy CopilotKit generative UI action props
  birthdays_json?: string
  overdue_json?: string
  follow_ups_json?: string
}

export function MorningBriefCard({ token, onPersonClick, birthdays_json, overdue_json }: MorningBriefCardProps) {
  const [data, setData] = useState<BriefingData | null>(null)
  const [loading, setLoading] = useState(!!token)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    if (!token) return
    const hour = new Date().getHours()
    if (hour < 5 || hour >= 12) { setLoading(false); return }

    fetch(`${process.env.NEXT_PUBLIC_JARVIS_URL}/briefing/morning`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [token])

  // CopilotKit generative UI fallback — render from props
  if (!token && (birthdays_json || overdue_json)) {
    const birthdays = birthdays_json ? JSON.parse(birthdays_json) : []
    const overdue = overdue_json ? JSON.parse(overdue_json) : []
    return (
      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
        <div className="flex items-center gap-2 mb-2">
          <Sun size={14} className="text-amber-400" />
          <span className="text-xs font-medium text-amber-400">Morning Briefing</span>
        </div>
        {birthdays.length > 0 && (
          <p className="text-sm text-gray-300">🎂 {birthdays.map((b: any) => b.name).join(', ')}</p>
        )}
        {overdue.length > 0 && (
          <p className="text-sm text-gray-400 mt-1">Reach out: {overdue.map((p: any) => p.name).join(', ')}</p>
        )}
      </div>
    )
  }

  const hour = new Date().getHours()
  if (loading || !data || hour < 5 || hour >= 12) return null

  return (
    <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 mb-4">
      <div className="flex items-center gap-2 mb-3">
        <Sun size={14} className="text-amber-400" />
        <span className="text-xs font-medium text-amber-400">Morning Briefing</span>
        <span className="text-xs text-gray-600 ml-auto">
          {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
        </span>
      </div>

      <p className="text-sm text-gray-300 leading-relaxed mb-3">{data.briefing}</p>

      {!expanded ? (
        <button
          onClick={() => setExpanded(true)}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          <ChevronRight size={12} />
          See details
        </button>
      ) : (
        <div className="space-y-3 mt-3 pt-3 border-t border-white/5">
          {data.birthdays_soon.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-1.5">
                <Gift size={12} className="text-pink-400" />
                <span className="text-xs text-pink-400 font-medium">Birthdays soon</span>
              </div>
              {data.birthdays_soon.map(b => (
                <button
                  key={b.person_id}
                  onClick={() => onPersonClick?.(b.person_id)}
                  className="flex items-center justify-between w-full text-left px-2 py-1 rounded-lg hover:bg-white/5 transition-colors"
                >
                  <span className="text-sm text-gray-300">{b.name}</span>
                  <span className="text-xs text-gray-500">
                    {b.days_until === 0 ? 'Today 🎂' : b.days_until === 1 ? 'Tomorrow' : `In ${b.days_until} days`}
                  </span>
                </button>
              ))}
            </div>
          )}

          {data.overdue_contacts.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-1.5">
                <Users size={12} className="text-orange-400" />
                <span className="text-xs text-orange-400 font-medium">Reach out to</span>
              </div>
              {data.overdue_contacts.slice(0, 3).map(p => (
                <button
                  key={p.person_id}
                  onClick={() => onPersonClick?.(p.person_id)}
                  className="flex items-center justify-between w-full text-left px-2 py-1 rounded-lg hover:bg-white/5 transition-colors"
                >
                  <span className="text-sm text-gray-300">{p.name}</span>
                  <span className={`text-xs ${p.strength === 'cold' ? 'text-red-400' : 'text-orange-400'}`}>
                    {p.strength}
                  </span>
                </button>
              ))}
            </div>
          )}

          {data.stale_goals.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-1.5">
                <Target size={12} className="text-blue-400" />
                <span className="text-xs text-blue-400 font-medium">Goals needing attention</span>
              </div>
              {data.stale_goals.map((g, i) => (
                <p key={i} className="text-sm text-gray-400 px-2">· {g}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default MorningBriefCard
