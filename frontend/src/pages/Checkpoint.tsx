import { useState } from 'react'
import { api, type CheckpointEvent } from '../lib/api'
import Card from '../components/Card'
import { ShieldCheck, AlertTriangle, CheckCircle, ArrowRight } from 'lucide-react'

export default function Checkpoint() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<CheckpointEvent | null>(null)
  const [animStep, setAnimStep] = useState(-1)

  const handleSimulate = async () => {
    setLoading(true)
    setResult(null)
    setAnimStep(-1)

    try {
      const res = await api.checkpointSimulate({
        job_id: 'fine-tune-llama-7b',
        current_region: 'francecentral',
        current_az: 'fr-central-1',
        current_sku: 'Standard_NC6s_v3',
        epoch_progress_pct: 42.0,
        model_size_gb: 14.0,
      })
      setResult(res)

      // Animate timeline steps
      res.timeline.forEach((_, i) => {
        setTimeout(() => setAnimStep(i), (i + 1) * 600)
      })
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Checkpoint Demo</h1>
        <p className="text-sm text-text-secondary mt-1">
          Simulate a Spot interruption and watch NERVE evacuate the workload
        </p>
      </div>

      {/* Trigger */}
      <Card>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-red-50 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-red-500" />
            </div>
            <div>
              <div className="font-semibold">Spot Interruption Notice</div>
              <div className="text-sm text-text-secondary">
                AWS announces termination in 2 minutes for fr-central-1
              </div>
            </div>
          </div>
          <button
            onClick={handleSimulate}
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2.5 bg-red-500 text-white text-sm font-medium rounded-xl hover:bg-red-600 transition-colors disabled:opacity-50"
          >
            <ShieldCheck className="w-4 h-4" />
            {loading ? 'Simulating...' : 'Trigger Interruption'}
          </button>
        </div>
      </Card>

      {/* Job Context */}
      <Card title="Active Job">
        <div className="grid grid-cols-4 gap-4 text-sm">
          <div>
            <div className="text-text-secondary text-xs">Job ID</div>
            <div className="font-mono font-medium">fine-tune-llama-7b</div>
          </div>
          <div>
            <div className="text-text-secondary text-xs">GPU</div>
            <div className="font-medium">V100 (NC6s_v3)</div>
          </div>
          <div>
            <div className="text-text-secondary text-xs">Progress</div>
            <div className="font-medium">42.0%</div>
          </div>
          <div>
            <div className="text-text-secondary text-xs">Model Size</div>
            <div className="font-medium">14.0 GB</div>
          </div>
        </div>
        <div className="mt-4 h-2 bg-surface-2 rounded-full overflow-hidden">
          <div className="h-full bg-nerve rounded-full transition-all" style={{ width: '42%' }} />
        </div>
      </Card>

      {/* Timeline */}
      {result && (
        <Card title="Evacuation Timeline">
          <div className="space-y-0">
            {result.timeline.map((step, i) => {
              const isVisible = i <= animStep
              const isLast = i === result.timeline.length - 1
              return (
                <div
                  key={i}
                  className={`flex gap-4 transition-all duration-500 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}`}
                >
                  {/* Timeline line */}
                  <div className="flex flex-col items-center">
                    <div className={`w-3 h-3 rounded-full border-2 ${
                      isVisible
                        ? isLast ? 'bg-green-accent border-green-accent' : 'bg-nerve border-nerve'
                        : 'bg-white border-border'
                    }`} />
                    {!isLast && <div className="w-0.5 h-12 bg-border" />}
                  </div>
                  {/* Content */}
                  <div className="pb-6">
                    <div className="flex items-baseline gap-3">
                      <span className="text-xs font-mono text-text-secondary w-12">
                        T+{step.time_sec.toFixed(1)}s
                      </span>
                      <span className="text-sm font-medium">{step.event}</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Result summary */}
          {animStep >= result.timeline.length - 1 && (
            <div className="mt-4 p-4 bg-green-50 rounded-xl border border-green-200 animate-slide-up">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-green-accent" />
                <div>
                  <div className="font-semibold text-green-800">Migration Complete</div>
                  <div className="text-sm text-green-700 mt-1">
                    {result.from_az}
                    <ArrowRight className="w-3 h-3 inline mx-1" />
                    {result.to_az}
                    {' — '}Checkpoint {result.checkpoint_size_gb} GB saved in {result.save_duration_sec.toFixed(1)}s
                    {' — '}<strong>0ms downtime</strong>
                  </div>
                </div>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
