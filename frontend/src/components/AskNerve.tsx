import { useState } from 'react'
import { api } from '../lib/api'
import { BrainCircuit, Send, Loader2 } from 'lucide-react'

export default function AskNerve() {
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const suggestions = [
    'Quel est le meilleur moment pour lancer un job de 24h GPU ?',
    'Compare les 3 regions en termes de cout et carbone.',
    'Recommande une strategie pour fine-tuner LLaMA-7B avec un budget de $50.',
  ]

  async function handleAsk(q: string) {
    const query = q || question
    if (!query.trim()) return

    setLoading(true)
    setError(null)
    setResponse(null)

    try {
      const result = await api.llmAnalyze(query)
      setResponse(result.response)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'LLM request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Input */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <BrainCircuit className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-nerve" />
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAsk(question)}
            placeholder="Ask NERVE AI about your infrastructure..."
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-nerve/20 focus:border-nerve"
          />
        </div>
        <button
          onClick={() => handleAsk(question)}
          disabled={loading || !question.trim()}
          className="px-4 py-2.5 bg-nerve text-white rounded-xl text-sm font-medium hover:bg-nerve/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          Ask
        </button>
      </div>

      {/* Suggestions */}
      {!response && !loading && (
        <div className="flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => { setQuestion(s); handleAsk(s); }}
              className="text-xs px-3 py-1.5 bg-surface-2 border border-border rounded-full text-text-secondary hover:bg-nerve/10 hover:text-nerve hover:border-nerve/30 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center gap-3 p-4 bg-nerve/5 border border-nerve/20 rounded-xl">
          <Loader2 className="w-5 h-5 text-nerve animate-spin" />
          <span className="text-sm text-nerve font-medium">NERVE AI is analyzing live data...</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          {error}
          <span className="block text-xs mt-1 text-red-500">Set NERVE_LLM_PROVIDER and API key in backend/.env</span>
        </div>
      )}

      {/* Response */}
      {response && (
        <div className="p-4 bg-white border border-border rounded-xl space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium text-nerve">
            <BrainCircuit className="w-4 h-4" />
            NERVE AI Response
          </div>
          <pre className="text-xs text-text-primary whitespace-pre-wrap font-mono bg-surface-2 rounded-lg p-3 max-h-64 overflow-auto">
            {typeof response === 'string' ? response : JSON.stringify(response, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
