import {
  CheckCircle2, Clock, Loader2, AlertTriangle, Ban, FileText, Truck, Sparkles,
  type LucideIcon,
} from 'lucide-react'

type Tone = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'ai'

interface Props {
  status: string
  /** Override the visual size. */
  size?: 'sm' | 'md'
}

// Map a status string → (icon, label, tone). Centralised so every page agrees.
const STATUS_MAP: Record<string, { icon: LucideIcon; label?: string; tone: Tone }> = {
  draft: { icon: FileText, tone: 'neutral' },
  screening: { icon: Sparkles, tone: 'ai' },
  classification: { icon: Sparkles, tone: 'ai' },
  declaration_ready: { icon: Loader2, label: 'Ready', tone: 'info' },
  filed: { icon: Truck, tone: 'info' },
  cleared: { icon: CheckCircle2, tone: 'success' },
  hold: { icon: Clock, label: 'On hold', tone: 'warning' },
  blocked: { icon: Ban, tone: 'danger' },
  clear: { icon: CheckCircle2, tone: 'success' },
  potential_match: { icon: AlertTriangle, label: 'Potential', tone: 'warning' },
  positive_match: { icon: Ban, label: 'Match', tone: 'danger' },
  pending: { icon: Clock, tone: 'neutral' },
  classified: { icon: Sparkles, tone: 'ai' },
  confirmed: { icon: CheckCircle2, tone: 'success' },
  disputed: { icon: AlertTriangle, tone: 'warning' },
  escalated: { icon: Ban, tone: 'danger' },
  submitted: { icon: Truck, tone: 'info' },
  accepted: { icon: CheckCircle2, tone: 'success' },
  rejected: { icon: Ban, tone: 'danger' },
  review: { icon: AlertTriangle, label: 'Review', tone: 'warning' },
}

const TONE_STYLES: Record<Tone, string> = {
  success: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  warning: 'bg-amber-50 text-amber-700 ring-amber-200',
  danger: 'bg-red-50 text-red-700 ring-red-200',
  info: 'bg-brand-50 text-brand-700 ring-brand-200',
  neutral: 'bg-slate-100 text-slate-700 ring-slate-200',
  ai: 'bg-ai-50 text-ai-700 ring-ai-100',
}

function titleCase(s: string): string {
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function StatusPill({ status, size = 'md' }: Props) {
  const key = (status || '').toLowerCase()
  const def = STATUS_MAP[key] ?? { icon: FileText, tone: 'neutral' as Tone }
  const Icon = def.icon
  const cls = TONE_STYLES[def.tone]
  const pad = size === 'sm' ? 'px-2 py-0.5 text-2xs' : 'px-2.5 py-1 text-xs'
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full ring-1 font-semibold ${cls} ${pad}`}>
      <Icon size={size === 'sm' ? 10 : 12} className={key === 'declaration_ready' ? 'animate-spin-slow' : ''} />
      {def.label ?? titleCase(status)}
    </span>
  )
}

export { STATUS_MAP, TONE_STYLES }
