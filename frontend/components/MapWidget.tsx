'use client'

import { useEffect, useRef } from 'react'

interface Place {
  name: string
  lat: number
  lng: number
  type?: string
}

interface Route {
  from: { lat: number; lng: number; label: string }
  to: { lat: number; lng: number; label: string }
  waypoints?: [number, number][]
}

interface MapWidgetProps {
  places?: Place[]
  route?: Route
  userLat?: number
  userLng?: number
  title?: string
}

export function MapWidget({ places, route, userLat, userLng, title }: MapWidgetProps) {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<any>(null)

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return

    import('leaflet').then(L => {
      delete (L.Icon.Default.prototype as any)._getIconUrl
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      })

      let centerLat = userLat || 6.5244
      let centerLng = userLng || 3.3792
      let zoom = 14

      if (places && places.length > 0) {
        centerLat = places[0].lat
        centerLng = places[0].lng
      } else if (route) {
        centerLat = (route.from.lat + route.to.lat) / 2
        centerLng = (route.from.lng + route.to.lng) / 2
        zoom = 12
      }

      const map = L.map(mapRef.current!, {
        center: [centerLat, centerLng],
        zoom,
        zoomControl: true,
        attributionControl: false,
      })
      mapInstanceRef.current = map

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
      }).addTo(map)

      if (userLat && userLng) {
        const userIcon = L.divIcon({
          html: '<div style="width:12px;height:12px;background:#3b82f6;border:2px solid white;border-radius:50%;box-shadow:0 0 6px rgba(59,130,246,0.8)"></div>',
          iconSize: [12, 12],
          iconAnchor: [6, 6],
          className: '',
        })
        L.marker([userLat, userLng], { icon: userIcon }).addTo(map).bindPopup('You are here')
      }

      if (places && places.length > 0) {
        const bounds: [number, number][] = []
        if (userLat && userLng) bounds.push([userLat, userLng])

        places.forEach((place, i) => {
          const icon = L.divIcon({
            html: `<div style="background:#ef4444;color:white;border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:bold;border:2px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3)">${i + 1}</div>`,
            iconSize: [24, 24],
            iconAnchor: [12, 12],
            className: '',
          })
          L.marker([place.lat, place.lng], { icon })
            .addTo(map)
            .bindPopup(`<b>${place.name}</b>${place.type ? `<br/>${place.type}` : ''}`)
          bounds.push([place.lat, place.lng])
        })

        if (bounds.length > 1) map.fitBounds(bounds, { padding: [30, 30] })
      }

      if (route) {
        const fromIcon = L.divIcon({
          html: '<div style="background:#22c55e;color:white;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:bold;border:2px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3)">A</div>',
          iconSize: [28, 28],
          iconAnchor: [14, 14],
          className: '',
        })
        L.marker([route.from.lat, route.from.lng], { icon: fromIcon }).addTo(map).bindPopup(route.from.label)

        const toIcon = L.divIcon({
          html: '<div style="background:#ef4444;color:white;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:bold;border:2px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3)">B</div>',
          iconSize: [28, 28],
          iconAnchor: [14, 14],
          className: '',
        })
        L.marker([route.to.lat, route.to.lng], { icon: toIcon }).addTo(map).bindPopup(route.to.label)

        const waypoints: [number, number][] = route.waypoints && route.waypoints.length > 2
          ? route.waypoints as [number, number][]
          : [[route.from.lat, route.from.lng], [route.to.lat, route.to.lng]]
        const polyline = L.polyline(waypoints, { color: '#3b82f6', weight: 4, opacity: 0.8 }).addTo(map)
        map.fitBounds(polyline.getBounds(), { padding: [40, 40] })
      }
    })

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="mt-3 rounded-xl overflow-hidden border border-white/10 shadow-lg">
      {title && (
        <div className="bg-gray-800/80 px-3 py-2 text-xs text-gray-400 border-b border-white/5 flex items-center gap-2">
          <span>🗺️</span>
          <span>{title}</span>
        </div>
      )}
      <div ref={mapRef} style={{ height: '220px', width: '100%' }} />
    </div>
  )
}
