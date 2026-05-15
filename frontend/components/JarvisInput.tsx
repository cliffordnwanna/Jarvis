"use client"
import { ArrowUp, Mic, MicOff, Square } from "lucide-react"
import { useRef, useState } from "react"

interface JarvisInputProps {
  inProgress: boolean
  onSend: (text: string) => void
  chatReady?: boolean
  onStop?: () => void
  onUpload?: () => void
  hideStopButton?: boolean
  isVisible?: boolean
}

export function JarvisInput({
  inProgress,
  onSend,
  chatReady = false,
  onStop,
  hideStopButton = false,
}: JarvisInputProps) {
  const [text, setText] = useState("")
  const [recording, setRecording] = useState(false)
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const submit = () => {
    const trimmed = text.trim()
    if (!trimmed || inProgress || !chatReady) return
    setText("")
    if (textareaRef.current) textareaRef.current.style.height = "auto"
    onSend(trimmed)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

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
      if (transcript.trim() && !inProgress && chatReady) {
        onSend(transcript.trim())
      }
    }
    recognition.onend = () => setRecording(false)
    recognition.onerror = () => setRecording(false)
    recognition.start()
  }

  const stopRecording = () => {
    recognitionRef.current?.stop()
    setRecording(false)
  }

  return (
    <div className="copilotKitInputContainer">
      <div className="copilotKitInput">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => {
            setText(e.target.value)
            e.target.style.height = "auto"
            e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`
          }}
          onKeyDown={handleKeyDown}
          placeholder="Message JARVIS…"
          rows={1}
          disabled={inProgress || !chatReady}
        />
        <div className="copilotKitInputControls">
          <button
            type="button"
            onClick={recording ? stopRecording : startRecording}
            disabled={inProgress}
            title={recording ? "Stop voice input" : "Voice input"}
            className={`copilotKitInputControlButton${recording ? " copilotKitPushToTalkRecording" : ""}`}
          >
            {recording ? <MicOff size={16} /> : <Mic size={16} />}
          </button>

          {inProgress && !hideStopButton ? (
            <button
              type="button"
              onClick={onStop}
              className="copilotKitInputControlButton"
              title="Stop generation"
            >
              <Square size={14} />
            </button>
          ) : (
            <button
              type="button"
              onClick={submit}
              disabled={!text.trim() || inProgress || !chatReady}
              className="copilotKitInputControlButton"
              title="Send message"
            >
              <ArrowUp size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
