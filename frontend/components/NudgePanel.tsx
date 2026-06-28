'use client'

import { useEffect, useState, useCallback } from 'react'
import { X, CloudRain, Calendar, Target, Users, Gift, Bell } from 'lucide-react'
import { MorningBriefCard } from './MorningBriefCard'
import type { Nudge } from '@/types'

interface NudgePanelProps {
  token: string
  onPersonClick?: (personId: string) => void
  onGoalTouch?: (message: string) => void
  onClose?: () => void
  // Legacy props from original page.tsx wiring
  nudges?: Nudge[]
  onDismiss?: (id: string) => void
}

const NUDGE_ICONS: Record<string, React.ReactNode> = {
  weather: <CloudRain size={14} className="text-blue-400" />,
  morning_briefing: <CloudRain size={14} className="text-green-400" />,
  calendar: <Calendar size={14} className="text-purple-400" />,
  goal: <Target size={14} className="text-blue-400" />,
  relationship_birthday: <Gift size={14} className="text-pink-400" />,
  relationship_cooling: <Users size={14} className="text-orange-400" />,
  relationship_followup: <Users size={14} className="text-green-400" />,
}

const PRIORITY_ORDER = ['high', 'medium', 'low']

const PRIORITY_BORDER: Record<string, string> = {
  high: 'border-red-500/30',
  medium: 'border-yellow-500/20',
  low: 'border-white/5',
}

const NUDGE_TYPE_STYLE: Record<string, { border: string; bg: string; dot: string }> = {
  morning_briefing: {
    border: 'border-green-500/30',
    bg: 'bg-green-500/5',
    dot: 'bg-green-400',
  },
}

export function NudgePanel({ token, onPersonClick, onGoalTouch, onClose }: NudgePanelProps) {
  const [nudges, setNudges] = useState<Nudge[]>([])
  const [dismissing, setDismissing] = useState<Set<string>>(new Set())

  const fetchNudges = useCallback(async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_JARVIS_URL}/nudges`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) return
      const data: Nudge[] = await res.json()
      const sorted = data.sort((a, b) => {
        const pa = PRIORITY_ORDER.indexOf(a.priority)
        const pb = PRIORITY_ORDER.indexOf(b.priority)
        if (pa !== pb) return pa - pb
        return new Date(b.delivered_at).getTime() - new Date(a.delivered_at).getTime()
      })
      setNudges(sorted.slice(0, 8))
    } catch {}
  }, [token])

  useEffect(() => {
    fetchNudges()
    const interval = setInterval(fetchNudges, 60_000)
    return () => clearInterval(interval)
  }, [fetchNudges])

  const dismiss = useCallback(async (id: string) => {
    setDismissing(prev => new Set(prev).add(id))
    try {
      await fetch(`${process.env.NEXT_PUBLIC_JARVIS_URL}/nudges/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      setNudges(prev => prev.filter(n => n.id !== id))
    } catch {}
    setDismissing(prev => { const s = new Set(prev); s.delete(id); return s })
  }, [token])

  return (
    <aside className="w-80 flex flex-col h-full border-l border-jarvis-border bg-jarvis-surface">
      <div className="flex items-center justify-between px-4 py-3 border-b border-jarvis-border">
        <span className="text-sm font-medium text-jarvis-text">Nudges</span>
        {onClose && (
          <button onClick={onClose} className="text-jarvis-muted hover:text-jarvis-text transition-colors">
            <X size={16} />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
        <MorningBriefCard token={token} onPersonClick={onPersonClick} />

        {nudges.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Bell size={22} className="text-gray-700 mb-3" />
            <p className="text-sm text-gray-600">No nudges right now.</p>
            <p className="text-xs text-gray-700 mt-1">JARVIS will notify you when something needs attention.</p>
          </div>
        ) : (
          nudges.map(nudge => {
            const typeStyle = NUDGE_TYPE_STYLE[nudge.nudge_type]
            const borderClass = typeStyle ? typeStyle.border : (PRIORITY_BORDER[nudge.priority] || 'border-white/5')
            const bgClass = typeStyle ? typeStyle.bg : (nudge.priority === 'high' ? 'bg-red-500/5' : 'bg-white/[0.02]')
            const dotColor = typeStyle ? typeStyle.dot : 'bg-red-500'
            return (
            <div
              key={nudge.id}
              className={`
                relative rounded-xl border p-3 transition-all duration-200
                ${borderClass} ${bgClass}
                ${dismissing.has(nudge.id) ? 'opacity-0 scale-95' : 'opacity-100 scale-100'}
              `}
            >
              {(nudge.priority === 'high' || typeStyle) && (
                <div className={`absolute top-2 left-2 w-1.5 h-1.5 rounded-full ${dotColor}`} />
              )}
              <button
                onClick={() => dismiss(nudge.id)}
                className="absolute top-2 right-2 text-gray-600 hover:text-gray-400 transition-colors"
              >
                <X size={12} />
              </button>

              <div className="flex items-start gap-2 pr-4 pl-1">
                <div className="mt-0.5 flex-shrink-0">
                  {NUDGE_ICONS[nudge.nudge_type] || <Bell size={14} className="text-gray-400" />}
                </div>
                <p className="text-sm text-gray-300 leading-snug">{nudge.message}</p>
              </div>

              <div className="flex gap-2 mt-2 ml-6">
                {nudge.nudge_type.startsWith('relationship') && nudge.person_id && (
                  <button
                    onClick={() => onPersonClick?.(nudge.person_id!)}
                    className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    View profile →
                  </button>
                )}
                {nudge.nudge_type === 'goal' && (
                  <button
                    onClick={() => { onGoalTouch?.(nudge.message); dismiss(nudge.id) }}
                    className="text-xs text-green-400 hover:text-green-300 transition-colors"
                  >
                    Mark done today →
                  </button>
                )}
              </div>
            </div>
          )})
        )}
      </div>
    </aside>
  )
}

export default NudgePanel
