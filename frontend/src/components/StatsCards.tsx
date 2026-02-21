import { DollarSign, Leaf, ShieldCheck, Activity } from 'lucide-react'
import type { DashboardStats } from '../lib/api'

interface Props {
  stats: DashboardStats | null
}

export default function StatsCards({ stats }: Props) {
  const cards = [
    {
      label: 'Savings',
      value: stats ? `${stats.total_savings_eur.toFixed(0)} EUR` : '—',
      sub: stats ? `${stats.avg_savings_pct}% avg` : '',
      icon: DollarSign,
      color: 'text-nerve',
      bg: 'bg-nerve/10',
    },
    {
      label: 'CO2 Saved',
      value: stats ? `${(stats.total_co2_saved_grams / 1000).toFixed(1)} kg` : '—',
      sub: 'vs worst region',
      icon: Leaf,
      color: 'text-green-accent',
      bg: 'bg-green-accent/10',
    },
    {
      label: 'Checkpoints',
      value: stats ? `${stats.total_checkpoints_saved}` : '—',
      sub: 'saves completed',
      icon: ShieldCheck,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
    },
    {
      label: 'Uptime',
      value: stats ? `${stats.uptime_pct}%` : '—',
      sub: `${stats?.total_evictions_handled ?? 0} evictions handled`,
      icon: Activity,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50',
    },
  ]

  return (
    <div className="grid grid-cols-4 gap-4">
      {cards.map((c) => (
        <div
          key={c.label}
          className="bg-white rounded-2xl border border-border p-5 animate-slide-up"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">
              {c.label}
            </span>
            <div className={`w-8 h-8 rounded-lg ${c.bg} flex items-center justify-center`}>
              <c.icon className={`w-4 h-4 ${c.color}`} />
            </div>
          </div>
          <div className="text-2xl font-bold tracking-tight">{c.value}</div>
          <div className="text-xs text-text-secondary mt-1">{c.sub}</div>
        </div>
      ))}
    </div>
  )
}
