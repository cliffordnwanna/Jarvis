'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { NudgePanel } from '@/components/NudgePanel'
import { VoiceMode } from '@/components/VoiceMode'
import { MapWidget } from '@/components/MapWidget'
import { collectSensors } from '@/lib/sensors'
import { supabase } from '@/lib/supabase'
import type { Nudge, WorldState, Message } from '@/types'
import { Send, Mic, Bell } from 'lucide-react'

const JARVIS_URL = process.env.NEXT_PUBLIC_JARVIS_URL || 'http://localhost:8000'

export default function HomePage() {
  const router = useRouter()
  const [panelOpen, setPanelOpen] = useState(false)
  const [nudges, setNudges] = useState<Nudge[]>([])
  const [worldState, setWorldState] = useState<WorldState | null>(null)
  const [voiceActive, setVoiceActive] = useState(false)
  const [userToken, setUserToken] = useState<string | null>(null)
  const [authChecked, setAuthChecked] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [locationPermission, setLocationPermission] = useState<'granted' | 'denied' | 'prompt' | 'unknown'>('unknown')
  const [activeTimer, setActiveTimer] = useState<{ label: string; seconds: number; msgIndex: number } | null>(null)
  const [activeMap, setActiveMap] = useState<{
    type: 'places' | 'route'
    title: string
    places?: Array<{ name: string; lat: number; lng: number; type?: string }>
    route?: { from: { lat: number; lng: number; label: string }; to: { lat: number; lng: number; label: string } }
    userLat?: number
    userLng?: number
    msgIndex: number
  } | null>(null)
  const [currentTime, setCurrentTime] = useState<string>('')
  const [contextReady, setContextReady] = useState(false)
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
      setAuthChecked(true)
    })
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_, session) => {
      if (!session) { router.push('/login'); return }
      const ok = await checkOnboarding(session.access_token)
      if (ok) setUserToken(session.access_token)
      setAuthChecked(true)
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

  // Bootstrap location once on auth — checks permission state before deciding whether to ask
  useEffect(() => {
    if (!userToken) return

    const bootstrapLocation = async () => {
      if (navigator.permissions) {
        try {
          const result = await navigator.permissions.query({ name: 'geolocation' as PermissionName })

          if (result.state === 'granted') {
            // Already granted — silent read, no dialog ever shown
            navigator.geolocation.getCurrentPosition(
              (pos) => {
                localStorage.setItem('jarvis_last_gps', JSON.stringify({
                  lat: pos.coords.latitude,
                  lng: pos.coords.longitude,
                }))
              },
              () => {} // silent fail — sensors.ts will use cached coords
            )
            await refreshContext()
            setContextReady(true)
            return
          }

          if (result.state === 'denied') {
            // Explicitly denied — never ask again, use cached/default
            setLocationPermission('denied')
            await refreshContext()
            setContextReady(true)
            return
          }

          // 'prompt' — first time, ask exactly once
          navigator.geolocation.getCurrentPosition(
            async (pos) => {
              localStorage.setItem('jarvis_last_gps', JSON.stringify({
                lat: pos.coords.latitude,
                lng: pos.coords.longitude,
              }))
              setLocationPermission('granted')
              await refreshContext()
              setContextReady(true)
            },
            async () => {
              setLocationPermission('denied')
              await refreshContext()
              setContextReady(true)
            },
            { timeout: 10000, maximumAge: 0, enableHighAccuracy: false }
          )

          // Adapt if user changes permission in browser settings later
          result.onchange = () => {
            setLocationPermission(result.state as 'granted' | 'denied' | 'prompt')
            if (result.state === 'granted') refreshContext()
          }
        } catch {
          // permissions API not supported — just try once, browser decides
          navigator.geolocation.getCurrentPosition(
            async (pos) => {
              localStorage.setItem('jarvis_last_gps', JSON.stringify({
                lat: pos.coords.latitude,
                lng: pos.coords.longitude,
              }))
              await refreshContext()
              setContextReady(true)
            },
            async () => {
              await refreshContext()
              setContextReady(true)
            }
          )
        }
      } else {
        // No permissions API (older browsers) — just refresh with whatever we have
        await refreshContext()
        setContextReady(true)
      }
    }

    bootstrapLocation()

    // Sync every 5 minutes — no permission dialog, reads from cache
    const interval = setInterval(() => refreshContext(), 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [userToken]) // eslint-disable-line react-hooks/exhaustive-deps

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
      (err) => {
        console.warn('[syncLocation] geolocation error:', err.message)
      }
    )
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const updateClock = () => {
      setCurrentTime(new Date().toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit', hour12: true,
        timeZone: 'Africa/Lagos',
      }))
    }
    updateClock()
    const interval = setInterval(updateClock, 1000)
    return () => clearInterval(interval)
  }, [])

  const handleTimerFromResponse = useCallback((response: string, msgIndex: number) => {
    // __TIMER__:seconds:label — primary format from create_timer tool
    let m = response.match(/__TIMER__:(\d+(?:\.\d+)?):([^_\n]+)/)
    if (m) {
      const seconds = Math.round(parseFloat(m[1]))
      const label = m[2].trim()
      setActiveTimer({ seconds, label, msgIndex })
      if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission()
      }
      return
    }
    // [TIMER:minutes:label] — legacy fallback, convert minutes → seconds
    m = response.match(/\[TIMER:(\d+(?:\.\d+)?):([^\]]+)\]/)
    if (m) {
      const seconds = Math.round(parseFloat(m[1]) * 60)
      const label = m[2].trim()
      setActiveTimer({ seconds, label, msgIndex })
      if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission()
      }
    }
  }, [])

  const handleMapFromResponse = useCallback((response: string, msgIndex: number) => {
    const placesMatch = response.match(/__MAP_PLACES__:(\[[\s\S]+?\])(?:\n|$)/)
    if (placesMatch) {
      try {
        const places = JSON.parse(placesMatch[1])
        setActiveMap({
          type: 'places',
          title: 'Nearby places',
          places,
          userLat: worldState?.location?.lat,
          userLng: worldState?.location?.lng,
          msgIndex,
        })
        return
      } catch {}
    }
    const routeMatch = response.match(/__MAP_ROUTE__:(\{[\s\S]+?\})(?:\n|$)/)
    if (routeMatch) {
      try {
        const route = JSON.parse(routeMatch[1])
        setActiveMap({
          type: 'route',
          title: route.title || 'Directions',
          route,
          userLat: worldState?.location?.lat,
          userLng: worldState?.location?.lng,
          msgIndex,
        })
      } catch {}
    }
  }, [worldState])

  const sendMessage = useCallback(async (overrideInput?: string) => {
    const text = (overrideInput ?? input).trim()
    if (!text || streaming || !userToken) return

    // First message after page load — ensure world state is posted before the agent reads it
    if (!contextReady) {
      await refreshContext()
      setContextReady(true)
    }

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

      // After stream ends — handle timer, map, clean sentinels
      if (assistantContent) {
        // messages (stale closure) has N items before this sendMessage call.
        // We added userMsg (+1) then the assistant placeholder (+1), so
        // the assistant message sits at index N+1.
        const msgIdx = messages.length + 1
        handleTimerFromResponse(assistantContent, msgIdx)
        handleMapFromResponse(assistantContent, msgIdx)
        const cleaned = assistantContent
          .replace(/\s*__TIMER__:\d+(?:\.\d+)?:[^\n]+/gm, '')
          .replace(/\s*__MAP_PLACES__:\[[\s\S]+?\](?:\n|$)/gm, '')
          .replace(/\s*__MAP_ROUTE__:\{[\s\S]+?\}(?:\n|$)/gm, '')
          .trim()
        if (cleaned !== assistantContent) {
          setMessages(prev => {
            const updated = [...prev]
            updated[updated.length - 1] = { role: 'assistant', content: cleaned }
            return updated
          })
        }
      }
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, something went wrong. Try again.' }])
    } finally {
      setStreaming(false)
    }
  }, [input, streaming, userToken, messages, contextReady, refreshContext, handleTimerFromResponse, handleMapFromResponse])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

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
            {currentTime && (
              <div className="flex items-center gap-1 px-3 py-2 ml-auto">
                <span className="text-gray-400 text-xs">{currentTime}</span>
              </div>
            )}
          </div>
        )
      })()}

      {/* Chat or Voice */}
      <div className="flex-1 overflow-hidden flex flex-col min-h-0">
        {voiceActive && userToken ? (
          <div className="flex flex-col items-center justify-center h-full gap-6 px-4">
            <p className="text-jarvis-muted text-sm">Voice mode active</p>
            <VoiceMode
              onTranscript={(text, role) => {
                setMessages(prev => [...prev, { role, content: text }])
              }}
            />
            <button
              onClick={() => { setVoiceActive(false); window.speechSynthesis?.cancel() }}
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
              {messages.map((msg, i) => {
                const displayContent = msg.content
                  .replace(/\s*__TIMER__:\d+(?:\.\d+)?:[^\n]+/gm, '')
                  .replace(/\s*__MAP_PLACES__:\[[\s\S]+?\](?:\n|$)/gm, '')
                  .replace(/\s*__MAP_ROUTE__:\{[\s\S]+?\}(?:\n|$)/gm, '')
                  .trim()
                return (
                  <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap break-words ${
                      msg.role === 'user'
                        ? 'bg-jarvis-accent text-white rounded-br-sm'
                        : 'bg-jarvis-surface text-jarvis-text rounded-bl-sm border border-jarvis-border'
                    }`}>
                      {displayContent || (streaming && i === messages.length - 1 ? '▋' : '')}
                    </div>
                    {activeTimer && activeTimer.msgIndex === i && (
                      <InlineTimer
                        key={`timer-${activeTimer.msgIndex}`}
                        label={activeTimer.label}
                        seconds={activeTimer.seconds}
                      />
                    )}
                    {activeMap && activeMap.msgIndex === i && (
                      <MapWidget
                        key={`map-${activeMap.msgIndex}`}
                        places={activeMap.places}
                        route={activeMap.route}
                        userLat={activeMap.userLat}
                        userLng={activeMap.userLng}
                        title={activeMap.title}
                      />
                    )}
                  </div>
                )
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="shrink-0 px-3 pt-2 pb-[max(8px,env(safe-area-inset-bottom))] border-t border-jarvis-border bg-jarvis-surface">
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
                    onClick={() => setVoiceActive(true)}
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
              {authChecked && !userToken && (
                <p className="text-xs text-jarvis-muted mt-1 text-center">
                  <a href="/login" className="text-jarvis-accent hover:underline">Sign in</a> to chat
                </p>
              )}
            </div>
          </>
        )}
      </div>

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

function InlineTimer({ label, seconds }: { label: string; seconds: number }) {
  const [remaining, setRemaining] = useState(seconds)
  const [done, setDone] = useState(false)
  const doneRef = useRef(false)

  // Countdown tick — only touches state, no browser APIs
  useEffect(() => {
    if (doneRef.current) return
    const interval = setInterval(() => {
      setRemaining(prev => {
        if (prev <= 1) {
          clearInterval(interval)
          if (!doneRef.current) {
            doneRef.current = true
            setDone(true)
          }
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [label, seconds])

  // Fire audio/speech/notification after done state is committed
  useEffect(() => {
    if (!done) return
    // Chime
    try {
      const AC = window.AudioContext || (window as any).webkitAudioContext
      if (AC) {
        const ctx = new AC()
        ;[523.25, 659.25, 783.99].forEach((freq, i) => {
          const osc = ctx.createOscillator()
          const gain = ctx.createGain()
          osc.connect(gain)
          gain.connect(ctx.destination)
          osc.frequency.value = freq
          osc.type = 'sine'
          const t = ctx.currentTime + i * 0.4
          gain.gain.setValueAtTime(0, t)
          gain.gain.linearRampToValueAtTime(0.3, t + 0.05)
          gain.gain.linearRampToValueAtTime(0, t + 0.8)
          osc.start(t)
          osc.stop(t + 0.8)
        })
        setTimeout(() => ctx.close(), 3000)
      }
    } catch {}
    // Speech
    try {
      window.speechSynthesis?.cancel()
      window.speechSynthesis?.speak(new SpeechSynthesisUtterance(`Timer done: ${label}`))
    } catch {}
    // Notification
    try {
      if (Notification.permission === 'granted') {
        new Notification('⏰ JARVIS', { body: `${label} — done!` })
      }
    } catch {}
  }, [done, label])

  const mins = Math.floor(remaining / 60)
  const secs = remaining % 60
  const display = mins > 0
    ? `${mins}:${String(secs).padStart(2, '0')}`
    : `${String(secs).padStart(2, '0')}`

  if (done) {
    return (
      <div className="mt-2 flex items-center gap-2 text-green-400 text-sm font-medium">
        <span>⏰</span>
        <span>{label} — Done!</span>
        <span>🔔</span>
      </div>
    )
  }

  return (
    <div className="mt-2 inline-flex items-center gap-3 bg-gray-800/80 border border-white/10 rounded-xl px-4 py-2">
      <span className="text-blue-400">⏰</span>
      <span className="text-gray-300 text-sm">{label}</span>
      <span className="font-mono font-bold text-white text-lg tabular-nums">{display}</span>
    </div>
  )
}

