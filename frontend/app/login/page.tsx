'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Auth } from '@supabase/auth-ui-react'
import { ThemeSupa } from '@supabase/auth-ui-shared'
import { supabase } from '../../lib/supabase'

export default function LoginPage() {
  const router = useRouter()

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (session) {
        router.push('/')
      }
    })
    return () => subscription.unsubscribe()
  }, [router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm p-8 rounded-2xl border border-white/10 bg-gray-900">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-white tracking-tight">JARVIS</h1>
          <p className="text-sm text-gray-500 mt-1">Your personal AI</p>
        </div>
        <Auth
          supabaseClient={supabase}
          appearance={{
            theme: ThemeSupa,
            variables: {
              default: {
                colors: {
                  brand: '#3b82f6',
                  brandAccent: '#2563eb',
                  inputBackground: '#111827',
                  inputBorder: '#374151',
                  inputText: '#f9fafb',
                  inputPlaceholder: '#6b7280',
                }
              }
            }
          }}
          theme="dark"
          providers={['google']}
          redirectTo={typeof window !== 'undefined' ? `${window.location.origin}/` : '/'}
        />
      </div>
    </div>
  )
}
