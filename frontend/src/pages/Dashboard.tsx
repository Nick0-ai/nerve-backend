import { useEffect, useState } from 'react'
import { api, type DashboardStats, type RegionSummary } from '../lib/api'
import StatsCards from '../components/StatsCards'
import Card from '../components/Card'
import WorldMap from '../components/WorldMap'
import PriceChart from '../components/PriceChart'
import EventFeed from '../components/EventFeed'

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [regions, setRegions] = useState<RegionSummary[]>([])

  useEffect(() => {
    api.dashboardStats().then(setStats).catch(() => {})
    api.regionsSummary().then(setRegions).catch(() => {})
    const interval = setInterval(() => {
      api.dashboardStats().then(setStats).catch(() => {})
      api.regionsSummary().then(setRegions).catch(() => {})
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  const carbonColor = (v: number) =>
    v < 100 ? 'text-green-accent' : v < 200 ? 'text-amber-600' : 'text-red-500'
  const carbonDot = (v: number) =>
    v < 100 ? 'bg-green-accent' : v < 200 ? 'bg-amber-500' : 'bg-red-500'

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-text-secondary mt-1">
          Real-time FinOps & GreenOps monitoring — live data from Azure, Open-Meteo, Carbon Intensity UK
        </p>
      </div>

      {/* KPI Cards */}
      <StatsCards stats={stats} />

      {/* Main Grid */}
      <div className="grid grid-cols-3 gap-4">
        {/* Map */}
        <Card title="Infrastructure Map" subtitle={`${regions.length} European regions · ${regions.reduce((s, r) => s + r.gpu_count, 0)} GPU SKUs`} className="col-span-2">
          <WorldMap compact />
        </Card>

        {/* Event Feed */}
        <Card title="Live Events" subtitle="WebSocket feed">
          <EventFeed />
        </Card>
      </div>

      {/* Price Chart */}
      <Card title="Spot Price Curve (24h)" subtitle="Live scraped prices · France Central · On-Demand in red">
        <PriceChart />
      </Card>

      {/* Region Table — LIVE DATA */}
      <Card title="Region Overview" subtitle="Live data refreshed every 10s">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-text-secondary">
              <th className="pb-3 font-medium">Region</th>
              <th className="pb-3 font-medium">Location</th>
              <th className="pb-3 font-medium">Weather</th>
              <th className="pb-3 font-medium">Carbon</th>
              <th className="pb-3 font-medium">Cheapest Spot</th>
              <th className="pb-3 font-medium">Savings</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {regions.map((r) => (
              <tr key={r.region_id} className="hover:bg-surface-2 transition-colors">
                <td className="py-3 font-mono text-xs">{r.region_id}</td>
                <td className="py-3">{r.location}</td>
                <td className="py-3 text-xs">
                  {r.temperature_c.toFixed(1)}°C · {r.wind_kmh.toFixed(0)} km/h
                </td>
                <td className="py-3">
                  <span className={`inline-flex items-center gap-1 ${carbonColor(r.carbon_gco2_kwh)} text-xs font-medium`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${carbonDot(r.carbon_gco2_kwh)}`} />
                    {r.carbon_gco2_kwh.toFixed(0)} gCO2
                  </span>
                </td>
                <td className="py-3 font-mono text-xs">
                  ${r.cheapest_spot_price.toFixed(2)}/h ({r.cheapest_gpu_name})
                </td>
                <td className="py-3 font-semibold text-nerve">
                  {r.cheapest_savings_pct.toFixed(1)}%
                </td>
              </tr>
            ))}
            {regions.length === 0 && (
              <tr>
                <td colSpan={6} className="py-6 text-center text-text-secondary text-xs">
                  Loading live data...
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
