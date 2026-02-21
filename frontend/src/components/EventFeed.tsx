import { useEffect, useState } from 'react'
import { connect, subscribe, type WSEvent } from '../lib/ws'
import { ArrowRightLeft, Clock, DollarSign, ShieldCheck } from 'lucide-react'

const EVENT_ICONS: Record<string, typeof DollarSign> = {
  az_price_update: DollarSign,
  checkpoint_event: ShieldCheck,
  migration_complete: ArrowRightLeft,
  timeshift_scheduled: Clock,
}

const EVENT_COLORS: Record<string, string> = {
  az_price_update: 'text-nerve bg-nerve/10',
  checkpoint_event: 'text-amber-600 bg-amber-50',
  migration_complete: 'text-emerald-600 bg-emerald-50',
  timeshift_scheduled: 'text-blue-600 bg-blue-50',
}

function formatEvent(e: WSEvent): string {
  switch (e.type) {
    case 'az_price_update':
      return `${e.instance} in ${e.az}: $${(e.old_price as number)?.toFixed(2)} → $${(e.new_price as number)?.toFixed(2)}`
    case 'checkpoint_event':
      return `${e.job_id}: ${e.status} (${e.progress_pct}%)`
    case 'migration_complete':
      return `${e.job_id}: ${e.from_az} → ${e.to_az} (0ms downtime)`
    case 'timeshift_scheduled':
      return `${e.job_id}: saves $${(e.estimated_savings_usd as number)?.toFixed(2)}`
    default:
      return e.type
  }
}

export default function EventFeed() {
  const [events, setEvents] = useState<WSEvent[]>([])

  useEffect(() => {
    connect()
    const unsub = subscribe((event) => {
      if (event.type === 'connected' || event.type === 'pong') return
      setEvents((prev) => [event, ...prev].slice(0, 50))
    })
    return unsub
  }, [])

  return (
    <div className="space-y-2 max-h-80 overflow-y-auto">
      {events.length === 0 && (
        <div className="text-sm text-text-secondary text-center py-8">
          Waiting for live events...
        </div>
      )}
      {events.map((e, i) => {
        const Icon = EVENT_ICONS[e.type] ?? DollarSign
        const color = EVENT_COLORS[e.type] ?? 'text-gray-600 bg-gray-50'
        return (
          <div key={i} className="flex items-start gap-3 py-2 animate-slide-up">
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${color}`}>
              <Icon className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-xs font-medium truncate">{formatEvent(e)}</div>
              <div className="text-[10px] text-text-secondary font-mono">
                {new Date(e.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
