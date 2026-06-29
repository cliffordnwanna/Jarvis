'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '../../lib/supabase'

const JARVIS_URL = process.env.NEXT_PUBLIC_JARVIS_URL || 'http://localhost:8000'

export default function OnboardingPage() {
  const router = useRouter()
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('Please enter your name')
      return
    }
    setLoading(true)
    setError('')
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) throw new Error('Not authenticated')

      const res = await fetch(`${JARVIS_URL}/users/profile`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ display_name: name.trim() }),
      })
      if (!res.ok) throw new Error('Failed to save')
      router.push('/')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Something went wrong')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm px-6">

        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Welcome to JARVIS</h1>
          <p className="text-gray-400 text-sm">Your personal AI. Let&apos;s start with your name.</p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-400 mb-2 block">
              What should JARVIS call you?
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
              placeholder="Your first name"
              autoFocus
              className="w-full px-4 py-3 rounded-xl bg-gray-800 border border-white/10
                         text-white placeholder-gray-500 text-base
                         focus:outline-none focus:border-blue-500 transition-colors"
            />
            {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
          </div>

          <button
            onClick={handleSubmit}
            disabled={loading || !name.trim()}
            className="w-full py-3 rounded-xl font-medium text-base transition-all
                       bg-blue-600 hover:bg-blue-500 text-white
                       disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? 'Saving...' : "Let's go →"}
          </button>
        </div>

        <p className="text-center text-xs text-gray-600 mt-6">
          You can change this anytime in settings.
        </p>
      </div>
    </div>
  )
}
