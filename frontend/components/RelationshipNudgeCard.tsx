interface Props {
  nudge_type: string
  person_name: string
  message: string
  suggested_message?: string
}

const typeIcon: Record<string, string> = {
  relationship_birthday: '🎂',
  relationship_cooling: '❄️',
  relationship_followup: '💬',
}

export default function RelationshipNudgeCard({ nudge_type, person_name, message, suggested_message }: Props) {
  const icon = typeIcon[nudge_type] || '👤'

  return (
    <div className="rounded-xl border border-jarvis-border bg-jarvis-surface p-4 w-72">
      <div className="flex items-center gap-2 mb-2">
        <span>{icon}</span>
        <span className="text-sm font-medium text-jarvis-text">{person_name}</span>
      </div>
      <p className="text-xs text-jarvis-muted mb-3">{message}</p>
      {suggested_message && (
        <div className="rounded-lg bg-jarvis-bg border border-jarvis-border p-2">
          <p className="text-xs text-jarvis-muted mb-1">Suggested message:</p>
          <p className="text-xs text-jarvis-text italic">"{suggested_message}"</p>
        </div>
      )}
    </div>
  )
}
