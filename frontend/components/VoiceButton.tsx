"use client"
import { Mic, MicOff } from "lucide-react"
import { useRef, useState } from "react"
import { useCopilotChat } from "@copilotkit/react-core"

export function VoiceButton({ compact = false }: { compact?: boolean }) {
  const [recording, setRecording] = useState(false)
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-deprecated
  const { appendMessage } = useCopilotChat()

  const startRecording = () => {
    if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) return
    const SpeechRecognitionCtor =
      (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition
    const recognition = new SpeechRecognitionCtor() as SpeechRecognition
    recognitionRef.current = recognition

    recognition.continuous = false
    recognition.interimResults = false
    recognition.language = "en-US"

    recognition.onstart = () => setRecording(true)

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = Array.from(event.results)
        .map((r: SpeechRecognitionResult) => r[0].transcript)
        .join("")
      if (!transcript.trim()) return
      // eslint-disable-next-line @typescript-eslint/no-deprecated
      appendMessage({ role: "user", content: transcript, id: crypto.randomUUID() } as any)
    }

    recognition.onend = () => setRecording(false)
    recognition.onerror = () => setRecording(false)
    recognition.start()
  }

  const stopRecording = () => {
    recognitionRef.current?.stop()
    setRecording(false)
  }

  if (compact) {
    return (
      <button
        onClick={recording ? stopRecording : startRecording}
        title={recording ? "Stop voice input" : "Voice input"}
        className={`flex h-8 w-8 items-center justify-center rounded-lg transition-colors ${
          recording
            ? "bg-red-500/20 text-red-300 hover:bg-red-500/30"
            : "text-white/50 hover:bg-white/10 hover:text-white/80"
        }`}
      >
        {recording
          ? <MicOff className="h-4 w-4" />
          : <Mic className="h-4 w-4" />}
      </button>
    )
  }

  return (
    <button
      onClick={recording ? stopRecording : startRecording}
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs transition-colors ${
        recording
          ? "border-red-400/30 bg-red-950/30 text-red-200 hover:bg-red-950/40"
          : "border-white/10 bg-white/[0.02] text-white/70 hover:bg-white/[0.05] hover:text-white"
      }`}
      title={recording ? "Stop voice input" : "Start voice input"}
    >
      <span className={`h-2 w-2 rounded-full ${recording ? "bg-red-400 animate-pulse" : "bg-white/20"}`} />
      {recording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
    </button>
  )
}
