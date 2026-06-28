interface Props {
  condition: string
  temp_c: number
  feels_like_c: number
  humidity_pct: number
  rain_prob_1h: number
  city: string
}

export default function WeatherCard({ condition, temp_c, feels_like_c, humidity_pct, rain_prob_1h, city }: Props) {
  return (
    <div className="rounded-xl border border-jarvis-border bg-jarvis-surface p-4 w-72">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-jarvis-muted uppercase tracking-widest">Weather</span>
        <span className="text-xs text-jarvis-muted">{city}</span>
      </div>
      <div className="flex items-end gap-3 mb-3">
        <span className="text-4xl font-light">{Math.round(temp_c)}°</span>
        <span className="text-sm text-jarvis-muted mb-1 capitalize">{condition?.replace('_', ' ')}</span>
      </div>
      <div className="space-y-1.5 text-xs text-jarvis-muted">
        <div className="flex justify-between">
          <span>Feels like</span>
          <span className="text-jarvis-text">{Math.round(feels_like_c)}°C</span>
        </div>
        <div className="flex justify-between">
          <span>Humidity</span>
          <span className="text-jarvis-text">{humidity_pct}%</span>
        </div>
        {rain_prob_1h > 0 && (
          <div className="flex justify-between">
            <span>Rain next hour</span>
            <span className={rain_prob_1h > 0.6 ? 'text-yellow-400' : 'text-jarvis-text'}>
              {Math.round(rain_prob_1h * 100)}%
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
