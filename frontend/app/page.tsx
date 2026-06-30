'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { NudgePanel } from '@/components/NudgePanel'
import { VoiceMode } from '@/components/VoiceMode'
import { TimerWidget } from '@/components/TimerWidget'
import { collectSensors } from '@/lib/sensors'
import { supabase } from '@/lib/supabase'
import type { Nudge, WorldState } from '@/types'
import { Send, Mic, Bell, X } from 'lucide-react'

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
  const [isVoiceMode, setIsVoiceMode] = useState(false)
  const [userToken, setUserToken] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [locationPermission, setLocationPermission] = useState<'granted' | 'denied' | 'prompt' | 'unknown'>('unknown')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const getToken = async (): Promise<string | null> => {
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token || null
  }

  const checkOnboarding = useCallback(async (token: string) => {
    try {
      const res = await fetch(`${JARVIS_URL}/users/profile`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const profile = await res.json()
        if (!profile.display_name) {
          router.push('/onboarding')
          return false
        }
      }
    } catch (e) {
      console.log('[onboarding] check failed, proceeding:', e)
    }
    return true
  }, [router])

  useEffect(() => {
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (!session) { router.push('/login'); return }
      const ok = await checkOnboarding(session.access_token)
      if (ok) setUserToken(session.access_token)
    })
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_, session) => {
      if (!session) { router.push('/login'); return }
      const ok = await checkOnboarding(session.access_token)
      if (ok) setUserToken(session.access_token)
    })
    return () => subscription.unsubscribe()
  }, [router, checkOnboarding])

  useEffect(() => {
    if (!navigator.permissions) {
      setLocationPermission('unknown')
      return
    }
    navigator.permissions.query({ name: 'geolocation' as PermissionName }).then((result) => {
      setLocationPermission(result.state as 'granted' | 'denied' | 'prompt')
      result.onchange = () => setLocationPermission(result.state as 'granted' | 'denied' | 'prompt')
    })
  }, [])

  const refreshNudges = useCallback(async () => {
    try {
      const token = await getToken()
      if (!token) return
      const res = await fetch(`${JARVIS_URL}/nudges`, { headers: { Authorization: `Bearer ${token}` } })
      if (res.ok) setNudges(await res.json())
    } catch (_) {}
  }, [])

  const refreshContext = useCallback(async () => {
    try {
      const token = await getToken()
      if (!token) return
      const sensors = await collectSensors()
      const res = await fetch(`${JARVIS_URL}/context/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(sensors),
      })
      if (res.ok) {
        const stateRes = await fetch(`${JARVIS_URL}/world-state`, { headers: { Authorization: `Bearer ${token}` } })
        if (stateRes.ok) setWorldState(await stateRes.json())
      }
      await refreshNudges()
    } catch (e) {
      console.error('[context] error:', e)
    }
  }, [refreshNudges])

  useEffect(() => {
    if (!userToken) return
    refreshContext()
    const interval = setInterval(() => refreshContext(), 30 * 60 * 1000)
    return () => clearInterval(interval)
  }, [userToken, refreshContext])

  const syncLocation = useCallback(async () => {
    const token = await getToken()
    if (!token) return
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const payload = {
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          location_accurate: true,
        }
        const res = await fetch(`${JARVIS_URL}/context/update`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify(payload),
        })
        if (res.ok) {
          const stateRes = await fetch(`${JARVIS_URL}/world-state`, { headers: { Authorization: `Bearer ${token}` } })
          if (stateRes.ok) setWorldState(await stateRes.json())
        }
      },
      async (err) => {
        console.warn('[syncLocation] geolocation error:', err.message)
        // Fall through to refreshContext which handles cached/default gracefully
        await refreshContext()
      }
    )
  }, [refreshContext])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Fix 1: reliable speakText — only fires after stream ends, voices loaded
  const speakText = useCallback((text: string) => {
    if (!window.speechSynthesis) return
    window.speechSynthesis.cancel()
    const clean = text
      .replace(/\[TIMER:[^\]]+\]/g, '')
      .replace(/\*\*/g, '')
      .replace(/\*/g, '')
      .replace(/#{1,6}\s/g, '')
      .trim()
    if (!clean) return

    const speak = () => {
      const utterance = new SpeechSynthesisUtterance(clean)
      utterance.rate = 1.05
      utterance.pitch = 1.0
      utterance.volume = 1.0
      const voices = window.speechSynthesis.getVoices()
      const preferred = voices.find(v => v.name.includes('Google') && v.lang.startsWith('en'))
        || voices.find(v => v.lang.startsWith('en') && !v.localService)
        || voices.find(v => v.lang.startsWith('en'))
      if (preferred) utterance.voice = preferred
      utterance.onerror = (e) => console.log('Speech error:', e)
      window.speechSynthesis.speak(utterance)
    }

    if (window.speechSynthesis.getVoices().length === 0) {
      window.speechSynthesis.onvoiceschanged = speak
    } else {
      speak()
    }
  }, [])

  const handleTimerFromResponse = useCallback((response: string) => {
    const timerMatch = response.match(/\[TIMER:(\d+(?:\.\d+)?):([^\]]+)\]/)
    if (timerMatch && (window as any).__jarvisAddTimer) {
      const minutes = parseFloat(timerMatch[1])
      const label = timerMatch[2]
      ;(window as any).__jarvisAddTimer(label, minutes * 60 * 1000)
    }
  }, [])

  const sendMessage = useCallback(async (overrideInput?: string) => {
    const text = (overrideInput ?? input).trim()
    if (!text || streaming || !userToken) return

    const userMsg: Message = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setStreaming(true)

    const allMessages = [...messages, userMsg].map(m => ({ role: m.role, content: m.content }))

    try {
      const token = await getToken()
      if (!token) throw new Error('No auth token')
      const res = await fetch(`${JARVIS_URL}/agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
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
        for (const line of decoder.decode(value).split('\n')) {
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

      // After stream ends — handle timer + speech
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
        // Fix 1: only speak if triggered via voice
        if (isVoiceMode) {
          speakText(cleaned || assistantContent)
        }
      }
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, something went wrong. Try again.' }])
    } finally {
      setStreaming(false)
    }
  }, [input, streaming, userToken, messages, handleTimerFromResponse, speakText, isVoiceMode])

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
  const temporal = worldState?.temporal

  return (
    <div className="flex flex-col h-dvh w-full bg-jarvis-bg text-jarvis-text overflow-hidden">

      {/* Header */}
      <header className="flex items-center justify-between px-3 py-2 border-b border-jarvis-border bg-jarvis-surface shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold tracking-tight">JARVIS</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-jarvis-muted">
          <button
            onClick={syncLocation}
            className="px-1.5 py-1 rounded bg-blue-900/40 hover:bg-blue-800/60 text-blue-400 transition-colors"
            title="Sync location"
          >
            ⌖ Sync
          </button>
          <button
            onClick={() => setPanelOpen(!panelOpen)}
            className="relative p-1.5 rounded bg-jarvis-border hover:bg-jarvis-accent/20 transition-colors"
            title="Nudges"
          >
            <Bell size={16} />
            {nudges.length > 0 && (
              <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center leading-none">
                {nudges.length}
              </span>
            )}
          </button>
        </div>
      </header>

      {/* Location denied banner */}
      {locationPermission === 'denied' && (
        <div className="bg-yellow-900/30 border-b border-yellow-700/30 px-4 py-2 text-xs text-yellow-400 flex items-center justify-between shrink-0">
          <span>📍 Location access denied — using default Lagos location. Enable in browser settings for accurate weather.</span>
        </div>
      )}

      {/* Rich context bar */}
      {worldState && (() => {
        const wb = worldState.environment?.weather
        const tmp = worldState.temporal
        const loc = worldState.location

        const getWeatherIcon = () => {
          const cond = wb?.condition || ''
          const isDay = wb?.is_day ?? true
          const precip = wb?.precipitation_mm || 0
          if (precip > 0.1 || cond.includes('rain') || cond.includes('drizzle')) return '🌧'
          if (cond.includes('thunder')) return '⛈'
          if (cond.includes('snow')) return '❄'
          if (cond.includes('fog') || cond.includes('mist')) return '🌫'
          if (cond.includes('partly_cloudy') || (cond.includes('cloud') && cond.includes('partly'))) return isDay ? '⛅' : '🌙'
          if (cond.includes('cloud') || cond.includes('overcast')) return '☁'
          if (!isDay) return '🌙'
          if (cond.includes('clear') || cond.includes('sunny')) return '☀'
          return isDay ? '🌤' : '🌙'
        }

        const rain1h = wb?.forecast_1h_rain_prob || 0
        const isRaining = (wb?.precipitation_mm || 0) > 0.1
        const district = loc?.district
        const city = loc?.city
        const locationStr = district && district !== city
          ? `${district}, ${city}`
          : city || 'Locating...'

        return (
          <div className="flex items-center gap-0 text-xs overflow-x-auto whitespace-nowrap border-b border-white/5 bg-gray-950/80 backdrop-blur-sm shrink-0">
            <div className="flex items-center gap-1 px-3 py-2 border-r border-white/5">
              <span className="text-blue-400">📍</span>
              <span className="text-gray-300">{locationStr}</span>
            </div>
            <div className="flex items-center gap-1 px-3 py-2 border-r border-white/5">
              <span>{getWeatherIcon()}</span>
              <span className="text-gray-300">{wb?.temp_c}°C</span>
            </div>
            {!isRaining && rain1h > 0.4 && (
              <div className="flex items-center gap-1 px-3 py-2 border-r border-white/5">
                <span>🌧</span>
                <span className="text-blue-400">{Math.round(rain1h * 100)}% soon</span>
              </div>
            )}
            {isRaining && (
              <div className="flex items-center gap-1 px-3 py-2 border-r border-white/5">
                <span>🌧</span>
                <span className="text-blue-400">Raining now</span>
              </div>
            )}
            {(wb?.uv_index ?? 0) >= 6 && wb?.is_day && (
              <div className="flex items-center gap-1 px-3 py-2 border-r border-white/5">
                <span>🕶</span>
                <span className="text-yellow-400">UV {wb.uv_index}</span>
              </div>
            )}
            {(wb?.humidity_pct ?? 0) >= 75 && (
              <div className="flex items-center gap-1 px-3 py-2 border-r border-white/5">
                <span>💧</span>
                <span className="text-gray-400">{wb?.humidity_pct}%</span>
              </div>
            )}
            {(wb?.wind_speed_kmh ?? 0) >= 20 && (
              <div className="flex items-center gap-1 px-3 py-2 border-r border-white/5">
                <span>💨</span>
                <span className="text-gray-400">{wb?.wind_speed_kmh} km/h</span>
              </div>
            )}
            {wb?.tomorrow_max_c && (
              <div className="flex items-center gap-1 px-3 py-2 border-r border-white/5">
                <span>🌤</span>
                <span className="text-gray-400">Tomorrow {wb.tomorrow_max_c}°C</span>
              </div>
            )}
            <div className="flex items-center gap-1 px-3 py-2 ml-auto">
              <span className="text-gray-500">
                {tmp?.timestamp
                  ? new Date(tmp.timestamp).toLocaleTimeString('en-US', {
                      hour: '2-digit', minute: '2-digit', hour12: true,
                    })
                  : ''}
              </span>
            </div>
          </div>
        )
      })()}

      {/* Chat or Voice */}
      <div className="flex-1 overflow-hidden flex flex-col min-h-0">
        {voiceActive && userToken ? (
          <div className="flex flex-col items-center justify-center h-full gap-6 px-4">
            <p className="text-jarvis-muted text-sm">Voice mode active</p>
            <VoiceMode
              worldStateContext={worldContext}
              userToken={userToken}
              onTranscript={(text, role) => {
                // VoiceMode handles its own agent call + speech internally.
                // onTranscript here is display-only — append to chat log.
                setMessages(prev => [...prev, { role, content: text }])
              }}
            />
            <button
              onClick={() => { setVoiceActive(false); setIsVoiceMode(false); window.speechSynthesis?.cancel() }}
              className="text-xs text-jarvis-muted hover:text-jarvis-text transition-colors"
            >
              Switch to text
            </button>
          </div>
        ) : (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-3 py-4 space-y-3">
              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center gap-3 px-4">
                  <p className="text-xl font-semibold text-jarvis-text">Good {getTimeOfDay()}, Clifford.</p>
                  <p className="text-jarvis-muted text-sm">What's on your mind?</p>
                </div>
              )}
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap break-words ${
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
            <div className="shrink-0 px-3 py-2 border-t border-jarvis-border bg-jarvis-surface">
              <div className="flex items-end gap-1.5">
                <textarea
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Message JARVIS..."
                  rows={1}
                  className="flex-1 min-w-0 resize-none bg-jarvis-bg border border-jarvis-border rounded-xl px-3 py-2 text-sm text-jarvis-text placeholder:text-jarvis-muted focus:outline-none focus:border-jarvis-accent transition-colors"
                  style={{ maxHeight: '100px' }}
                />
                {userToken && (
                  <button
                    onClick={() => { setIsVoiceMode(true); setVoiceActive(true) }}
                    className="p-2 rounded-xl bg-jarvis-border hover:bg-jarvis-accent/20 transition-colors text-jarvis-muted hover:text-jarvis-accent shrink-0"
                    title="Voice mode"
                  >
                    <Mic size={18} />
                  </button>
                )}
                <button
                  onClick={() => sendMessage()}
                  disabled={!input.trim() || streaming || !userToken}
                  className="p-2 rounded-xl bg-jarvis-accent hover:bg-jarvis-accent/80 disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-white shrink-0"
                >
                  <Send size={18} />
                </button>
              </div>
              {!userToken && (
                <p className="text-xs text-jarvis-muted mt-1 text-center">
                  <a href="/login" className="text-jarvis-accent hover:underline">Sign in</a> to chat
                </p>
              )}
            </div>
          </>
        )}
      </div>

      <TimerWidget />

      {/* Nudge panel */}
      {panelOpen && userToken && (
        <div className="fixed inset-0 z-50 md:relative md:inset-auto md:w-80">
          <div className="absolute inset-0 bg-black/60 md:hidden" onClick={() => setPanelOpen(false)} />
          <div className="absolute right-0 top-0 bottom-0 w-80 md:relative md:w-full">
            <NudgePanel
              token={userToken}
              onClose={() => setPanelOpen(false)}
              onPersonClick={(personId) => { window.location.href = `/people/${personId}` }}
            />
          </div>
        </div>
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
