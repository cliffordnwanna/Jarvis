'use client'
import { X } from 'lucide-react'
import type { WorldState } from '@/types'

interface Props {
  worldState: WorldState
  onClose: () => void
}

export default function WorldStateFloater({ worldState, onClose }: Props) {
  return (
    <div className="fixed bottom-4 right-4 w-96 max-h-96 overflow-auto rounded-xl border border-jarvis-border bg-jarvis-surface/95 backdrop-blur shadow-xl z-50">
      <div className="flex items-center justify-between px-3 py-2 border-b border-jarvis-border sticky top-0 bg-jarvis-surface">
        <span className="text-xs font-medium text-jarvis-muted">World State</span>
        <button onClick={onClose} className="text-jarvis-muted hover:text-jarvis-text">
          <X size={14} />
        </button>
      </div>
      <pre className="p-3 text-xs text-jarvis-muted font-mono whitespace-pre-wrap break-words">
        {JSON.stringify(worldState, null, 2)}
      </pre>
    </div>
  )
}
