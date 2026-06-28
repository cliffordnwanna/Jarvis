'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { Mic, PhoneOff, MicOff } from 'lucide-react'

interface VoiceModeProps {
  worldStateContext: string
  userToken: string
  onTranscript?: (text: string, role: 'user' | 'assistant') => void
}

const JARVIS_URL = process.env.NEXT_PUBLIC_JARVIS_URL || 'http://localhost:8000'

const JARVIS_SYSTEM_PROMPT = `You are JARVIS — a proactive personal AI. Not a chatbot.
You know the user's world and their people. You speak like a smart, warm friend.
Be direct. Be concise. No filler phrases. No "As an AI..." disclaimers.
Keep responses short in voice mode — 2-3 sentences max unless asked for more.`

// --- OpenAI Realtime (WebRTC) mode ---

function RealtimeVoice({ worldStateContext, userToken, onTranscript, onFallback }: VoiceModeProps & { onFallback: () => void }) {
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const peerConnectionRef = useRef<RTCPeerConnection | null>(null)
  const dataChannelRef = useRef<RTCDataChannel | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const disconnect = useCallback(() => {
    dataChannelRef.current?.close()
    peerConnectionRef.current?.close()
    streamRef.current?.getTracks().forEach(t => t.stop())
    if (audioRef.current) audioRef.current.srcObject = null
    dataChannelRef.current = null
    peerConnectionRef.current = null
    streamRef.current = null
    setIsConnected(false)
    setIsSpeaking(false)
    setIsListening(false)
    setError(null)
  }, [])

  const connect = useCallback(async () => {
    setIsConnecting(true)
    setError(null)
    try {
      const tokenRes = await fetch(`${JARVIS_URL}/voice/token`, {
        headers: { Authorization: `Bearer ${userToken}` }
      })
      if (!tokenRes.ok) {
        onFallback()
        return
      }
      const { client_secret } = await tokenRes.json()

      const pc = new RTCPeerConnection()
      peerConnectionRef.current = pc

      if (!audioRef.current) {
        audioRef.current = document.createElement('audio')
        audioRef.current.autoplay = true
        document.body.appendChild(audioRef.current)
      }
      pc.ontrack = (e) => { if (audioRef.current && e.streams[0]) audioRef.current.srcObject = e.streams[0] }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      stream.getTracks().forEach(track => pc.addTrack(track, stream))

      const dc = pc.createDataChannel('oai-events')
      dataChannelRef.current = dc

      dc.onopen = () => {
        dc.send(JSON.stringify({
          type: 'session.update',
          session: {
            modalities: ['text', 'audio'],
            instructions: JARVIS_SYSTEM_PROMPT + '\n\nCurrent context:\n' + worldStateContext,
            voice: 'alloy',
            input_audio_format: 'pcm16',
            output_audio_format: 'pcm16',
            turn_detection: { type: 'server_vad', threshold: 0.5, prefix_padding_ms: 300, silence_duration_ms: 600 },
            temperature: 0.8,
          }
        }))
        setIsConnected(true)
        setIsConnecting(false)
        setIsListening(true)
      }

      dc.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data)
          if (event.type === 'input_audio_buffer.speech_started') { setIsListening(true); setIsSpeaking(false) }
          if (event.type === 'response.audio.delta') { setIsSpeaking(true); setIsListening(false) }
          if (event.type === 'response.audio.done') { setIsSpeaking(false); setIsListening(true) }
          if (event.type === 'conversation.item.completed') {
            const t = event.item?.content?.[0]?.transcript
            if (t && onTranscript) onTranscript(t, 'assistant')
          }
          if (event.type === 'conversation.item.created') {
            const t = event.item?.content?.[0]?.transcript
            if (t && onTranscript) onTranscript(t, 'user')
          }
          if (event.type === 'error') setError(event.error?.message || 'Voice error')
        } catch (_) {}
      }

      dc.onclose = () => disconnect()

      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)

      const sdpRes = await fetch('https://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17', {
        method: 'POST',
        headers: { Authorization: `Bearer ${client_secret.value}`, 'Content-Type': 'application/sdp' },
        body: offer.sdp
      })
      if (!sdpRes.ok) throw new Error('WebRTC negotiation failed')
      await pc.setRemoteDescription({ type: 'answer' as RTCSdpType, sdp: await sdpRes.text() })

    } catch (err: any) {
      setError(err.message)
      setIsConnecting(false)
      disconnect()
    }
  }, [userToken, worldStateContext, disconnect, onTranscript, onFallback])

  useEffect(() => () => { disconnect() }, [disconnect])

  if (!isConnected) {
    return (
      <div className="flex flex-col items-center gap-3">
        <button onClick={connect} disabled={isConnecting}
          className={`flex items-center gap-2 px-6 py-3 rounded-full font-medium transition-all ${isConnecting ? 'bg-gray-700 text-gray-400 cursor-wait' : 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg'}`}>
          <Mic size={18} />
          {isConnecting ? 'Connecting...' : 'Talk to JARVIS'}
        </button>
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative flex items-center justify-center w-20 h-20">
        {(isSpeaking || isListening) && (
          <>
            <div className={`absolute inset-0 rounded-full animate-ping opacity-20 ${isSpeaking ? 'bg-blue-400' : 'bg-green-400'}`} />
            <div className={`absolute inset-2 rounded-full animate-ping opacity-30 ${isSpeaking ? 'bg-blue-400' : 'bg-green-400'}`} />
          </>
        )}
        <button onClick={disconnect}
          className={`relative z-10 flex items-center justify-center w-14 h-14 rounded-full transition-all ${isSpeaking ? 'bg-blue-600 shadow-lg shadow-blue-500/40' : isListening ? 'bg-green-600 shadow-lg shadow-green-500/40' : 'bg-gray-700'}`}>
          <PhoneOff size={20} className="text-white" />
        </button>
      </div>
      <p className="text-sm text-gray-400">{isSpeaking ? 'JARVIS is speaking...' : isListening ? 'Listening...' : 'Connected'}</p>
      <p className="text-xs text-gray-600">Tap to end call</p>
    </div>
  )
}

// --- Web Speech API fallback mode ---

function SpeechAPIVoice({ userToken, onTranscript }: { userToken: string; onTranscript?: (text: string, role: 'user' | 'assistant') => void }) {
  const [isListening, setIsListening] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [status, setStatus] = useState('Ready')
  const recognitionRef = useRef<any>(null)

  const speak = useCallback((text: string) => {
    setIsSpeaking(true)
    const utt = new SpeechSynthesisUtterance(text)
    utt.rate = 1.05
    utt.onend = () => setIsSpeaking(false)
    window.speechSynthesis.speak(utt)
  }, [])

  const sendToAgent = useCallback(async (transcript: string) => {
    if (onTranscript) onTranscript(transcript, 'user')
    setStatus('Thinking...')
    try {
      const res = await fetch(`${JARVIS_URL}/agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${userToken}` },
        body: JSON.stringify({ messages: [{ role: 'user', content: transcript }] }),
      })
      if (!res.ok || !res.body) { setStatus('Error'); return }
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
      if (full) {
        if (onTranscript) onTranscript(full, 'assistant')
        speak(full)
      }
      setStatus('Ready')
    } catch { setStatus('Error') }
  }, [userToken, onTranscript, speak])

  const startListening = useCallback(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) { setStatus('Speech API not supported in this browser'); return }

    const rec = new SpeechRecognition()
    rec.lang = 'en-US'
    rec.interimResults = false
    rec.maxAlternatives = 1
    recognitionRef.current = rec

    rec.onstart = () => { setIsListening(true); setStatus('Listening...') }
    rec.onresult = (e: any) => {
      const transcript = e.results[0][0].transcript
      setIsListening(false)
      sendToAgent(transcript)
    }
    rec.onerror = (e: any) => { setIsListening(false); setStatus(`Error: ${e.error}`) }
    rec.onend = () => setIsListening(false)
    rec.start()
  }, [sendToAgent])

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
    window.speechSynthesis.cancel()
    setIsListening(false)
    setIsSpeaking(false)
    setStatus('Ready')
  }, [])

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative flex items-center justify-center w-20 h-20">
        {(isListening || isSpeaking) && (
          <div className={`absolute inset-0 rounded-full animate-ping opacity-20 ${isSpeaking ? 'bg-blue-400' : 'bg-green-400'}`} />
        )}
        <button
          onClick={isListening || isSpeaking ? stop : startListening}
          className={`relative z-10 flex items-center justify-center w-14 h-14 rounded-full transition-all ${
            isListening ? 'bg-green-600 shadow-lg shadow-green-500/40'
            : isSpeaking ? 'bg-blue-600 shadow-lg shadow-blue-500/40'
            : 'bg-gray-700 hover:bg-gray-600'
          }`}
        >
          {isListening || isSpeaking ? <MicOff size={20} className="text-white" /> : <Mic size={20} className="text-white" />}
        </button>
      </div>
      <p className="text-sm text-gray-400">{status}</p>
      <p className="text-xs text-gray-600">
        {isListening ? 'Speak now...' : isSpeaking ? 'JARVIS is speaking...' : 'Tap to speak'}
      </p>
      <p className="text-xs text-gray-700">Using browser speech (Realtime API unavailable)</p>
    </div>
  )
}

// --- Main export: tries Realtime first, falls back to Web Speech ---

export function VoiceMode({ worldStateContext, userToken, onTranscript }: VoiceModeProps) {
  const [useFallback, setUseFallback] = useState(false)

  if (useFallback) {
    return <SpeechAPIVoice userToken={userToken} onTranscript={onTranscript} />
  }

  return (
    <RealtimeVoice
      worldStateContext={worldStateContext}
      userToken={userToken}
      onTranscript={onTranscript}
      onFallback={() => setUseFallback(true)}
    />
  )
}
