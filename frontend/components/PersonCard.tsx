interface Props {
  name: string
  relationship_type: string
  strength_signal: string
  last_contacted_at: string
  notes_summary?: string
}

const strengthColor: Record<string, string> = {
  warm: 'text-green-400',
  cooling: 'text-yellow-400',
  cold: 'text-red-400',
}

export default function PersonCard({ name, relationship_type, strength_signal, last_contacted_at, notes_summary }: Props) {
  const lastContact = last_contacted_at
    ? new Date(last_contacted_at).toLocaleDateString()
    : 'Never'

  return (
    <div className="rounded-xl border border-jarvis-border bg-jarvis-surface p-4 w-72">
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="text-sm font-medium text-jarvis-text">{name}</p>
          <p className="text-xs text-jarvis-muted capitalize">{relationship_type}</p>
        </div>
        <span className={`text-xs font-medium capitalize ${strengthColor[strength_signal] || 'text-jarvis-muted'}`}>
          {strength_signal}
        </span>
      </div>
      <p className="text-xs text-jarvis-muted mb-2">Last contact: {lastContact}</p>
      {notes_summary && (
        <p className="text-xs text-jarvis-text/70 line-clamp-3">{notes_summary}</p>
      )}
    </div>
  )
}
