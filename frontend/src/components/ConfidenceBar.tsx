interface Props {
  /** 0–1 (or 0–100 if percent=true). */
  value: number
  percent?: boolean
  size?: 'sm' | 'md'
  showLabel?: boolean
}

/** Confidence/quality bar with semantic colors and tabular numerals. */
export default function ConfidenceBar({ value, percent = false, size = 'md', showLabel = true }: Props) {
  const pct = Math.max(0, Math.min(100, percent ? value : value * 100))
  const tone =
    pct >= 90 ? { bar: 'bg-emerald-500', text: 'text-emerald-700' }
    : pct >= 75 ? { bar: 'bg-brand-500', text: 'text-brand-700' }
    : pct >= 60 ? { bar: 'bg-amber-500', text: 'text-amber-700' }
    : { bar: 'bg-red-500', text: 'text-red-700' }
  const h = size === 'sm' ? 'h-1.5' : 'h-2'
  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <div className={`flex-1 bg-slate-100 rounded-full ${h} overflow-hidden`}>
        <div
          className={`${tone.bar} ${h} rounded-full transition-[width] duration-700 ease-out`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <span className={`text-xs font-semibold tabular w-9 text-right ${tone.text}`}>
          {pct.toFixed(0)}%
        </span>
      )}
    </div>
  )
}
