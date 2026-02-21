import { useEffect, useState } from 'react'
import { api, type DashboardStats } from '../lib/api'
import StatsCards from '../components/StatsCards'
import Card from '../components/Card'
import WorldMap from '../components/WorldMap'
import PriceChart from '../components/PriceChart'
import EventFeed from '../components/EventFeed'

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)

  useEffect(() => {
    api.dashboardStats().then(setStats).catch(() => {})
    const interval = setInterval(() => {
      api.dashboardStats().then(setStats).catch(() => {})
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-text-secondary mt-1">
          Real-time FinOps & GreenOps monitoring
        </p>
      </div>

      {/* KPI Cards */}
      <StatsCards stats={stats} />

      {/* Main Grid */}
      <div className="grid grid-cols-3 gap-4">
        {/* Map */}
        <Card title="Infrastructure Map" subtitle="3 European regions" className="col-span-2">
          <WorldMap compact />
        </Card>

        {/* Event Feed */}
        <Card title="Live Events" subtitle="WebSocket feed">
          <EventFeed />
        </Card>
      </div>

      {/* Price Chart */}
      <Card title="Spot Price Curve (24h)" subtitle="V100 — France Central · On-Demand in red">
        <PriceChart />
      </Card>

      {/* Region Table */}
      <Card title="Region Overview">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-text-secondary">
              <th className="pb-3 font-medium">Region</th>
              <th className="pb-3 font-medium">Location</th>
              <th className="pb-3 font-medium">Carbon</th>
              <th className="pb-3 font-medium">Cheapest Spot</th>
              <th className="pb-3 font-medium">Savings</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            <tr className="hover:bg-surface-2 transition-colors">
              <td className="py-3 font-mono text-xs">francecentral</td>
              <td className="py-3">Paris, France</td>
              <td className="py-3">
                <span className="inline-flex items-center gap-1 text-green-accent text-xs font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-accent" />
                  56 gCO2
                </span>
              </td>
              <td className="py-3 font-mono text-xs">$0.66/h (V100)</td>
              <td className="py-3 font-semibold text-nerve">81.5%</td>
            </tr>
            <tr className="hover:bg-surface-2 transition-colors">
              <td className="py-3 font-mono text-xs">westeurope</td>
              <td className="py-3">Amsterdam, NL</td>
              <td className="py-3">
                <span className="inline-flex items-center gap-1 text-amber-600 text-xs font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                  328 gCO2
                </span>
              </td>
              <td className="py-3 font-mono text-xs">$1.64/h (H100)</td>
              <td className="py-3 font-semibold text-nerve">84.1%</td>
            </tr>
            <tr className="hover:bg-surface-2 transition-colors">
              <td className="py-3 font-mono text-xs">uksouth</td>
              <td className="py-3">London, UK</td>
              <td className="py-3">
                <span className="inline-flex items-center gap-1 text-green-accent text-xs font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-accent" />
                  55 gCO2
                </span>
              </td>
              <td className="py-3 font-mono text-xs">$0.36/h (T4)</td>
              <td className="py-3 font-semibold text-nerve">75.0%</td>
            </tr>
          </tbody>
        </table>
      </Card>
    </div>
  )
}
