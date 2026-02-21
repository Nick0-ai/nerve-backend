const BASE = '/api'

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`)
  return res.json()
}

// Types
export interface GpuInstance {
  sku: string
  gpu_name: string
  gpu_count: number
  vcpus: number
  ram_gb: number
  spot_price_usd_hr: number
  ondemand_price_usd_hr: number
  savings_pct: number
  availability: string
}

export interface AZInfo {
  az_id: string
  az_name: string
  gpu_instances: GpuInstance[]
  carbon_intensity_gco2_kwh: number
  carbon_index: string
  temperature_c: number
  wind_kmh: number
  score: number | null
}

export interface RegionInfo {
  region_id: string
  region_name: string
  cloud_provider: string
  location: string
  availability_zones: AZInfo[]
}

export interface SimulateRequest {
  job_type: string
  model_name: string
  estimated_gpu_hours: number
  deadline: string
  min_gpu_memory_gb: number
  framework: string
  checkpoint_interval_min: number
  preferred_region?: string
}

export interface SimulateResponse {
  decision: {
    primary_region: string
    primary_az: string
    gpu_sku: string
    gpu_name: string
    spot_price_usd_hr: number
    start_strategy: string
    optimal_start_time: string | null
    reason: string
  }
  fallback: {
    secondary_az: string
    secondary_sku: string
    fallback_reason: string
  }
  checkpointing: {
    recommended_interval_min: number
    storage_target: string
    estimated_checkpoint_size_gb: number
    reason: string
  }
  savings: {
    spot_cost_total_usd: number
    ondemand_cost_total_usd: number
    savings_usd: number
    savings_eur: number
    savings_pct: number
    time_shift_extra_savings_usd: number
  }
  green_impact: {
    carbon_intensity_gco2_kwh: number
    total_energy_kwh: number
    total_co2_grams: number
    co2_vs_worst_region_grams: number
    co2_saved_grams: number
    equivalent: string
  }
  server_path: {
    step: number
    action: string
    region: string
    az: string
    gpu: string
    time: string
  }[]
  risk_assessment: {
    spot_interruption_probability: string
    eviction_mitigation: string
    max_evictions_per_hour: number
  }
}

export interface CheckpointRequest {
  job_id: string
  current_region: string
  current_az: string
  current_sku: string
  epoch_progress_pct: number
  model_size_gb: number
}

export interface CheckpointEvent {
  job_id: string
  status: string
  checkpoint_saved: boolean
  checkpoint_size_gb: number
  save_duration_sec: number
  from_az: string
  to_az: string
  downtime_ms: number
  epoch_progress_pct: number
  resumed: boolean
  timeline: { time_sec: number; event: string }[]
}

export interface DashboardStats {
  total_jobs_managed: number
  total_savings_usd: number
  total_savings_eur: number
  total_co2_saved_grams: number
  total_checkpoints_saved: number
  total_evictions_handled: number
  avg_savings_pct: number
  uptime_pct: number
  regions_monitored: string[]
  last_updated: string
}

export interface TimeShiftPlan {
  recommended: boolean
  optimal_window_start: string | null
  optimal_window_end: string | null
  reason: string
  estimated_spot_price_usd_hr: number
  current_spot_price_usd_hr: number
  price_reduction_pct: number
  carbon_reduction_pct: number
  meets_deadline: boolean
}

// Live region summary (for dashboard)
export interface RegionSummary {
  region_id: string
  region_name: string
  location: string
  carbon_gco2_kwh: number
  carbon_index: string
  carbon_source: string
  temperature_c: number
  wind_kmh: number
  gpu_count: number
  cheapest_gpu_name: string
  cheapest_spot_price: number
  cheapest_ondemand_price: number
  cheapest_savings_pct: number
  cheapest_sku: string
}

// Live price curve
export interface PriceCurve {
  region_id: string
  gpu_name: string
  sku: string
  data: { hour: string; spot: number; ondemand: number }[]
}

// API calls
export const api = {
  getRegion: (id: string) => request<RegionInfo>(`/region?region_id=${id}`),
  getAZs: (id: string) => request<AZInfo[]>(`/azs?region_id=${id}`),
  simulate: (body: SimulateRequest) =>
    request<SimulateResponse>('/simulate', { method: 'POST', body: JSON.stringify(body) }),
  checkpointSimulate: (body: CheckpointRequest) =>
    request<CheckpointEvent>('/checkpoint/simulate', { method: 'POST', body: JSON.stringify(body) }),
  timeshiftPlan: (body: Record<string, unknown>) =>
    request<TimeShiftPlan>('/timeshifting/plan', { method: 'POST', body: JSON.stringify(body) }),
  dashboardStats: () => request<DashboardStats>('/dashboard/stats'),
  regionsSummary: () => request<RegionSummary[]>('/regions/summary'),
  priceCurve: (regionId: string) => request<PriceCurve>(`/prices/curve?region_id=${regionId}`),
  health: () => request<{ status: string; engine: string }>('/health'),
  llmAnalyze: (question: string) =>
    request<{ question: string; response: Record<string, unknown>; data_source: string }>(
      '/llm/analyze', { method: 'POST', body: JSON.stringify({ question }) }
    ),
}
