'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '../../lib/supabase'

const JARVIS_URL = process.env.NEXT_PUBLIC_JARVIS_URL || 'http://localhost:8000'

type Step = 'name' | 'tour'

const slides = [
  {
    icon: '🌍',
    title: 'Always aware of your world',
    description: "JARVIS knows your location, weather, and time. Ask anything — should I carry an umbrella? What's the temperature? Is it a good time to leave?",
    example: '"What\'s the weather like right now?"'
  },
  {
    icon: '👥',
    title: 'Remembers your people',
    description: 'Add anyone important to you. JARVIS remembers their details, birthdays, and your history together.',
    example: '"Add Cherry to my people. She\'s my sister and a physiotherapist."'
  },
  {
    icon: '⏰',
    title: 'Reminders and timers',
    description: 'Set reminders for specific times or countdown timers for anything. JARVIS will alert you when it\'s time.',
    example: '"Remind me to call mum at noon. Set a 10 minute timer."'
  },
  {
    icon: '🗺️',
    title: 'Find places and directions',
    description: 'Find restaurants, churches, ATMs, pharmacies near you. Get real traffic-aware directions to anywhere.',
    example: '"Find a restaurant near me. How long to get to work?"'
  },
  {
    icon: '🎯',
    title: 'Goals and daily planning',
    description: 'Track your goals and let JARVIS proactively remind you. Every morning you get a briefing with what matters today.',
    example: '"Add getting a remote job as a goal. What are my priorities today?"'
  },
]

export default function OnboardingPage() {
  const router = useRouter()
  const [step, setStep] = useState<Step>('name')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [currentSlide, setCurrentSlide] = useState(0)

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
      setStep('tour')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Something went wrong')
      setLoading(false)
    }
  }

  if (step === 'tour') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-950 px-6">

        {/* Header */}
        <div className="w-full max-w-sm mb-8 flex items-center justify-between">
          <h2 className="text-white font-semibold">Here&apos;s what JARVIS can do</h2>
          <button
            onClick={() => router.push('/')}
            className="text-gray-500 text-sm hover:text-gray-300 transition-colors"
          >
            Skip
          </button>
        </div>

        {/* Slide card */}
        <div className="w-full max-w-sm bg-gray-900 rounded-2xl p-8 border border-white/10">
          <div className="text-5xl mb-6 text-center">{slides[currentSlide].icon}</div>
          <h3 className="text-white text-xl font-bold mb-3 text-center">
            {slides[currentSlide].title}
          </h3>
          <p className="text-gray-400 text-sm text-center leading-relaxed mb-6">
            {slides[currentSlide].description}
          </p>
          <div className="bg-gray-800/60 rounded-xl px-4 py-3 border border-white/5">
            <p className="text-blue-400 text-xs text-center italic">
              {slides[currentSlide].example}
            </p>
          </div>
        </div>

        {/* Dot indicators */}
        <div className="flex gap-2 mt-6 mb-8">
          {slides.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrentSlide(i)}
              className={`h-2 rounded-full transition-all ${
                i === currentSlide ? 'bg-blue-500 w-4' : 'bg-gray-600 w-2'
              }`}
            />
          ))}
        </div>

        {/* Navigation */}
        <div className="w-full max-w-sm flex gap-3">
          {currentSlide > 0 && (
            <button
              onClick={() => setCurrentSlide(prev => prev - 1)}
              className="flex-1 py-3 rounded-xl border border-white/10
                         text-gray-400 text-sm hover:border-white/20 transition-colors"
            >
              Back
            </button>
          )}
          <button
            onClick={() => {
              if (currentSlide < slides.length - 1) {
                setCurrentSlide(prev => prev + 1)
              } else {
                router.push('/')
              }
            }}
            className="flex-1 py-3 rounded-xl bg-blue-600 hover:bg-blue-500
                       text-white text-sm font-medium transition-colors"
          >
            {currentSlide < slides.length - 1 ? 'Next →' : 'Start chatting →'}
          </button>
        </div>

        {/* Progress */}
        <p className="text-gray-600 text-xs mt-4">{currentSlide + 1} of {slides.length}</p>

      </div>
    )
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
