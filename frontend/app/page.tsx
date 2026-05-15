"use client"
import { CopilotKit } from "@copilotkit/react-core"
import { useCopilotAction, useCopilotChatInternal, useCopilotReadable } from "@copilotkit/react-core"
import { CopilotChat } from "@copilotkit/react-ui"
import type { Parameter } from "@copilotkit/shared"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Settings } from "lucide-react"
import { FoodOptionsCard } from "@/components/FoodOptionsCard"
import { GoalReminderCard } from "@/components/GoalReminderCard"
import { JarvisInput } from "@/components/JarvisInput"
import { NudgePanel } from "@/components/NudgePanel"
import { TrafficCard } from "@/components/TrafficCard"
import { WeatherCard } from "@/components/WeatherCard"
import { WorldStateFloater } from "@/components/WorldStateFloater"
import { api, type Nudge } from "@/lib/api"
import { getGpsPermissionState, pushSensors } from "@/lib/sensors"

function formatTime(value?: unknown) {
  if (typeof value !== "string" || !value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date)
}

function formatTemp(value?: unknown) {
  if (typeof value !== "number" || !Number.isFinite(value)) return null
  return `${Math.round(value)}°C`
}

function formatPercent(value?: unknown) {
  if (typeof value !== "number" || !Number.isFinite(value)) return null
  return `${Math.round(value)}%`
}

// For values stored as fractions (0-1) instead of percentages (0-100)
function formatFraction(value?: unknown) {
  if (typeof value !== "number" || !Number.isFinite(value)) return null
  return `${Math.round(value * 100)}%`
}

function StatusChip(props: { label: string; value?: string | null }) {
  if (!props.value) return null
  return (
    <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-white/80">
      <span className="text-white/50">{props.label}</span>
      <span className="font-medium text-white/90">{props.value}</span>
    </div>
  )
}

function JARVISInner({
  devConsoleOpen: _devConsoleOpen,
}: {
  devConsoleOpen: boolean
}) {
  const [panelOpen, setPanelOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [worldStateOpen, setWorldStateOpen] = useState(false)
  const [speechEnabled, setSpeechEnabled] = useState(true)
  const [nudges, setNudges] = useState<Nudge[]>([])
  const [goals, setGoals] = useState<any[]>([])
  const [worldState, setWorldState] = useState<Record<string, unknown>>({})
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [gpsGranted, setGpsGranted] = useState<boolean | null>(null)
  const [locRequesting, setLocRequesting] = useState(false)
  const [chatStarted, setChatStarted] = useState(false)
  const settingsRef = useRef<HTMLDivElement>(null)
  const spokenUpToRef = useRef<Record<string, number>>({})
  const speechUnlockedRef = useRef(false)

  useEffect(() => {
    try {
      const stored = localStorage.getItem("jarvis_speech_enabled")
      if (stored === "0") setSpeechEnabled(false)
      if (stored === "1") setSpeechEnabled(true)
    } catch {}
  }, [])

  useEffect(() => {
    try {
      localStorage.setItem("jarvis_speech_enabled", speechEnabled ? "1" : "0")
    } catch {}
  }, [speechEnabled])

  const unlockSpeech = useCallback(() => {
    if (speechUnlockedRef.current) return
    try {
      if (!("speechSynthesis" in window)) return
      const u = new SpeechSynthesisUtterance(" ")
      u.volume = 0
      window.speechSynthesis.speak(u)
      speechUnlockedRef.current = true
    } catch {}
  }, [])

  useEffect(() => {
    if (!speechEnabled) return
    const handler = () => {
      unlockSpeech()
      window.removeEventListener("pointerdown", handler, true)
    }
    window.addEventListener("pointerdown", handler, true)
    return () => window.removeEventListener("pointerdown", handler, true)
  }, [speechEnabled, unlockSpeech])

  // Auto-speak assistant messages — streams sentence-by-sentence while generating,
  // then speaks any remaining text when done.
  const { messages: chatMessages, isLoading } = useCopilotChatInternal()
  const prevLoadingRef = useRef(false)
  useEffect(() => {
    if (!speechEnabled) return
    if (!("speechSynthesis" in window)) return
    const wasLoading = prevLoadingRef.current
    prevLoadingRef.current = isLoading

    // New request starting — cancel previous speech
    if (!wasLoading && isLoading) {
      window.speechSynthesis.cancel()
      return
    }

    const msgs = Array.isArray(chatMessages) ? chatMessages : []
    const lastAssistant = [...msgs].reverse().find((m: any) => m.role === "assistant")
    if (!lastAssistant) return

    const id = (lastAssistant as any).id ?? `msg-${msgs.length}`
    const content = (lastAssistant as any).content
    const fullText =
      typeof content === "string"
        ? content
        : Array.isArray(content)
          ? content.filter((c: any) => c.type === "text").map((c: any) => c.text ?? "").join(" ")
          : ""
    if (!fullText.trim()) return

    const alreadySpoken = spokenUpToRef.current[id] ?? 0
    const newText = fullText.slice(alreadySpoken)
    if (!newText.trim()) return

    let toSpeak: string
    if (isLoading) {
      // During streaming: only speak at sentence boundaries to minimise latency
      const m = newText.match(/^([\s\S]*?[.!?])[\s]/)
      if (!m) return
      toSpeak = m[1]
    } else {
      // Generation done — speak whatever is left
      toSpeak = newText
    }

    if (!speechUnlockedRef.current) return

    spokenUpToRef.current[id] = alreadySpoken + toSpeak.length
    const utterance = new SpeechSynthesisUtterance(toSpeak)
    utterance.rate = 1.05
    window.speechSynthesis.speak(utterance)
  }, [isLoading, chatMessages, speechEnabled])

  // Close settings dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setSettingsOpen(false)
      }
    }
    if (settingsOpen) document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [settingsOpen])

  const BACKEND = process.env.NEXT_PUBLIC_JARVIS_URL || "http://localhost:8000"

  const refreshWorldState = useCallback(async () => {
    try {
      const ws = await api.worldState()
      setWorldState(ws)
      setLastUpdated(new Date())
    } catch {}
  }, [])

  const requestLocation = useCallback(async () => {
    setLocRequesting(true)
    try {
      const perm = await getGpsPermissionState()
      if (perm === "denied") {
        alert(
          "Location permission is blocked for this site. Enable Location for this site in your browser settings, then try again.",
        )
        return
      }
      const res = await pushSensors(BACKEND, { allowGpsPrompt: true, gpsTimeoutMs: 20000 })
      setGpsGranted(res.gpsAvailable)
      await refreshWorldState()
      if (!res.gpsAvailable) {
        alert("Could not get GPS fix yet. If you allowed Location, try again outdoors or wait a few seconds.")
      }
    } finally {
      setLocRequesting(false)
    }
  }, [BACKEND, refreshWorldState])

  // Push sensors then immediately refresh world state
  useEffect(() => {
    const push = async () => {
      const res = await pushSensors(BACKEND, { allowGpsPrompt: false })
      setGpsGranted(res.gpsAvailable)
      await refreshWorldState()
    }
    push()
    const interval = setInterval(push, 30 * 60_000) // 30 min
    return () => clearInterval(interval)
  }, [BACKEND, refreshWorldState])

  // Check GPS permission on mount
  useEffect(() => {
    getGpsPermissionState().then((state) => {
      if (state === "granted") setGpsGranted(true)
      else if (state === "denied") setGpsGranted(false)
    })
  }, [])

  // Poll nudges — no auto-open (just badge count)
  const refreshNudges = useCallback(async () => {
    try {
      const list = await api.nudges.list()
      setNudges(list)
    } catch {}
  }, [])

  useEffect(() => {
    refreshNudges()
    const interval = setInterval(refreshNudges, 30 * 60_000)
    return () => clearInterval(interval)
  }, [refreshNudges])

  // Poll world state (lightweight for header chips)
  useEffect(() => {
    const interval = setInterval(refreshWorldState, 5 * 60_000)
    return () => clearInterval(interval)
  }, [refreshWorldState])

  // Persona injected as context because CopilotKit 1.57 BuiltInAgent reads input.context,
  // not the CopilotChat instructions prop, when building the system prompt.
  useCopilotReadable({
    description: "AI assistant identity — follow these instructions at all times",
    value:
      "You are JARVIS, a proactive personal AI assistant. Your name is JARVIS — never call yourself 'Assistant'. " +
      "The human you are talking to is Clifford. When asked your name say 'I am JARVIS'. " +
      "When asked who the user is, say 'You are Clifford'. " +
      "Use the world-state context proactively. When showing weather/traffic/food data, call the matching UI card action.",
  })

  useCopilotReadable({
    description:
      "Current world state: time, location, weather, device, cognitive load, biological signals, nearby places, goals.",
    value: worldState,
  })

  useCopilotReadable({
    description: "Pending proactive nudges waiting for user attention.",
    value: nudges,
  })

  // Generative UI cards
  useCopilotAction({
    name: "weatherCard",
    description: "Show current weather conditions as a visual card",
    parameters: [
      { name: "condition", type: "string", required: true },
      { name: "temp_c", type: "number", required: true },
      { name: "feels_like_c", type: "number", required: true },
      { name: "humidity_pct", type: "number", required: true },
      { name: "rain_prob_1h", type: "number", required: true },
      { name: "city", type: "string", required: true },
    ] satisfies Parameter[],
    handler: async () => "ok",
    render: ({ status, args }) => (status === "inProgress" ? <></> : <WeatherCard {...(args as any)} />),
  })

  useCopilotAction({
    name: "trafficCard",
    description: "Show traffic conditions and ETA for a route",
    parameters: [
      { name: "congestion", type: "string", required: true },
      { name: "eta_now_minutes", type: "number", required: true },
      { name: "usual_eta_minutes", type: "number", required: true },
      { name: "delay_minutes", type: "number", required: true },
      { name: "route_label", type: "string", required: true },
    ] satisfies Parameter[],
    handler: async () => "ok",
    render: ({ status, args }) => (status === "inProgress" ? <></> : <TrafficCard {...(args as any)} />),
  })

  useCopilotAction({
    name: "foodOptionsCard",
    description: "Show nearby food options when user is hungry",
    parameters: [
      { name: "reason", type: "string", required: true },
      { name: "time_context", type: "string", required: true },
      {
        name: "options_json",
        type: "string",
        required: true,
        description:
          'JSON array of food options, e.g. [{"name":"KFC","distance_m":500,"estimated_delivery_min":20,"open_until":"22:00"}]',
      },
    ] satisfies Parameter[],
    handler: async () => "ok",
    render: ({ status, args }) => {
      if (status === "inProgress") return <></>
      let options: any[] = []
      try { options = JSON.parse((args as any).options_json ?? "[]") } catch {}
      return <FoodOptionsCard reason={(args as any).reason} time_context={(args as any).time_context} options={options} />
    },
  })

  useCopilotAction({
    name: "goalReminderCard",
    description: "Remind user about a stale or urgent goal",
    parameters: [
      { name: "goal_name", type: "string", required: true },
      { name: "days_stale", type: "number", required: true },
      { name: "urgency", type: "string", required: true },
      { name: "suggested_action", type: "string", required: true },
    ] satisfies Parameter[],
    handler: async () => "ok",
    render: ({ status, args }) => (status === "inProgress" ? <></> : <GoalReminderCard {...(args as any)} />),
  })

  useCopilotAction({
    name: "openNudgePanel",
    description: "Open the proactive nudge panel on the right side",
    parameters: [{ name: "reason", type: "string", required: false }] satisfies Parameter[],
    handler: async () => {
      setPanelOpen(true)
      return "Panel opened"
    },
  })

  useCopilotAction({
    name: "closeNudgePanel",
    description: "Close the nudge panel",
    parameters: [] satisfies Parameter[],
    handler: async () => {
      setPanelOpen(false)
      return "Panel closed"
    },
  })

  const handleDismissNudge = async (id: string) => {
    try {
      await api.nudges.dismiss(id)
    } catch {}
    setNudges((curr) => curr.filter((n) => n.id !== id))
  }

  const WrappedInput = useCallback(
    (props: any) => (
      <JarvisInput
        {...props}
        onSend={(text: string) => {
          setChatStarted(true)
          props.onSend?.(text)
        }}
      />
    ),
    [],
  )

  const greeting = useMemo(() => {
    const hour = new Date().getHours()
    const period = hour < 5 ? "night" : hour < 12 ? "morning" : hour < 17 ? "afternoon" : "evening"
    const ws = worldState as any
    const weatherDesc = ws?.environment?.weather?.description ?? ws?.environment?.weather?.condition
    const temp = ws?.environment?.weather?.temp_c ?? ws?.environment?.weather?.temperature_c
    const city = ws?.location?.city ?? ws?.location?.city_name ?? ws?.location?.town

    let msg = `Good ${period}, Clifford.`
    if (typeof weatherDesc === "string") {
      msg += ` It's ${weatherDesc.toLowerCase()}`
      if (typeof temp === "number") msg += ` at ${Math.round(temp)}°C`
      if (typeof city === "string") msg += ` in ${city}`
      msg += "."
    }
    return msg
  }, [worldState])

  const ws = worldState as any
  const city =
    ws?.location?.city ??
    ws?.location?.city_name ??
    ws?.location?.town ??
    ws?.location?.district ??
    null
  const state = ws?.location?.state ?? null
  const country = ws?.location?.country ?? null
  const localTime =
    formatTime(ws?.temporal?.timestamp) ??
    formatTime(ws?.temporal?.iso) ??
    formatTime(ws?.temporal?.local_time) ??
    null
  // Compute UTC offset from the browser's own clock — accurate regardless of VPN/IP routing
  const browserTzOffset = useMemo(() => {
    const offsetMin = -new Date().getTimezoneOffset()
    const sign = offsetMin >= 0 ? "+" : "-"
    const h = String(Math.floor(Math.abs(offsetMin) / 60)).padStart(2, "0")
    const m = String(Math.abs(offsetMin) % 60).padStart(2, "0")
    return `${sign}${h}:${m}`
  }, [])
  const weatherDesc = ws?.environment?.weather?.description ?? ws?.environment?.weather?.condition ?? null
  const temp = formatTemp(ws?.environment?.weather?.temp_c ?? ws?.environment?.weather?.temperature_c)
  const feelsLike = formatTemp(ws?.environment?.weather?.feels_like_c)
  const humidity = formatPercent(ws?.environment?.weather?.humidity_pct)
  // forecast_1h_rain_prob is stored as 0-1 fraction from Open-Meteo
  const rainProb =
    formatFraction(ws?.environment?.weather?.forecast_1h_rain_prob) ??
    formatPercent(ws?.environment?.weather?.rain_prob_1h)
  const windSpeedKmh = ws?.environment?.weather?.wind_speed_kmh
  const windDir = ws?.environment?.weather?.wind_direction
  const wind =
    typeof windSpeedKmh === "number"
      ? `${Math.round(windSpeedKmh)} km/h${typeof windDir === "string" ? ` ${windDir}` : ""}`
      : null
  // Just the number — chip label already says "UV"
  const uvIndex =
    typeof ws?.environment?.weather?.uv_index === "number"
      ? String(Math.round(ws.environment.weather.uv_index))
      : null
  // Show AQI score + category when available ("23 · good"), otherwise category only
  const aqiNum = ws?.environment?.air_quality?.aqi
  const aqiCat = typeof ws?.environment?.air_quality?.category === "string"
    ? ws.environment.air_quality.category.replace(/_/g, " ")
    : null
  const aqiLabel = typeof aqiNum === "number"
    ? `${Math.round(aqiNum)} · ${aqiCat ?? ""}`
    : aqiCat
  const battery = formatPercent(ws?.device?.battery_pct)
  const isCharging = ws?.device?.charging === true
  const batteryDisplay = battery ? (isCharging ? `${battery} charging` : battery) : null

  return (
    <div className="h-[100dvh] min-h-[100dvh] overflow-hidden bg-[#0a0f1a] text-slate-100">
      <div className="mx-auto flex h-full max-w-5xl flex-col">
        <header className="flex items-center justify-between px-4 sm:px-5 pt-[calc(1rem+env(safe-area-inset-top))] pb-3 sm:py-4">
          <div className="min-w-0">
            <div className="flex items-baseline gap-3">
              <h1 className="text-sm font-semibold tracking-wide text-white">JARVIS</h1>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <StatusChip label="Time" value={localTime} />
              {gpsGranted === false || (typeof city === "string" && city === "Unknown") ? (
                <button
                  onClick={requestLocation}
                  disabled={locRequesting}
                  className="flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/[0.08] px-3 py-1.5 text-xs text-amber-400/90 hover:bg-amber-500/[0.15] transition-colors"
                  title="Allow location — if already denied, reset permission in browser settings (lock icon in address bar)"
                >
                  <span className="text-amber-500/60">Loc</span>
                  <span>{locRequesting ? "Requesting..." : "Allow location"}</span>
                </button>
              ) : (
                <>
                  <StatusChip label="City" value={typeof city === "string" && city !== "Unknown" ? city : null} />
                  <StatusChip label="State" value={typeof state === "string" && state !== "Unknown" ? state : null} />
                  <StatusChip label="Country" value={typeof country === "string" && country !== "Unknown" ? country : null} />
                </>
              )}
              <StatusChip label="UTC" value={browserTzOffset} />
              <StatusChip label="Weather" value={typeof weatherDesc === "string" ? weatherDesc.replace(/_/g, " ") : null} />
              <StatusChip label="Temp" value={temp} />
              <StatusChip label="Feels" value={feelsLike} />
              <StatusChip label="Humidity" value={humidity} />
              <StatusChip label="Rain 1h" value={rainProb} />
              <StatusChip label="Wind" value={wind} />
              <StatusChip label="UV" value={uvIndex} />
              <StatusChip label="Air" value={aqiLabel} />
              <StatusChip label="Battery" value={batteryDisplay} />
            </div>
          </div>
          <div className="flex flex-shrink-0 items-center gap-2">
            <button
              onClick={() => setPanelOpen((v) => !v)}
              className="rounded-full border border-white/10 bg-white/[0.02] px-3 py-2 text-xs text-white/70 hover:bg-white/[0.05]"
            >
              Nudges{nudges.length > 0 && ` (${nudges.length})`}
            </button>
            {/* Settings dropdown */}
            <div ref={settingsRef} className="relative">
              <button
                onClick={() => setSettingsOpen((v) => !v)}
                className="rounded-full border border-white/10 bg-white/[0.02] p-2 text-white/70 hover:bg-white/[0.05]"
                title="Settings"
              >
                <Settings size={14} />
              </button>
              {settingsOpen && (
                <div className="absolute right-0 top-full mt-2 z-50 w-44 rounded-xl border border-white/10 bg-[#0d1424] py-1 shadow-xl">
                  <button
                    onClick={() => setSpeechEnabled((v) => !v)}
                    className="w-full px-4 py-2 text-left text-xs text-white/70 hover:bg-white/[0.05]"
                  >
                    Speech: {speechEnabled ? "On" : "Off"}
                  </button>
                  {speechEnabled && (
                    <button
                      onClick={() => {
                        unlockSpeech()
                        const u = new SpeechSynthesisUtterance("Audio enabled.")
                        u.rate = 1.05
                        window.speechSynthesis.cancel()
                        window.speechSynthesis.speak(u)
                        setSettingsOpen(false)
                      }}
                      className="w-full px-4 py-2 text-left text-xs text-white/70 hover:bg-white/[0.05]"
                    >
                      Test audio
                    </button>
                  )}
                  <button
                    onClick={() => { setWorldStateOpen((v) => !v); setSettingsOpen(false) }}
                    className="w-full px-4 py-2 text-left text-xs text-white/70 hover:bg-white/[0.05]"
                  >
                    {worldStateOpen ? "Hide world state" : "World state"}
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-hidden px-3 sm:px-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))]">
          <div className="h-full rounded-2xl border border-white/10 bg-white/[0.02]">
            <div className="relative mx-auto h-full w-full max-w-3xl">
              {!chatStarted && (
                <div className="pointer-events-none absolute inset-0 z-10 flex flex-col items-center justify-center pb-20">
                  <p className="px-6 text-center text-2xl font-semibold leading-snug text-white/80">
                    {greeting}
                  </p>
                </div>
              )}
              <CopilotChat
                className="jarvis-chat h-full"
                instructions="You are JARVIS, an AI assistant. You are NOT Clifford — Clifford is the human user talking to you. Your name is JARVIS. Always refer to yourself as JARVIS. When asked your name, say 'I am JARVIS'. The user's name is Clifford. You have access to Clifford's real-time world state including location, weather, device battery, and goals — use this context proactively. When showing weather, traffic, or food data, use the appropriate UI card actions (weatherCard, trafficCard, foodOptionsCard). Be concise, specific, and helpful."
                labels={{
                  title: "JARVIS",
                  initial: "",
                  placeholder: "Message JARVIS…",
                }}
                Input={WrappedInput}
              />
            </div>
          </div>
        </div>
      </div>

      {panelOpen && (
        <>
          <button
            aria-label="Close nudges panel"
            className="fixed inset-0 z-40 cursor-default bg-black/50"
            onClick={() => setPanelOpen(false)}
          />
          <NudgePanel
            nudges={nudges}
            goals={goals}
            onClose={() => setPanelOpen(false)}
            onGoalUpdate={setGoals}
            onDismissNudge={handleDismissNudge}
          />
        </>
      )}

      {worldStateOpen && (
        <WorldStateFloater
          worldState={worldState}
          lastUpdated={lastUpdated}
          onRefresh={refreshWorldState}
          onClose={() => setWorldStateOpen(false)}
        />
      )}
    </div>
  )
}

export default function JARVISPage() {
  const [devConsoleOpen] = useState(false)

  return (
    <CopilotKit runtimeUrl="/api/copilotkit">
      <JARVISInner devConsoleOpen={devConsoleOpen} />
    </CopilotKit>
  )
}
