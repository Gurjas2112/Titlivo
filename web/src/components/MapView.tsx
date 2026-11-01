import * as maplibregl from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useRef } from 'react'
import { API, MAP_STYLE } from '../lib/api'

// MapLibre 6 runs its tile parsing in a module worker; give Vite's emitted file to it explicitly.
maplibregl.setWorkerUrl(workerUrl)

interface Props {
  highlightId?: string
  focus?: GeoJSON.Polygon
  onSelect?: (id: string) => void
  className?: string
  refreshKey?: number
}

const SEVERITY_COLOR: maplibregl.ExpressionSpecification = [
  'match',
  ['get', 'max_severity'],
  3,
  '#d92d20',
  2,
  '#f5a524',
  1,
  '#64748b',
  '#2ec4a6',
]

export default function MapView({ highlightId, focus, onSelect, className = '', refreshKey = 0 }: Props) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const selectRef = useRef(onSelect)
  selectRef.current = onSelect

  useEffect(() => {
    if (!el.current) return
    const m = new maplibregl.Map({
      container: el.current,
      style: MAP_STYLE,
      center: [75.5, 17.5],
      zoom: 4.6,
      attributionControl: { compact: true, customAttribution: 'Parcels: synthetic (Titlivo demo)' },
    })
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.current = m
    m.on('load', async () => {
      const data = await (await fetch(`${API}/v1/map`)).json()
      m.addSource('villages', { type: 'geojson', data: data.villages })
      m.addSource('parcels', { type: 'geojson', data: data.parcels, promoteId: 'id' })
      m.addLayer({ id: 'village-line', type: 'line', source: 'villages', paint: { 'line-color': '#0b1736', 'line-width': 2, 'line-dasharray': [2, 1] } })
      m.addLayer({
        id: 'parcel-fill',
        type: 'fill',
        source: 'parcels',
        paint: { 'fill-color': SEVERITY_COLOR, 'fill-opacity': ['case', ['==', ['get', 'id'], highlightId ?? ''], 0.85, 0.45] },
      })
      m.addLayer({
        id: 'parcel-line',
        type: 'line',
        source: 'parcels',
        paint: {
          'line-color': ['case', ['==', ['get', 'id'], highlightId ?? ''], '#0b1736', '#ffffff'],
          'line-width': ['case', ['==', ['get', 'id'], highlightId ?? ''], 3.5, 0.8],
        },
      })
      // Villages are tiny at state zoom: show them as markers until the parcels are visible.
      const points: GeoJSON.FeatureCollection = {
        type: 'FeatureCollection',
        features: data.villages.features.map((f: GeoJSON.Feature<GeoJSON.MultiPolygon>) => {
          const ring = f.geometry.coordinates[0][0]
          const [x, y] = ring.reduce(([a, b], [lon, lat]) => [a + lon, b + lat], [0, 0])
          return { type: 'Feature', properties: f.properties, geometry: { type: 'Point', coordinates: [x / ring.length, y / ring.length] } }
        }),
      }
      m.addSource('village-points', { type: 'geojson', data: points })
      m.addLayer({
        id: 'village-dot',
        type: 'circle',
        source: 'village-points',
        maxzoom: 12,
        paint: { 'circle-radius': 9, 'circle-color': '#ff7a00', 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 3 },
      })
      m.addLayer({
        id: 'village-label',
        type: 'symbol',
        source: 'village-points',
        maxzoom: 13.5,
        layout: { 'text-field': ['get', 'name'], 'text-size': 12, 'text-font': ['Noto Sans Bold'], 'text-offset': [0, 1.4], 'text-anchor': 'top' },
        paint: { 'text-color': '#0b1736', 'text-halo-color': '#ffffff', 'text-halo-width': 2 },
      })
      m.on('click', 'village-dot', (e: maplibregl.MapLayerMouseEvent) => {
        const p = e.features?.[0]?.geometry as GeoJSON.Point | undefined
        if (p) m.flyTo({ center: p.coordinates as [number, number], zoom: 14 })
      })
      m.on('click', 'parcel-fill', (e: maplibregl.MapLayerMouseEvent) => {
        const id = e.features?.[0]?.properties?.id
        if (id && selectRef.current) selectRef.current(id)
      })
      m.on('mouseenter', 'parcel-fill', () => (m.getCanvas().style.cursor = 'pointer'))
      m.on('mouseleave', 'parcel-fill', () => (m.getCanvas().style.cursor = ''))
      if (focus) fitTo(m, focus)
    })
    return () => m.remove()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highlightId])

  useEffect(() => {
    const m = map.current
    if (!m || !refreshKey) return
    fetch(`${API}/v1/map`)
      .then((r) => r.json())
      .then((d) => (m.getSource('parcels') as maplibregl.GeoJSONSource | undefined)?.setData(d.parcels))
  }, [refreshKey])

  return <div ref={el} className={`h-full min-h-[320px] w-full overflow-hidden rounded-2xl ${className}`} data-testid="map" />
}

function fitTo(m: maplibregl.Map, poly: GeoJSON.Polygon) {
  const b = new maplibregl.LngLatBounds()
  poly.coordinates[0].forEach((c: GeoJSON.Position) => b.extend(c as [number, number]))
  m.fitBounds(b, { padding: 120, maxZoom: 16, duration: 0 })
}
