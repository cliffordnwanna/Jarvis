'use client'

import { useRef, useState, useCallback } from 'react'
import { Mic, MicOff, Square } from 'lucide-react'
import { supabase } from '@/lib/supabase'

interface VoiceModeProps {
  userToken: string
  onTranscript?: (text: string, role: 'user' | 'assistant') => void
}

type VoiceStatus = 'idle' | 'listening' | 'thinking' | 'speaking'

const JARVIS_URL = process.env.NEXT_PUBLIC_JARVIS_URL || 'http://localhost:8000'

async function getToken(): Promise<string | null> {
  const { data: { session } } = await supabase.auth.getSession()
  return session?.access_token || null
}

function speak(text: string, onDone: () => void) {
  const cleaned = text
    .replace(/\[TIMER:[^\]]+\]/g, '')
    .replace(/\*\*/g, '')
    .replace(/\*/g, '')
    .replace(/#{1,6}\s/g, '')
    .trim()
  if (!cleaned || !window.speechSynthesis) { onDone(); return }
  window.speechSynthesis.cancel()
  const utter = new SpeechSynthesisUtterance(cleaned)
  utter.rate = 1.05
  utter.pitch = 1.0
  utter.volume = 1.0
  utter.onend = onDone
  utter.onerror = onDone
  const trySpeak = () => {
    const voices = window.speechSynthesis.getVoices()
    const preferred =
      voices.find(v => v.lang.startsWith('en') && !v.localService) ||
      voices.find(v => v.lang.startsWith('en'))
    if (preferred) utter.voice = preferred
    window.speechSynthesis.speak(utter)
  }
  if (window.speechSynthesis.getVoices().length === 0) {
    window.speechSynthesis.onvoiceschanged = trySpeak
  } else {
    trySpeak()
  }
}

export function VoiceMode({ onTranscript }: VoiceModeProps) {
  const [status, setStatus] = useState<VoiceStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const recognitionRef = useRef<any>(null)
  const safetyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const isSafari = typeof navigator !== 'undefined' &&
    /^((?!chrome|android).)*safari/i.test(navigator.userAgent)
  const isIOS = typeof navigator !== 'undefined' &&
    /iPad|iPhone|iPod/.test(navigator.userAgent)
  const speechSupported = typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)

  if (!speechSupported) {
    return (
      <div className="flex flex-col items-center gap-2">
        <div className="w-14 h-14 rounded-full bg-gray-800 flex items-center justify-center opacity-50">
          <MicOff size={20} className="text-gray-500" />
        </div>
        <p className="text-xs text-gray-600 text-center max-w-[160px]">
          Voice not supported in this browser
        </p>
      </div>
    )
  }

  const stop = useCallback(() => {
    if (safetyTimerRef.current) clearTimeout(safetyTimerRef.current)
    recognitionRef.current?.stop()
    window.speechSynthesis?.cancel()
    setStatus('idle')
  }, [])

  const startListening = useCallback(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      setError('Speech recognition not supported in this browser')
      return
    }

    setError(null)
    const rec = new SpeechRecognition()
    // Safari requires both of these to be false
    rec.lang = 'en-US'
    rec.continuous = false
    rec.interimResults = false
    rec.maxAlternatives = 1
    recognitionRef.current = rec

    // Guard against Safari firing onend before onresult
    let resultReceived = false

    rec.onstart = () => {
      setStatus('listening')
      // 10-second safety net for Safari — clears if result arrives first
      safetyTimerRef.current = setTimeout(() => {
        if (!resultReceived) {
          rec.stop()
          setStatus('idle')
          setError('Listening timed out — tap to try again')
        }
      }, 10000)
    }

    rec.onresult = async (e: any) => {
      resultReceived = true
      if (safetyTimerRef.current) clearTimeout(safetyTimerRef.current)

      const transcript = Array.from(e.results as SpeechRecognitionResultList)
        .map((r: SpeechRecognitionResult) => r[0].transcript)
        .join('')
      if (!transcript.trim()) { setStatus('idle'); return }

      if (onTranscript) onTranscript(transcript, 'user')
      setStatus('thinking')

      try {
        const token = await getToken()
        if (!token) { setStatus('idle'); setError('Not signed in'); return }

        const res = await fetch(`${JARVIS_URL}/agent`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ messages: [{ role: 'user', content: transcript }] }),
        })
        if (!res.ok || !res.body) { setStatus('idle'); setError('Agent error'); return }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let full = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          for (const line of decoder.decode(value).split('\n')) {
            if (line.startsWith('data: ') && !line.includes('[DONE]')) {
              try { full += JSON.parse(line.slice(6)).content || '' } catch (_) {}
            }
          }
        }

        if (full && onTranscript) onTranscript(full, 'assistant')
        setStatus('speaking')
        speak(full || '', () => setStatus('idle'))
      } catch (err: any) {
        setError(err.message || 'Something went wrong')
        setStatus('idle')
      }
    }

    rec.onerror = (e: any) => {
      if (safetyTimerRef.current) clearTimeout(safetyTimerRef.current)
      const msg =
        e.error === 'not-allowed' ? 'Microphone permission denied' :
        e.error === 'no-speech'   ? 'No speech detected — tap to try again' :
        `Error: ${e.error}`
      setError(msg)
      setStatus('idle')
    }

    rec.onend = () => {
      if (safetyTimerRef.current) clearTimeout(safetyTimerRef.current)
      // Only reset to idle if no result was received —
      // Safari sometimes fires onend before onresult
      if (!resultReceived) setStatus('idle')
    }

    rec.start()
  }, [onTranscript])

  const isActive = status === 'listening' || status === 'speaking'

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Mic button */}
      <div className="relative flex items-center justify-center w-20 h-20">
        {status === 'listening' && (
          <>
            <div className="absolute inset-0 rounded-full animate-ping opacity-20 bg-red-400" />
            <div className="absolute inset-2 rounded-full animate-ping opacity-30 bg-red-400" />
          </>
        )}
        {status === 'speaking' && (
          <>
            <div className="absolute inset-0 rounded-full animate-ping opacity-20 bg-blue-400" />
            <div className="absolute inset-2 rounded-full animate-ping opacity-30 bg-blue-400" />
          </>
        )}
        {status === 'thinking' && (
          <div className="absolute inset-0 rounded-full border-2 border-yellow-500/40 border-t-yellow-400 animate-spin" />
        )}
        <button
          onClick={status === 'idle' ? startListening : stop}
          className={`relative z-10 flex items-center justify-center w-14 h-14 rounded-full transition-all ${
            status === 'listening' ? 'bg-red-600 shadow-lg shadow-red-500/40'
            : status === 'speaking' ? 'bg-blue-600 shadow-lg shadow-blue-500/40'
            : status === 'thinking' ? 'bg-yellow-700 cursor-wait'
            : 'bg-gray-700 hover:bg-gray-600'
          }`}
        >
          {isActive
            ? <Square size={16} className="text-white" />
            : <Mic size={20} className="text-white" />
          }
        </button>
      </div>

      {/* Status label */}
      <p className="text-sm text-gray-400">
        {status === 'idle'      && 'Tap to talk'}
        {status === 'listening' && 'Listening...'}
        {status === 'thinking'  && 'Thinking...'}
        {status === 'speaking'  && 'Speaking...'}
      </p>

      {/* Stop hint when active */}
      {status !== 'idle' && (
        <button onClick={stop} className="text-xs text-gray-600 hover:text-gray-400 transition-colors">
          Stop
        </button>
      )}

      {error && <p className="text-xs text-red-400 text-center max-w-[200px]">{error}</p>}

      {isIOS && isSafari && status === 'idle' && !error && (
        <p className="text-xs text-gray-600 text-center max-w-[180px]">
          Voice is limited on Safari — Chrome works best
        </p>
      )}
    </div>
  )
}
