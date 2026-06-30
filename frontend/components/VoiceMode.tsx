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
  const voices = window.speechSynthesis.getVoices()
  const preferred =
    voices.find(v => v.lang.startsWith('en') && !v.localService) ||
    voices.find(v => v.lang.startsWith('en'))
  if (preferred) utter.voice = preferred
  window.speechSynthesis.speak(utter)
}

export function VoiceMode({ onTranscript }: VoiceModeProps) {
  const [status, setStatus] = useState<VoiceStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const recognitionRef = useRef<any>(null)

  const stop = useCallback(() => {
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
    rec.lang = 'en-US'
    rec.interimResults = false
    rec.maxAlternatives = 1
    recognitionRef.current = rec

    rec.onstart = () => setStatus('listening')

    rec.onresult = async (e: any) => {
      const transcript = e.results[0][0].transcript
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
      setError(e.error === 'no-speech' ? 'No speech detected' : `Error: ${e.error}`)
      setStatus('idle')
    }

    rec.onend = () => {
      // Only reset to idle if we haven't moved on to thinking/speaking
      setStatus(prev => prev === 'listening' ? 'idle' : prev)
    }

    rec.start()
  }, [onTranscript])

  const isActive = status === 'listening' || status === 'speaking'

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Mic button */}
      <div className="relative flex items-center justify-center w-20 h-20">
        {isActive && (
          <>
            <div className={`absolute inset-0 rounded-full animate-ping opacity-20 ${status === 'speaking' ? 'bg-blue-400' : 'bg-red-400'}`} />
            <div className={`absolute inset-2 rounded-full animate-ping opacity-30 ${status === 'speaking' ? 'bg-blue-400' : 'bg-red-400'}`} />
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
          {status === 'idle'
            ? <Mic size={20} className="text-white" />
            : isActive
            ? <Square size={16} className="text-white" />
            : <MicOff size={20} className="text-white" />
          }
        </button>
      </div>

      {/* Status label */}
      <p className="text-sm text-gray-400">
        {status === 'idle' && 'Tap to talk'}
        {status === 'listening' && 'Listening...'}
        {status === 'thinking' && 'Thinking...'}
        {status === 'speaking' && 'Speaking...'}
      </p>

      {/* Stop hint when active */}
      {status !== 'idle' && (
        <button onClick={stop} className="text-xs text-gray-600 hover:text-gray-400 transition-colors">
          Stop
        </button>
      )}

      {/* Error */}
      {error && <p className="text-xs text-red-400 text-center max-w-[200px]">{error}</p>}
    </div>
  )
}
