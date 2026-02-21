import { useState, useEffect } from 'react'
import { api, type RegionSummary } from '../lib/api'

// Static coords (geometry only — data is fetched live)
const REGION_COORDS: Record<string, { lat: number; lng: number }> = {
  francecentral: { lat: 48.86, lng: 2.35 },
  westeurope: { lat: 52.37, lng: 4.90 },
  uksouth: { lat: 51.51, lng: -0.13 },
}

function project(lat: number, lng: number): [number, number] {
  const x = ((lng + 25) / 70) * 800
  const y = ((65 - lat) / 30) * 400
  return [x, y]
}

interface Props {
  onSelectRegion?: (id: string) => void
  activeRegion?: string | null
  compact?: boolean
}

export default function WorldMap({ onSelectRegion, activeRegion, compact }: Props) {
  const [hovered, setHovered] = useState<string | null>(null)
  const [regions, setRegions] = useState<RegionSummary[]>([])
  const height = compact ? 260 : 400

  useEffect(() => {
    api.regionsSummary().then(setRegions).catch(() => {})
    const interval = setInterval(() => {
      api.regionsSummary().then(setRegions).catch(() => {})
    }, 15000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="relative w-full" style={{ height }}>
      <svg viewBox="0 0 800 400" className="w-full h-full" style={{ background: 'transparent' }}>
        {/* Europe landmass (simplified) */}
        <path
          d="M280,180 L300,140 L350,120 L400,110 L450,100 L500,105 L550,120 L580,140
             L600,160 L590,200 L570,220 L540,250 L500,270 L450,280 L420,290
             L380,285 L350,270 L320,260 L290,240 L270,220 Z"
          fill="#e2e8f0" stroke="#cbd5e1" strokeWidth="1" opacity="0.5"
        />
        {/* UK */}
        <path
          d="M250,130 L260,110 L275,100 L280,115 L275,135 L265,145 L255,140 Z"
          fill="#e2e8f0" stroke="#cbd5e1" strokeWidth="1" opacity="0.5"
        />
        {/* Scandinavia */}
        <path
          d="M380,40 L400,20 L430,15 L450,30 L440,60 L420,80 L400,90 L385,70 Z"
          fill="#e2e8f0" stroke="#cbd5e1" strokeWidth="1" opacity="0.5"
        />
        {/* Iberia */}
        <path
          d="M240,250 L270,235 L310,240 L330,260 L320,290 L280,300 L245,290 L230,270 Z"
          fill="#e2e8f0" stroke="#cbd5e1" strokeWidth="1" opacity="0.5"
        />
        {/* Italy */}
        <path
          d="M400,220 L410,240 L420,270 L415,290 L405,300 L395,285 L390,260 L395,235 Z"
          fill="#e2e8f0" stroke="#cbd5e1" strokeWidth="1" opacity="0.5"
        />

        {/* Connection lines */}
        {regions.map((r, i) => {
          const next = regions[(i + 1) % regions.length]
          const coords1 = REGION_COORDS[r.region_id]
          const coords2 = REGION_COORDS[next.region_id]
          if (!coords1 || !coords2) return null
          const [x1, y1] = project(coords1.lat, coords1.lng)
          const [x2, y2] = project(coords2.lat, coords2.lng)
          return (
            <line
              key={`line-${r.region_id}-${next.region_id}`}
              x1={x1} y1={y1} x2={x2} y2={y2}
              stroke="#6366f1" strokeWidth="1" strokeDasharray="6 4" opacity="0.3"
            />
          )
        })}

        {/* Datacenter nodes — LIVE DATA */}
        {regions.map((r) => {
          const coords = REGION_COORDS[r.region_id]
          if (!coords) return null
          const [cx, cy] = project(coords.lat, coords.lng)
          const isActive = activeRegion === r.region_id
          const isHovered = hovered === r.region_id
          const carbonColor = r.carbon_gco2_kwh < 100 ? '#16a34a' : r.carbon_gco2_kwh < 200 ? '#d97706' : '#ef4444'

          return (
            <g
              key={r.region_id}
              onClick={() => onSelectRegion?.(r.region_id)}
              onMouseEnter={() => setHovered(r.region_id)}
              onMouseLeave={() => setHovered(null)}
              className="cursor-pointer"
            >
              {/* Pulse ring */}
              <circle cx={cx} cy={cy} r="20" fill="#6366f1" opacity="0.08" className="animate-pulse-dot" />
              <circle cx={cx} cy={cy} r="12" fill="#6366f1" opacity="0.15" className="animate-pulse-dot" />

              {/* Core dot */}
              <circle
                cx={cx} cy={cy} r="6"
                fill={isActive ? '#4f46e5' : '#6366f1'}
                stroke="white" strokeWidth="2"
              />

              {/* Label — LIVE price + carbon */}
              <text x={cx} y={cy - 28} textAnchor="middle" className="text-[11px] font-semibold" fill="#0f172a">
                {r.location.split(',')[0]}
              </text>
              <text x={cx} y={cy - 16} textAnchor="middle" className="text-[9px] font-mono" fill="#64748b">
                ${r.cheapest_spot_price.toFixed(2)}/h · {r.carbon_gco2_kwh.toFixed(0)} gCO2
              </text>

              {/* Tooltip on hover — LIVE data */}
              {isHovered && (
                <foreignObject x={cx - 90} y={cy + 15} width="180" height="100">
                  <div className="bg-white border border-border rounded-xl p-3 shadow-lg text-center">
                    <div className="text-xs font-bold">{r.region_name}</div>
                    <div className="text-[10px] text-text-secondary mt-1">
                      {r.cheapest_gpu_name} @ ${r.cheapest_spot_price.toFixed(2)}/h
                      <span className="text-nerve ml-1">({r.cheapest_savings_pct.toFixed(0)}% off)</span>
                    </div>
                    <div className="text-[10px] mt-0.5" style={{ color: carbonColor }}>
                      {r.carbon_gco2_kwh.toFixed(0)} gCO2/kWh ({r.carbon_index})
                    </div>
                    <div className="text-[10px] text-text-secondary mt-0.5">
                      {r.temperature_c.toFixed(1)}°C · {r.wind_kmh.toFixed(0)} km/h wind
                    </div>
                  </div>
                </foreignObject>
              )}
            </g>
          )
        })}

        {/* Grid lines */}
        {[0, 200, 400, 600, 800].map((x) => (
          <line key={`gx-${x}`} x1={x} y1="0" x2={x} y2="400" stroke="#e2e8f0" strokeWidth="0.5" opacity="0.3" />
        ))}
        {[0, 100, 200, 300, 400].map((y) => (
          <line key={`gy-${y}`} x1="0" y1={y} x2="800" y2={y} stroke="#e2e8f0" strokeWidth="0.5" opacity="0.3" />
        ))}
      </svg>

      {/* Live badge */}
      <div className="absolute top-3 right-3 flex items-center gap-1.5 bg-white/90 border border-border rounded-full px-3 py-1">
        <div className="w-1.5 h-1.5 rounded-full bg-green-accent animate-pulse-dot" />
        <span className="text-[10px] font-medium text-text-secondary">LIVE</span>
      </div>
    </div>
  )
}
