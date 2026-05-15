CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS location_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    lat FLOAT, lng FLOAT, city TEXT,
    location_type TEXT DEFAULT 'unknown',
    location_label TEXT,
    arrived_at TIMESTAMPTZ DEFAULT NOW(),
    left_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS behavioral_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    pattern_key TEXT NOT NULL,
    pattern_value JSONB NOT NULL,
    confidence FLOAT DEFAULT 0.5,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, pattern_key)
);

CREATE TABLE IF NOT EXISTS goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    urgency TEXT DEFAULT 'medium',
    last_touched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS nudge_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    nudge_type TEXT,
    message TEXT,
    delivered_at TIMESTAMPTZ DEFAULT NOW(),
    accepted BOOLEAN,
    ignored BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS meal_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    logged_at TIMESTAMPTZ DEFAULT NOW(),
    description TEXT
);
