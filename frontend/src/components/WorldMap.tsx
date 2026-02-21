import { useState } from 'react'

interface Datacenter {
  id: string
  name: string
  location: string
  lat: number
  lng: number
  carbon_gco2: number
  cheapest_gpu: string
  cheapest_price: number
  status: 'active' | 'idle'
}

const DATACENTERS: Datacenter[] = [
  {
    id: 'francecentral',
    name: 'France Central',
    location: 'Paris',
    lat: 48.86,
    lng: 2.35,
    carbon_gco2: 56,
    cheapest_gpu: 'V100',
    cheapest_price: 0.66,
    status: 'active',
  },
  {
    id: 'westeurope',
    name: 'West Europe',
    location: 'Amsterdam',
    lat: 52.37,
    lng: 4.90,
    carbon_gco2: 328,
    cheapest_gpu: 'H100',
    cheapest_price: 1.64,
    status: 'active',
  },
  {
    id: 'uksouth',
    name: 'UK South',
    location: 'London',
    lat: 51.51,
    lng: -0.13,
    carbon_gco2: 55,
    cheapest_gpu: 'T4',
    cheapest_price: 0.36,
    status: 'active',
  },
]

// Simple Mercator projection for Europe-focused view
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
  const height = compact ? 260 : 400

  return (
    <div className="relative w-full" style={{ height }}>
      <svg viewBox="0 0 800 400" className="w-full h-full" style={{ background: 'transparent' }}>
        {/* Europe landmass (simplified) */}
        <path
          d="M280,180 L300,140 L350,120 L400,110 L450,100 L500,105 L550,120 L580,140
             L600,160 L590,200 L570,220 L540,250 L500,270 L450,280 L420,290
             L380,285 L350,270 L320,260 L290,240 L270,220 Z"
          fill="#e2e8f0"
          stroke="#cbd5e1"
          strokeWidth="1"
          opacity="0.5"
        />
        {/* UK */}
        <path
          d="M250,130 L260,110 L275,100 L280,115 L275,135 L265,145 L255,140 Z"
          fill="#e2e8f0"
          stroke="#cbd5e1"
          strokeWidth="1"
          opacity="0.5"
        />
        {/* Scandinavia */}
        <path
          d="M380,40 L400,20 L430,15 L450,30 L440,60 L420,80 L400,90 L385,70 Z"
          fill="#e2e8f0"
          stroke="#cbd5e1"
          strokeWidth="1"
          opacity="0.5"
        />
        {/* Iberia */}
        <path
          d="M240,250 L270,235 L310,240 L330,260 L320,290 L280,300 L245,290 L230,270 Z"
          fill="#e2e8f0"
          stroke="#cbd5e1"
          strokeWidth="1"
          opacity="0.5"
        />
        {/* Italy */}
        <path
          d="M400,220 L410,240 L420,270 L415,290 L405,300 L395,285 L390,260 L395,235 Z"
          fill="#e2e8f0"
          stroke="#cbd5e1"
          strokeWidth="1"
          opacity="0.5"
        />

        {/* Connection lines between datacenters */}
        {DATACENTERS.map((dc, i) => {
          const next = DATACENTERS[(i + 1) % DATACENTERS.length]
          const [x1, y1] = project(dc.lat, dc.lng)
          const [x2, y2] = project(next.lat, next.lng)
          return (
            <line
              key={`line-${dc.id}-${next.id}`}
              x1={x1} y1={y1} x2={x2} y2={y2}
              stroke="#6366f1"
              strokeWidth="1"
              strokeDasharray="6 4"
              opacity="0.3"
            />
          )
        })}

        {/* Datacenter nodes */}
        {DATACENTERS.map((dc) => {
          const [cx, cy] = project(dc.lat, dc.lng)
          const isActive = activeRegion === dc.id
          const isHovered = hovered === dc.id

          return (
            <g
              key={dc.id}
              onClick={() => onSelectRegion?.(dc.id)}
              onMouseEnter={() => setHovered(dc.id)}
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
                stroke="white"
                strokeWidth="2"
              />

              {/* Label */}
              <text
                x={cx}
                y={cy - 28}
                textAnchor="middle"
                className="text-[11px] font-semibold"
                fill="#0f172a"
              >
                {dc.location}
              </text>
              <text
                x={cx}
                y={cy - 16}
                textAnchor="middle"
                className="text-[9px] font-mono"
                fill="#64748b"
              >
                ${dc.cheapest_price}/h · {dc.carbon_gco2} gCO2
              </text>

              {/* Tooltip on hover */}
              {isHovered && (
                <foreignObject x={cx - 80} y={cy + 15} width="160" height="80">
                  <div className="bg-white border border-border rounded-xl p-3 shadow-lg text-center">
                    <div className="text-xs font-bold">{dc.name}</div>
                    <div className="text-[10px] text-text-secondary mt-1">
                      Cheapest: {dc.cheapest_gpu} @ ${dc.cheapest_price}/h
                    </div>
                    <div className="text-[10px] text-green-accent mt-0.5">
                      {dc.carbon_gco2} gCO2/kWh
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
