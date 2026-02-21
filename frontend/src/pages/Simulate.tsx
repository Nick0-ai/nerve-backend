import { useState } from 'react'
import { api, type SimulateResponse } from '../lib/api'
import Card from '../components/Card'
import { Play, Server, DollarSign, Leaf, ShieldCheck, ArrowRight } from 'lucide-react'

export default function Simulate() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SimulateResponse | null>(null)

  const [form, setForm] = useState({
    model_name: 'LLaMA-7B',
    estimated_gpu_hours: 24,
    min_gpu_memory_gb: 16,
    deadline_hours: 12,
  })

  const handleSubmit = async () => {
    setLoading(true)
    try {
      const deadline = new Date(Date.now() + form.deadline_hours * 3600_000).toISOString()
      const res = await api.simulate({
        job_type: 'llm_fine_tuning',
        model_name: form.model_name,
        estimated_gpu_hours: form.estimated_gpu_hours,
        deadline,
        min_gpu_memory_gb: form.min_gpu_memory_gb,
        framework: 'pytorch',
        checkpoint_interval_min: 30,
      })
      setResult(res)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Simulate Job</h1>
        <p className="text-sm text-text-secondary mt-1">
          Submit a compute job and let NERVE find the optimal placement
        </p>
      </div>

      {/* Form */}
      <Card title="Job Configuration">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1.5">Model Name</label>
            <input
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-surface text-sm focus:outline-none focus:ring-2 focus:ring-nerve/30 focus:border-nerve"
              value={form.model_name}
              onChange={(e) => setForm({ ...form, model_name: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1.5">GPU Hours Needed</label>
            <input
              type="number"
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-surface text-sm focus:outline-none focus:ring-2 focus:ring-nerve/30 focus:border-nerve"
              value={form.estimated_gpu_hours}
              onChange={(e) => setForm({ ...form, estimated_gpu_hours: +e.target.value })}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1.5">Min GPU Memory (GB)</label>
            <input
              type="number"
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-surface text-sm focus:outline-none focus:ring-2 focus:ring-nerve/30 focus:border-nerve"
              value={form.min_gpu_memory_gb}
              onChange={(e) => setForm({ ...form, min_gpu_memory_gb: +e.target.value })}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1.5">Deadline (hours from now)</label>
            <input
              type="number"
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-surface text-sm focus:outline-none focus:ring-2 focus:ring-nerve/30 focus:border-nerve"
              value={form.deadline_hours}
              onChange={(e) => setForm({ ...form, deadline_hours: +e.target.value })}
            />
          </div>
        </div>
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="mt-6 flex items-center gap-2 px-6 py-2.5 bg-nerve text-white text-sm font-medium rounded-xl hover:bg-nerve-dark transition-colors disabled:opacity-50"
        >
          <Play className="w-4 h-4" />
          {loading ? 'Computing...' : 'Run Simulation'}
        </button>
      </Card>

      {/* Results */}
      {result && (
        <>
          {/* Decision */}
          <Card title="NERVE Decision" className="border-nerve/30">
            <div className="flex items-start gap-6">
              <div className="w-12 h-12 rounded-2xl bg-nerve/10 flex items-center justify-center shrink-0">
                <Server className="w-6 h-6 text-nerve" />
              </div>
              <div className="flex-1 space-y-3">
                <div className="flex items-baseline gap-3">
                  <span className="text-lg font-bold">{result.decision.gpu_name}</span>
                  <span className="text-xs font-mono text-text-secondary">{result.decision.gpu_sku}</span>
                </div>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-text-secondary text-xs">Region</span>
                    <div className="font-medium">{result.decision.primary_region}</div>
                  </div>
                  <div>
                    <span className="text-text-secondary text-xs">AZ</span>
                    <div className="font-medium">{result.decision.primary_az}</div>
                  </div>
                  <div>
                    <span className="text-text-secondary text-xs">Strategy</span>
                    <div className="font-medium capitalize">{result.decision.start_strategy.replace('_', ' ')}</div>
                  </div>
                </div>
                <p className="text-sm text-text-secondary">{result.decision.reason}</p>
              </div>
            </div>
          </Card>

          {/* Savings + Green */}
          <div className="grid grid-cols-2 gap-4">
            <Card title="Savings">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <DollarSign className="w-4 h-4 text-nerve" />
                    <span className="text-sm">Spot cost</span>
                  </div>
                  <span className="font-mono font-bold">${result.savings.spot_cost_total_usd}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <DollarSign className="w-4 h-4 text-red-400" />
                    <span className="text-sm">On-Demand cost</span>
                  </div>
                  <span className="font-mono text-text-secondary line-through">${result.savings.ondemand_cost_total_usd}</span>
                </div>
                <div className="border-t border-border pt-3 flex items-center justify-between">
                  <span className="text-sm font-semibold">You save</span>
                  <div className="text-right">
                    <div className="text-xl font-bold text-nerve">{result.savings.savings_eur} EUR</div>
                    <div className="text-xs text-text-secondary">{result.savings.savings_pct}% reduction</div>
                  </div>
                </div>
              </div>
            </Card>

            <Card title="Green Impact">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Leaf className="w-4 h-4 text-green-accent" />
                    <span className="text-sm">Carbon intensity</span>
                  </div>
                  <span className="font-mono">{result.green_impact.carbon_intensity_gco2_kwh} gCO2/kWh</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Total energy</span>
                  <span className="font-mono">{result.green_impact.total_energy_kwh} kWh</span>
                </div>
                <div className="border-t border-border pt-3 flex items-center justify-between">
                  <span className="text-sm font-semibold">CO2 saved</span>
                  <div className="text-right">
                    <div className="text-xl font-bold text-green-accent">{(result.green_impact.co2_saved_grams / 1000).toFixed(1)} kg</div>
                    <div className="text-xs text-text-secondary">{result.green_impact.equivalent}</div>
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* Server Path */}
          <Card title="Server Path">
            <div className="space-y-4">
              {result.server_path.map((step, i) => (
                <div key={step.step} className="flex items-center gap-4">
                  <div className="w-8 h-8 rounded-full bg-nerve/10 flex items-center justify-center text-xs font-bold text-nerve shrink-0">
                    {step.step}
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">{step.action}</div>
                    <div className="text-xs text-text-secondary font-mono">
                      {step.region} / {step.az} / {step.gpu}
                    </div>
                  </div>
                  <div className="text-xs text-text-secondary font-mono">
                    {new Date(step.time).toLocaleTimeString()}
                  </div>
                  {i < result.server_path.length - 1 && (
                    <ArrowRight className="w-4 h-4 text-text-secondary/30" />
                  )}
                </div>
              ))}
            </div>
          </Card>

          {/* Risk + Checkpoint */}
          <div className="grid grid-cols-2 gap-4">
            <Card title="Risk Assessment">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-text-secondary">Interruption risk</span>
                  <span className="font-medium capitalize">{result.risk_assessment.spot_interruption_probability}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Mitigation</span>
                  <span className="font-medium text-right max-w-[200px]">{result.risk_assessment.eviction_mitigation}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Max evictions/h</span>
                  <span className="font-medium">{result.risk_assessment.max_evictions_per_hour}</span>
                </div>
              </div>
            </Card>

            <Card title="Checkpointing">
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2 mb-3">
                  <ShieldCheck className="w-5 h-5 text-amber-600" />
                  <span className="font-semibold">Every {result.checkpointing.recommended_interval_min} min</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Storage</span>
                  <span className="font-mono uppercase">{result.checkpointing.storage_target}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Checkpoint size</span>
                  <span className="font-mono">{result.checkpointing.estimated_checkpoint_size_gb} GB</span>
                </div>
                <p className="text-xs text-text-secondary mt-2">{result.checkpointing.reason}</p>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
