import { useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { api, type PriceCurve } from '../lib/api'

const currentHour = new Date().getHours()

export default function PriceChart() {
  const [curve, setCurve] = useState<PriceCurve | null>(null)

  useEffect(() => {
    api.priceCurve('francecentral').then(setCurve).catch(() => {})
    const interval = setInterval(() => {
      api.priceCurve('francecentral').then(setCurve).catch(() => {})
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  const data = curve?.data ?? []
  const gpuLabel = curve?.gpu_name ?? 'GPU'

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="spotGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} />
            <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v}`} />
        <Tooltip
          contentStyle={{
            background: 'white',
            border: '1px solid #e2e8f0',
            borderRadius: '12px',
            fontSize: '12px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
          }}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter={(value: any, name: any) => [`$${Number(value).toFixed(4)}/h`, name === 'spot' ? `Spot ${gpuLabel}` : 'On-Demand']}
        />
        <ReferenceLine
          x={`${currentHour.toString().padStart(2, '0')}h`}
          stroke="#6366f1"
          strokeDasharray="4 4"
          label={{ value: 'Now', position: 'top', fontSize: 10, fill: '#6366f1' }}
        />
        <Area type="monotone" dataKey="ondemand" stroke="#f87171" strokeWidth={1.5} strokeDasharray="6 4" fill="none" dot={false} />
        <Area type="monotone" dataKey="spot" stroke="#6366f1" strokeWidth={2} fill="url(#spotGrad)" dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
