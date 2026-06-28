'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Timer, X } from 'lucide-react'

interface ActiveTimer {
  id: string
  label: string
  endsAt: number
  duration: number
}

export function TimerWidget() {
  const [timers, setTimers] = useState<ActiveTimer[]>([])
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const [, forceUpdate] = useState(0)

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      forceUpdate(n => n + 1)
      const now = Date.now()
      setTimers(prev => {
        const expired = prev.filter(t => t.endsAt <= now)
        expired.forEach(t => {
          if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('⏰ JARVIS Timer', { body: t.label, icon: '/icon-192.png' })
          }
          if (window.speechSynthesis) {
            const u = new SpeechSynthesisUtterance(`Timer done: ${t.label}`)
            window.speechSynthesis.speak(u)
          }
        })
        return prev.filter(t => t.endsAt > now)
      })
    }, 1000)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [])

  const addTimer = useCallback((label: string, durationMs: number) => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }
    const timer: ActiveTimer = {
      id: Math.random().toString(36).slice(2),
      label,
      endsAt: Date.now() + durationMs,
      duration: durationMs,
    }
    setTimers(prev => [...prev, timer])
    return timer.id
  }, [])

  const removeTimer = useCallback((id: string) => {
    setTimers(prev => prev.filter(t => t.id !== id))
  }, [])

  useEffect(() => {
    (window as any).__jarvisAddTimer = addTimer
  }, [addTimer])

  if (timers.length === 0) return null

  return (
    <div className="fixed bottom-24 right-4 flex flex-col gap-2 z-50">
      {timers.map(timer => {
        const remaining = Math.max(0, timer.endsAt - Date.now())
        const totalSeconds = Math.floor(remaining / 1000)
        const hours = Math.floor(totalSeconds / 3600)
        const minutes = Math.floor((totalSeconds % 3600) / 60)
        const seconds = totalSeconds % 60
        const progress = 1 - (remaining / timer.duration)

        const timeStr = hours > 0
          ? `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
          : `${minutes}:${String(seconds).padStart(2, '0')}`

        return (
          <div key={timer.id} className="bg-gray-900 border border-white/10 rounded-xl p-3 flex items-center gap-3 min-w-48 shadow-xl">
            <div className="relative w-10 h-10 flex-shrink-0">
              <svg className="w-10 h-10 -rotate-90" viewBox="0 0 36 36">
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="#374151" strokeWidth="2.5" />
                <circle
                  cx="18" cy="18" r="15.9" fill="none"
                  stroke="#3b82f6" strokeWidth="2.5"
                  strokeDasharray={`${progress * 100} 100`}
                  strokeLinecap="round"
                />
              </svg>
              <Timer size={12} className="absolute inset-0 m-auto text-blue-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-500 truncate">{timer.label}</p>
              <p className="text-lg font-mono font-bold text-white">{timeStr}</p>
            </div>
            <button onClick={() => removeTimer(timer.id)} className="text-gray-600 hover:text-gray-400">
              <X size={14} />
            </button>
          </div>
        )
      })}
    </div>
  )
}
