export interface Person {
  id: string
  user_id: string
  name: string
  relationship_type: 'friend' | 'family' | 'colleague' | 'mentor' | 'acquaintance'
  circle: 'inner' | 'family' | 'work' | 'community'
  birthday?: string
  contact_frequency_days?: number
  last_contacted_at?: string
  strength_signal: 'warm' | 'cooling' | 'cold'
  notes_summary?: string
  phone?: string
  email?: string
  tags: string[]
  created_at: string
  updated_at: string
}

export interface RelationshipNote {
  id: string
  user_id: string
  person_id: string
  content: string
  extracted_facts: Fact[]
  source: 'voice' | 'text' | 'chat_extraction' | 'import'
  created_at: string
}

export interface Fact {
  type: string
  value: string
  date?: string
}

export interface RelationshipEvent {
  id: string
  user_id: string
  person_id: string
  event_type: 'birthday' | 'follow_up' | 'call' | 'meeting' | 'occasion' | 'check_in'
  title: string
  scheduled_at: string
  completed_at?: string
  nudge_sent: boolean
  context: Record<string, unknown>
  created_at: string
}

export interface Goal {
  id: string
  user_id: string
  title: string
  status: 'active' | 'paused' | 'completed'
  urgency: 'low' | 'medium' | 'high'
  last_touched_at: string
  created_at: string
}

export interface Nudge {
  id: string
  user_id: string
  nudge_type: string
  person_id?: string
  message: string
  priority: 'low' | 'medium' | 'high'
  delivered_at: string
  dismissed_at?: string
  actioned: boolean
}

export interface WorldState {
  user_id?: string
  _meta?: { schema_version: string; built_at: string; lat: number; lng: number }
  temporal?: {
    timestamp: string
    timezone: string
    day_of_week: string
    time_of_day: string
    is_weekend: boolean
    hour_decimal: number
    sunrise?: string
    sunset?: string
  }
  location?: {
    lat?: number
    lng?: number
    city?: string
    state?: string
    district?: string
    country?: string
    location_type?: string
  }
  environment?: {
    weather?: {
      condition?: string
      description?: string
      temp_c?: number
      feels_like_c?: number
      humidity_pct?: number
      wind_speed_kmh?: number
      forecast_1h_rain_prob?: number
      forecast_3h_rain_prob?: number
    }
    air_quality?: {
      aqi?: number
      category?: string
    }
  }
  device?: {
    network_type?: string
    platform?: string
    headphones_connected?: boolean
    preferred_modality?: string
  }
  cognitive?: {
    estimated_focus?: number
    estimated_fatigue?: number
    deep_work_likely?: boolean
    preferred_modality?: string
  }
  biological?: {
    hunger_probability?: number
    sleep_pressure?: number
    estimated_energy?: number
  }
  goals?: {
    active_goals?: Goal[]
    stale_count?: number
  }
  upcoming_relationship_events?: RelationshipEvent[]
}
