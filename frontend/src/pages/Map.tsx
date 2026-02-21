import { useState, useEffect } from 'react'
import { api, type RegionInfo } from '../lib/api'
import Card from '../components/Card'
import WorldMap from '../components/WorldMap'
import { Server, Cpu, Thermometer, Wind, Leaf } from 'lucide-react'

const REGIONS = ['francecentral', 'westeurope', 'uksouth']

export default function MapPage() {
  const [activeRegion, setActiveRegion] = useState<string>('francecentral')
  const [regionData, setRegionData] = useState<RegionInfo | null>(null)

  useEffect(() => {
    api.getRegion(activeRegion).then(setRegionData).catch(() => {})
  }, [activeRegion])

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Infrastructure Map</h1>
        <p className="text-sm text-text-secondary mt-1">
          Live view of European datacenter regions
        </p>
      </div>

      {/* Map */}
      <Card className="p-0 overflow-hidden">
        <div className="p-6 pb-0">
          <div className="flex items-center gap-2 mb-4">
            {REGIONS.map((r) => (
              <button
                key={r}
                onClick={() => setActiveRegion(r)}
                className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  activeRegion === r
                    ? 'bg-nerve text-white'
                    : 'bg-surface-2 text-text-secondary hover:text-text'
                }`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
        <WorldMap onSelectRegion={setActiveRegion} activeRegion={activeRegion} />
      </Card>

      {/* Region Detail */}
      {regionData && (
        <div className="grid grid-cols-3 gap-4">
          <Card title={regionData.region_name} subtitle={regionData.location} className="col-span-1">
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2 text-text-secondary">
                <Server className="w-4 h-4" />
                <span>{regionData.cloud_provider.toUpperCase()}</span>
              </div>
              <div className="flex items-center gap-2 text-text-secondary">
                <Cpu className="w-4 h-4" />
                <span>{regionData.availability_zones.length} Availability Zones</span>
              </div>
              {regionData.availability_zones[0] && (
                <>
                  <div className="flex items-center gap-2 text-text-secondary">
                    <Leaf className="w-4 h-4 text-green-accent" />
                    <span>{regionData.availability_zones[0].carbon_intensity_gco2_kwh} gCO2/kWh ({regionData.availability_zones[0].carbon_index})</span>
                  </div>
                  <div className="flex items-center gap-2 text-text-secondary">
                    <Thermometer className="w-4 h-4" />
                    <span>{regionData.availability_zones[0].temperature_c}°C</span>
                  </div>
                  <div className="flex items-center gap-2 text-text-secondary">
                    <Wind className="w-4 h-4" />
                    <span>{regionData.availability_zones[0].wind_kmh} km/h</span>
                  </div>
                </>
              )}
            </div>
          </Card>

          {/* AZ Cards */}
          {regionData.availability_zones.map((az) => (
            <Card key={az.az_id} title={az.az_name} subtitle={az.az_id}>
              <div className="space-y-2">
                {az.gpu_instances.slice(0, 4).map((gpu) => (
                  <div
                    key={gpu.sku}
                    className="flex items-center justify-between py-2 border-b border-border last:border-0"
                  >
                    <div>
                      <div className="text-xs font-medium">{gpu.gpu_name}</div>
                      <div className="text-[10px] font-mono text-text-secondary">{gpu.sku}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-bold text-nerve">${gpu.spot_price_usd_hr}/h</div>
                      <div className="text-[10px] text-text-secondary line-through">
                        ${gpu.ondemand_price_usd_hr}/h
                      </div>
                    </div>
                  </div>
                ))}
                {az.gpu_instances.length > 4 && (
                  <div className="text-[10px] text-text-secondary text-center pt-1">
                    +{az.gpu_instances.length - 4} more GPUs
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
