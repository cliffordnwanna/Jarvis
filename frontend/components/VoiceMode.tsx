'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { Mic, PhoneOff, Loader2 } from 'lucide-react'
import { supabase } from '@/lib/supabase'

interface VoiceModeProps {
  onTranscript?: (text: string, role: 'user' | 'assistant') => void
}

type VoiceStatus = 'idle' | 'connecting' | 'connected' | 'listening' | 'speaking' | 'error'

const JARVIS_URL = process.env.NEXT_PUBLIC_JARVIS_URL || 'http://localhost:8000'

async function getRoomToken(): Promise<{ token: string; room: string; url: string } | null> {
  const { data: { session } } = await supabase.auth.getSession()
  if (!session?.access_token) return null

  const res = await fetch(`${JARVIS_URL}/voice/token`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
  })
  if (!res.ok) return null
  return res.json()
}

export function VoiceMode({ onTranscript }: VoiceModeProps) {
  const [status, setStatus] = useState<VoiceStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const roomRef = useRef<any>(null)

  const connect = useCallback(async () => {
    setStatus('connecting')
    setError(null)

    try {
      const { Room, RoomEvent, Track } = await import('livekit-client')

      const tokenData = await getRoomToken()
      if (!tokenData) throw new Error('Failed to get room token')

      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
      })
      roomRef.current = room

      room.on(RoomEvent.TrackSubscribed, (track: any) => {
        if (track.kind === Track.Kind.Audio) {
          setStatus('speaking')
          const audio = track.attach()
          document.body.appendChild(audio)
          audio.play().catch(console.error)
          track.on('ended', () => setStatus('connected'))
        }
      })

      room.on(RoomEvent.DataReceived, (data: Uint8Array) => {
        try {
          const msg = JSON.parse(new TextDecoder().decode(data))
          if (msg.type === 'transcript' && onTranscript) {
            onTranscript(msg.text, msg.role)
          }
        } catch {}
      })

      room.on(RoomEvent.Disconnected, () => {
        setStatus('idle')
      })

      await room.connect(tokenData.url, tokenData.token)
      await room.localParticipant.setMicrophoneEnabled(true)
      setStatus('connected')
    } catch (err: any) {
      setError(err.message || 'Connection failed')
      setStatus('error')
    }
  }, [onTranscript])

  const disconnect = useCallback(async () => {
    if (roomRef.current) {
      await roomRef.current.disconnect()
      roomRef.current = null
    }
    setStatus('idle')
    setError(null)
  }, [])

  useEffect(() => {
    return () => { disconnect() }
  }, [disconnect])

  const statusConfig: Record<VoiceStatus, { color: string; label: string; pulse: boolean }> = {
    idle:       { color: 'bg-gray-700 hover:bg-gray-600', label: 'Talk to JARVIS', pulse: false },
    connecting: { color: 'bg-yellow-700', label: 'Connecting...', pulse: false },
    connected:  { color: 'bg-green-700', label: 'Connected — speak now', pulse: true },
    listening:  { color: 'bg-red-600', label: 'Listening...', pulse: true },
    speaking:   { color: 'bg-blue-600', label: 'JARVIS speaking...', pulse: true },
    error:      { color: 'bg-red-800', label: 'Error — tap to retry', pulse: false },
  }

  const cfg = statusConfig[status]
  const isActive = status !== 'idle' && status !== 'error'

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative flex items-center justify-center w-16 h-16">
        {cfg.pulse && (
          <div className={`absolute inset-0 rounded-full animate-ping opacity-20 ${cfg.color}`} />
        )}
        {status === 'connecting' && (
          <div className="absolute inset-0 rounded-full border-2 border-yellow-500/40 border-t-yellow-400 animate-spin" />
        )}
        <button
          onClick={isActive ? disconnect : connect}
          disabled={status === 'connecting'}
          className={`relative z-10 w-12 h-12 rounded-full flex items-center justify-center
                      transition-all ${cfg.color} disabled:opacity-50 disabled:cursor-wait`}
        >
          {status === 'connecting' ? (
            <Loader2 size={18} className="text-white animate-spin" />
          ) : isActive ? (
            <PhoneOff size={16} className="text-white" />
          ) : (
            <Mic size={18} className="text-white" />
          )}
        </button>
      </div>

      <p className="text-xs text-gray-400">{cfg.label}</p>

      {error && (
        <p className="text-xs text-red-400 text-center max-w-[160px]">{error}</p>
      )}
    </div>
  )
}
