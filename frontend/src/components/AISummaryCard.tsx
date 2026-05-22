import { Sparkles, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import StreamingText from './StreamingText'

interface AIInsight {
  tone: 'positive' | 'warning' | 'danger' | 'neutral'
  icon?: string
  title: string
  body: string
}

interface Props {
  insights: AIInsight[]
  title?: string
  /** Show "Regenerate" button. */
  onRegenerate?: () => void
  isRegenerating?: boolean
}

const toneStyles: Record<AIInsight['tone'], { dot: string; ring: string; title: string; body: string }> = {
  positive: { dot: 'bg-emerald-500', ring: 'ring-emerald-100', title: 'text-emerald-700', body: 'text-emerald-700/80' },
  warning: { dot: 'bg-amber-500', ring: 'ring-amber-100', title: 'text-amber-700', body: 'text-amber-700/80' },
  danger: { dot: 'bg-red-500', ring: 'ring-red-100', title: 'text-red-700', body: 'text-red-700/80' },
  neutral: { dot: 'bg-brand-500', ring: 'ring-brand-100', title: 'text-brand-700', body: 'text-brand-700/80' },
}

export default function AISummaryCard({
  insights,
  title = 'AI Insights',
  onRegenerate,
  isRegenerating,
}: Props) {
  const [streamKey, setStreamKey] = useState(0)
  const handleRegen = () => {
    setStreamKey((k) => k + 1)
    onRegenerate?.()
  }
  return (
    <div className="relative rounded-2xl ai-surface shadow-soft-2 overflow-hidden">
      <div className="absolute inset-0 bg-grid-fade opacity-60 pointer-events-none" />
      <div className="relative p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="relative">
              <Sparkles className="text-ai-600" size={18} />
              <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-ai-cyan animate-pulse" />
            </span>
            <h3 className="text-sm font-bold ai-text-gradient uppercase tracking-wider">{title}</h3>
            <span className="text-2xs text-slate-500 hidden sm:inline">· Powered by GPT-4.1 mini + WCO/OFAC corpus</span>
          </div>
          {onRegenerate && (
            <button
              onClick={handleRegen}
              className="text-2xs text-ai-700 hover:text-ai-800 font-medium inline-flex items-center gap-1"
              disabled={isRegenerating}
            >
              <RefreshCw size={11} className={isRegenerating ? 'animate-spin' : ''} />
              {isRegenerating ? 'Thinking…' : 'Regenerate'}
            </button>
          )}
        </div>
        {insights.length === 0 ? (
          <p className="text-sm text-slate-500">No insights to surface yet — once you run more compliance checks, AI will surface trends here.</p>
        ) : (
          <div className="space-y-3">
            {insights.map((ins, i) => {
              const t = toneStyles[ins.tone]
              return (
                <div
                  key={`${streamKey}-${i}`}
                  className="bg-white/80 backdrop-blur rounded-xl p-3 ring-1 ring-slate-200/70 animate-fade-in"
                  style={{ animationDelay: `${i * 90}ms` }}
                >
                  <div className="flex items-start gap-3">
                    <span className={`mt-1.5 w-2 h-2 rounded-full ${t.dot} animate-pulse`} />
                    <div className="min-w-0 flex-1">
                      <p className={`text-sm font-semibold ${t.title}`}>{ins.title}</p>
                      <p className={`text-xs mt-0.5 leading-relaxed text-slate-600`}>
                        <StreamingText text={ins.body} cps={120} cursor={false} />
                      </p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
