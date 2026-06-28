interface Place {
  name: string
  distance_m: number
}

interface Props {
  category: string
  places_json: string
}

export default function PlacesCard({ category, places_json }: Props) {
  let places: Place[] = []
  try {
    places = JSON.parse(places_json)
  } catch (_) {}

  return (
    <div className="rounded-xl border border-jarvis-border bg-jarvis-surface p-4 w-72">
      <div className="mb-3">
        <span className="text-xs text-jarvis-muted uppercase tracking-widest">Nearby</span>
        <span className="ml-2 text-xs text-jarvis-text capitalize">{category}</span>
      </div>
      <div className="space-y-2">
        {places.slice(0, 4).map((p, i) => (
          <div key={i} className="flex justify-between text-xs">
            <span className="text-jarvis-text">{p.name}</span>
            <span className="text-jarvis-muted">{p.distance_m < 1000 ? `${p.distance_m}m` : `${(p.distance_m / 1000).toFixed(1)}km`}</span>
          </div>
        ))}
        {places.length === 0 && <p className="text-xs text-jarvis-muted">No results found nearby</p>}
      </div>
    </div>
  )
}
