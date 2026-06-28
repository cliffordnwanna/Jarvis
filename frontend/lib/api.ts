const BASE = process.env.NEXT_PUBLIC_JARVIS_URL || 'http://localhost:8000'

async function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const { supabase } = await import('./supabase')
  const { data: { session } } = await supabase.auth.getSession()
  const token = session?.access_token

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string> || {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  return fetch(`${BASE}${path}`, { ...init, headers })
}

export const api = {
  health: async () => {
    const res = await fetch(`${BASE}/health`)
    return res.json()
  },

  worldState: async () => {
    const res = await authedFetch('/world-state')
    return res.json()
  },

  context: {
    update: async (payload: Record<string, unknown>) => {
      const res = await authedFetch('/context/update', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      return res.json()
    },
    latest: async () => {
      const res = await authedFetch('/context/latest')
      return res.json()
    },
  },

  nudges: {
    list: async () => {
      const res = await authedFetch('/nudges')
      return res.json()
    },
    dismiss: async (id: string) => {
      const res = await authedFetch(`/nudges/${id}`, { method: 'DELETE' })
      return res.json()
    },
    clearAll: async () => {
      const res = await authedFetch('/nudges', { method: 'DELETE' })
      return res.json()
    },
    action: async (id: string) => {
      const res = await authedFetch(`/nudges/${id}/action`, { method: 'POST' })
      return res.json()
    },
  },

  goals: {
    list: async () => {
      const res = await authedFetch('/goals')
      return res.json()
    },
    create: async (title: string, urgency = 'medium') => {
      const res = await authedFetch('/goals', {
        method: 'POST',
        body: JSON.stringify({ title, urgency }),
      })
      return res.json()
    },
    touch: async (id: string) => {
      const res = await authedFetch(`/goals/${id}/touch`, { method: 'POST' })
      return res.json()
    },
  },

  people: {
    list: async (circle?: string, strength?: string) => {
      const params = new URLSearchParams()
      if (circle) params.set('circle', circle)
      if (strength) params.set('strength', strength)
      const res = await authedFetch(`/people?${params}`)
      return res.json()
    },
    get: async (id: string) => {
      const res = await authedFetch(`/people/${id}`)
      return res.json()
    },
    suggestMessage: async (id: string) => {
      const res = await authedFetch(`/people/suggest-message/${id}`)
      return res.json()
    },
  },

  memory: {
    conversations: async () => {
      const res = await authedFetch('/memory/conversations')
      return res.json()
    },
    search: async (query: string) => {
      const res = await authedFetch('/memory/search', {
        method: 'POST',
        body: JSON.stringify({ query }),
      })
      return res.json()
    },
  },

  briefing: {
    morning: async () => {
      const res = await authedFetch('/briefing/morning')
      return res.json()
    },
  },

  voice: {
    token: async () => {
      const res = await authedFetch('/voice/token')
      return res.json()
    },
  },
}

export async function fetchNudges(token: string) {
  const res = await fetch(`${BASE}/nudges`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) return []
  return res.json()
}

export async function fetchMorningBriefing(token: string) {
  const res = await fetch(`${BASE}/briefing/morning`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) return null
  return res.json()
}

export async function dismissNudge(id: string, token: string) {
  await fetch(`${BASE}/nudges/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
}
