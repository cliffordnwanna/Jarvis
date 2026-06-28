'use client'
// Phase 2: Individual person profile — notes, events, message suggestion
export default function PersonProfilePage({ params }: { params: { id: string } }) {
  return (
    <div className="p-8 text-jarvis-muted">
      <h1 className="text-2xl font-semibold text-jarvis-text mb-2">Person Profile</h1>
      <p>ID: {params.id} — Coming in Phase 2.</p>
    </div>
  )
}
