const BASE = process.env.NEXT_PUBLIC_JARVIS_URL || "http://localhost:8000"

async function fetchJSON(url: string, options?: RequestInit) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const api = {
  health: () => fetchJSON(`${BASE}/health`),

  worldState: () => fetchJSON(`${BASE}/world-state`),

  nudges: {
    list: (): Promise<Nudge[]> => fetchJSON(`${BASE}/nudges`),
    dismiss: (id: string) => fetchJSON(`${BASE}/nudges/${id}`, { method: "DELETE" }),
    clearAll: () => fetchJSON(`${BASE}/nudges`, { method: "DELETE" }),
  },

  memory: {
    goals: (userId: string) => fetchJSON(`${BASE}/memory/goals/${userId}`),
    createGoal: (data: { user_id: string; name: string; urgency?: string }) =>
      fetchJSON(`${BASE}/memory/goals`, { method: "POST", body: JSON.stringify(data) }),
  },
}

export interface Nudge {
  id: string
  type: "weather" | "food" | "traffic" | "goal" | "calendar" | "battery" | string
  message: string
  card_data: Record<string, unknown>
  priority: "low" | "medium" | "high"
}
