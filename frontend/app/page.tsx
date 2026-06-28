'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { NudgePanel } from '@/components/NudgePanel'
import { VoiceMode } from '@/components/VoiceMode'
import { TimerWidget } from '@/components/TimerWidget'
import { api } from '@/lib/api'
import { collectSensors } from '@/lib/sensors'
import { supabase } from '@/lib/supabase'
import type { Nudge, WorldState } from '@/types'
import { Send, Mic } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const JARVIS_URL = process.env.NEXT_PUBLIC_JARVIS_URL || 'http://localhost:8000'

export default function HomePage() {
  const router = useRouter()
  const [panelOpen, setPanelOpen] = useState(false)
  const [nudges, setNudges] = useState<Nudge[]>([])
  const [worldState, setWorldState] = useState<WorldState | null>(null)
  const [voiceActive, setVoiceActive] = useState(false)
  const [userToken, setUserToken] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        router.push('/login')
      } else {
        setUserToken(session.access_token)
      }
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (!session) {
        router.push('/login')
      } else {
        setUserToken(session.access_token)
      }
    })

    return () => subscription.unsubscribe()
  }, [router])

  const refreshNudges = useCallback(async (token: string) => {
    try {
      const res = await fetch(`${JARVIS_URL}/nudges`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) setNudges(await res.json())
    } catch (_) {}
  }, [])

  const refreshContext = useCallback(async (token: string) => {
    try {
      const sensors = await collectSensors()
      console.log('[sensors]', sensors)
      console.log('[context] posting with token:', !!token)
      const res = await fetch(`${JARVIS_URL}/context/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(sensors),
      })
      console.log('[context] response status:', res.status)
      if (res.ok) {
        const stateRes = await fetch(`${JARVIS_URL}/world-state`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (stateRes.ok) setWorldState(await stateRes.json())
      }
      await refreshNudges(token)
    } catch (e) {
      console.error('[context] error:', e)
    }
  }, [refreshNudges])

  // Only run context refresh AFTER token is available
  useEffect(() => {
    if (!userToken) return
    refreshContext(userToken)
    const interval = setInterval(() => refreshContext(userToken), 30 * 60 * 1000)
    return () => clearInterval(interval)
  }, [userToken, refreshContext])

  const syncLocation = useCallback(() => {
    if (!userToken) return
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const payload = { lat: pos.coords.latitude, lng: pos.coords.longitude, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone }
        console.log('[sync] got coords:', payload)
        const res = await fetch(`${JARVIS_URL}/context/update`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${userToken}` },
          body: JSON.stringify(payload),
        })
        console.log('[sync] response:', res.status)
        if (res.ok) {
          const stateRes = await fetch(`${JARVIS_URL}/world-state`, { headers: { Authorization: `Bearer ${userToken}` } })
          if (stateRes.ok) setWorldState(await stateRes.json())
          alert('Location synced!')
        } else {
          alert(`Sync failed: ${res.status}`)
        }
      },
      (err) => {
        console.error('[sync] geolocation error:', err)
        alert(`Location denied: ${err.message}. Sending Lagos default.`)
        fetch(`${JARVIS_URL}/context/update`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${userToken}` },
          body: JSON.stringify({ lat: 6.5244, lng: 3.3792, timezone: 'Africa/Lagos' }),
        }).then(r => console.log('[sync] fallback response:', r.status))
      }
    )
  }, [userToken])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleTimerFromResponse = useCallback((response: string) => {
    const timerMatch = response.match(/\[TIMER:(\d+(?:\.\d+)?):([^\]]+)\]/)
    if (timerMatch && (window as any).__jarvisAddTimer) {
      const minutes = parseFloat(timerMatch[1])
      const label = timerMatch[2]
      ;(window as any).__jarvisAddTimer(label, minutes * 60 * 1000)
    }
  }, [])

  const sendMessage = useCallback(async () => {
    if (!input.trim() || streaming || !userToken) return

    const userMsg: Message = { role: 'user', content: input.trim() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setStreaming(true)

    const allMessages = [...messages, userMsg].map(m => ({
      role: m.role,
      content: m.content,
    }))

    try {
      const res = await fetch(`${JARVIS_URL}/agent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${userToken}`,
        },
        body: JSON.stringify({ messages: allMessages }),
      })

      if (!res.ok || !res.body) throw new Error('Agent error')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let assistantContent = ''

      setMessages(prev => [...prev, { role: 'assistant', content: '' }])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ') && line !== 'data: [DONE]') {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.content) {
                assistantContent += data.content
                setMessages(prev => {
                  const updated = [...prev]
                  updated[updated.length - 1] = { role: 'assistant', content: assistantContent }
                  return updated
                })
              }
            } catch (_) {}
          }
        }
      }
      // Handle timer marker, strip it from displayed message
      if (assistantContent) {
        handleTimerFromResponse(assistantContent)
        const cleaned = assistantContent.replace(/\s*\[TIMER:[^\]]+\]/g, '').trim()
        if (cleaned !== assistantContent) {
          setMessages(prev => {
            const updated = [...prev]
            updated[updated.length - 1] = { role: 'assistant', content: cleaned }
            return updated
          })
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, something went wrong. Try again.' }])
    } finally {
      setStreaming(false)
    }
  }, [input, streaming, userToken, messages, handleTimerFromResponse])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const worldContext = worldState
    ? `Time: ${worldState.temporal?.day_of_week} ${worldState.temporal?.time_of_day}. Location: ${worldState.location?.city}. Weather: ${worldState.environment?.weather?.temp_c}°C ${worldState.environment?.weather?.condition}.`
    : 'No world context available yet.'

  const weather = worldState?.environment?.weather
  const location = worldState?.location

  return (
    <div className="flex h-screen bg-jarvis-bg text-jarvis-text overflow-hidden">
      {/* Main chat area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-jarvis-border bg-jarvis-surface">
          <div className="flex items-center gap-3">
            <span className="text-lg font-semibold tracking-tight">JARVIS</span>
            <span className="text-xs text-jarvis-muted">v3</span>
          </div>
          <div className="flex items-center gap-3 text-xs text-jarvis-muted">
            {location?.city && <span>{location.city}</span>}
            {weather?.temp_c != null && (
              <span>{Math.round(weather.temp_c)}°C · {weather.condition}</span>
            )}
            <button
              onClick={syncLocation}
              className="px-2 py-1 rounded bg-blue-900/40 hover:bg-blue-800/60 text-blue-400 transition-colors"
              title="Sync location"
            >
              ⌖ Sync
            </button>
            <button
              onClick={() => setPanelOpen(!panelOpen)}
              className="relative px-2 py-1 rounded bg-jarvis-border hover:bg-jarvis-accent/20 transition-colors"
            >
              Nudges
              {nudges.length > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                  {nudges.length}
                </span>
              )}
            </button>
          </div>
        </header>

        {/* Chat or Voice */}
        <div className="flex-1 overflow-hidden relative flex flex-col">
          {voiceActive && userToken ? (
            <div className="flex flex-col items-center justify-center h-full gap-6">
              <p className="text-jarvis-muted text-sm">Voice mode active</p>
              <VoiceMode
                worldStateContext={worldContext}
                userToken={userToken}
                onTranscript={(text, role) => {
                  setMessages(prev => [...prev, { role, content: text }])
                }}
              />
              <button
                onClick={() => setVoiceActive(false)}
                className="text-xs text-jarvis-muted hover:text-jarvis-text transition-colors mt-4"
              >
                Switch to text
              </button>
            </div>
          ) : (
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
                {messages.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-full text-center gap-3">
                    <p className="text-2xl font-semibold text-jarvis-text">Good {getTimeOfDay()}, Clifford.</p>
                    <p className="text-jarvis-muted text-sm">What's on your mind?</p>
                  </div>
                )}
                {messages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
                      msg.role === 'user'
                        ? 'bg-jarvis-accent text-white rounded-br-sm'
                        : 'bg-jarvis-surface text-jarvis-text rounded-bl-sm border border-jarvis-border'
                    }`}>
                      {msg.content || (streaming && i === messages.length - 1 ? '▋' : '')}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="px-4 py-3 border-t border-jarvis-border bg-jarvis-surface">
                <div className="flex items-end gap-2">
                  <textarea
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Message JARVIS..."
                    rows={1}
                    className="flex-1 resize-none bg-jarvis-bg border border-jarvis-border rounded-xl px-4 py-2.5 text-sm text-jarvis-text placeholder:text-jarvis-muted focus:outline-none focus:border-jarvis-accent transition-colors"
                    style={{ maxHeight: '120px' }}
                  />
                  {userToken && (
                    <button
                      onClick={() => setVoiceActive(true)}
                      className="p-2.5 rounded-xl bg-jarvis-border hover:bg-jarvis-accent/20 transition-colors text-jarvis-muted hover:text-jarvis-accent"
                      title="Voice mode"
                    >
                      <Mic size={18} />
                    </button>
                  )}
                  <button
                    onClick={sendMessage}
                    disabled={!input.trim() || streaming || !userToken}
                    className="p-2.5 rounded-xl bg-jarvis-accent hover:bg-jarvis-accent/80 disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-white"
                  >
                    <Send size={18} />
                  </button>
                </div>
                {!userToken && (
                  <p className="text-xs text-jarvis-muted mt-1 text-center">
                    <a href="/login" className="text-jarvis-accent hover:underline">Sign in</a> to chat with JARVIS
                  </p>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      <TimerWidget />

      {/* Nudge panel */}
      {panelOpen && userToken && (
        <NudgePanel
          token={userToken}
          onClose={() => setPanelOpen(false)}
          onPersonClick={(personId) => {
            window.location.href = `/people/${personId}`
          }}
        />
      )}
    </div>
  )
}

function getTimeOfDay() {
  const h = new Date().getHours()
  if (h < 12) return 'morning'
  if (h < 17) return 'afternoon'
  return 'evening'
}
