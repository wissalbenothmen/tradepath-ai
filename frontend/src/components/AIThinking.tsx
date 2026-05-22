import { Sparkles } from 'lucide-react'

interface AIThinkingProps {
  label?: string
  /** Variant: 'subtle' for inline, 'card' for full surface */
  variant?: 'subtle' | 'card'
}

export default function AIThinking({ label = 'AI is thinking…', variant = 'card' }: AIThinkingProps) {
  if (variant === 'subtle') {
    return (
      <span className="inline-flex items-center gap-2 text-xs text-ai-700 font-medium">
        <Sparkles size={12} className="text-ai-600 animate-pulse" />
        <span className="ai-text-gradient font-semibold">{label}</span>
        <span className="inline-flex items-center gap-0.5">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1 h-1 rounded-full bg-ai-500 animate-thinking"
              style={{ animationDelay: `${i * 0.16}s` }}
            />
          ))}
        </span>
      </span>
    )
  }
  return (
    <div className="ai-surface rounded-xl p-4 flex items-center gap-3">
      <div className="relative shrink-0">
        <Sparkles className="text-ai-600 animate-pulse" size={20} />
        <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-ai-cyan animate-ping" />
      </div>
      <div className="flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-2 h-2 rounded-full bg-gradient-to-br from-ai-600 to-ai-cyan animate-thinking"
            style={{ animationDelay: `${i * 0.16}s` }}
          />
        ))}
      </div>
      <p className="text-sm font-semibold ai-text-gradient">{label}</p>
    </div>
  )
}
