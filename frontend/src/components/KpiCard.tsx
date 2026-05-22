import type { ReactNode } from 'react'
import Sparkline from './Sparkline'

interface Props {
  label: string
  value: string | number
  /** Optional small suffix after the number (e.g. "%", "USD"). */
  suffix?: string
  icon?: ReactNode
  /** Background tint of the icon chip. */
  tone?: 'brand' | 'success' | 'danger' | 'warning' | 'ai' | 'neutral'
  /** Optional delta line (e.g. "+12% vs prev 30d"). */
  delta?: { value: string; positive?: boolean }
  /** Optional sparkline series. */
  spark?: number[]
  /** Optional click-through. */
  onClick?: () => void
}

const toneStyles: Record<NonNullable<Props['tone']>, { chip: string; ring: string }> = {
  brand: { chip: 'bg-brand-50 text-brand-600', ring: 'ring-brand-100' },
  success: { chip: 'bg-emerald-50 text-emerald-600', ring: 'ring-emerald-100' },
  danger: { chip: 'bg-red-50 text-red-600', ring: 'ring-red-100' },
  warning: { chip: 'bg-amber-50 text-amber-600', ring: 'ring-amber-100' },
  ai: { chip: 'bg-ai-50 text-ai-600', ring: 'ring-ai-100' },
  neutral: { chip: 'bg-slate-100 text-slate-600', ring: 'ring-slate-100' },
}

export default function KpiCard({
  label,
  value,
  suffix,
  icon,
  tone = 'brand',
  delta,
  spark,
  onClick,
}: Props) {
  const s = toneStyles[tone]
  const Container: any = onClick ? 'button' : 'div'
  return (
    <Container
      onClick={onClick}
      className={`group bg-white rounded-2xl shadow-soft-1 hover:shadow-soft-3 transition-shadow p-5 text-left w-full ring-1 ring-slate-100 ${onClick ? 'cursor-pointer' : ''}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-2xs uppercase tracking-wider font-semibold text-slate-500">{label}</p>
          <p className="mt-1 text-2xl sm:text-3xl font-bold text-slate-900 tabular">
            {value}
            {suffix ? <span className="text-base ml-1 font-semibold text-slate-500">{suffix}</span> : null}
          </p>
          {delta && (
            <p className={`mt-1 text-xs font-medium tabular ${delta.positive ? 'text-emerald-600' : 'text-red-600'}`}>
              {delta.positive ? '▲' : '▼'} {delta.value}
            </p>
          )}
        </div>
        {icon && (
          <div className={`p-2.5 rounded-xl ${s.chip}`}>{icon}</div>
        )}
      </div>
      {spark && spark.length > 1 && (
        <div className="mt-3">
          <Sparkline values={spark} tone={tone === 'warning' || tone === 'neutral' ? 'brand' : tone} />
        </div>
      )}
    </Container>
  )
}
