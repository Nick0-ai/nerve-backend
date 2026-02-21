import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

// Simulated 24h price curve (matches backend timeshifter.py)
const PRICE_DATA = Array.from({ length: 24 }, (_, h) => {
  const curve: Record<number, number> = {
    0: 0.25, 1: 0.18, 2: 0.10, 3: 0.08, 4: 0.10, 5: 0.15,
    6: 0.30, 7: 0.50, 8: 0.65, 9: 0.80, 10: 0.95, 11: 1.00,
    12: 0.98, 13: 0.95, 14: 0.90, 15: 0.82, 16: 0.75, 17: 0.70,
    18: 0.60, 19: 0.50, 20: 0.42, 21: 0.35, 22: 0.30, 23: 0.28,
  }
  const factor = curve[h] ?? 0.5
  return {
    hour: `${h.toString().padStart(2, '0')}h`,
    spot: +(0.66 * (0.5 + factor)).toFixed(3),
    ondemand: 3.58,
  }
})

const currentHour = new Date().getHours()

export default function PriceChart() {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={PRICE_DATA} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
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
          formatter={(value: any, name: any) => [`$${Number(value).toFixed(3)}/h`, name === 'spot' ? 'Spot V100' : 'On-Demand']}
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
