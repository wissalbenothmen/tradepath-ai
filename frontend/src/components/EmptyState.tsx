import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

interface Props {
  icon: LucideIcon
  title: string
  description?: string
  action?: ReactNode
  /** Pull illustration tone. */
  tone?: 'brand' | 'ai' | 'neutral'
}

export default function EmptyState({ icon: Icon, title, description, action, tone = 'neutral' }: Props) {
  const chipBg = tone === 'ai'
    ? 'bg-gradient-to-br from-ai-100 to-cyan-50 text-ai-600'
    : tone === 'brand'
    ? 'bg-brand-50 text-brand-600'
    : 'bg-slate-100 text-slate-500'
  return (
    <div className="bg-white rounded-2xl shadow-soft-1 ring-1 ring-slate-100 py-12 px-6 text-center">
      <div className={`mx-auto w-14 h-14 rounded-2xl flex items-center justify-center ${chipBg}`}>
        <Icon size={26} />
      </div>
      <h3 className="mt-4 text-base font-semibold text-slate-900">{title}</h3>
      {description && <p className="mt-1 text-sm text-slate-500 max-w-md mx-auto">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
