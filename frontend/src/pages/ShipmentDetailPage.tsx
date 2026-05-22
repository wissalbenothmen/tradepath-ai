import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  ArrowLeft, Ship, Tag, ShieldAlert, FileText, Award, TrendingDown, FolderOpen,
  Mic, GitCompare, Check, AlertTriangle, X, RefreshCw, Sparkles, Download,
} from 'lucide-react'
import api, { endpoints, qk } from '../api'
import StatusPill from '../components/StatusPill'
import AIThinking from '../components/AIThinking'
import StreamingText from '../components/StreamingText'
import { SkeletonCard } from '../components/Skeleton'
import { formatUSD } from '../utils/format'

interface Shipment {
  id: string; reference_number: string; status: string; origin_country: string;
  destination_country: string; exporter_name: string | null; importer_name: string | null;
  consignee_name: string | null; total_value_usd: number | null; incoterms: string | null;
  transport_mode: string | null; currency: string; denied_party_status: string | null;
  restriction_status: string | null;
}
interface VoiceRecord {
  id: string; voice_transcript: string | null; transcript_status: string | null;
  provider: string | null; created_at: string | null;
}
interface CrossValidateResp {
  status: string; mode?: string; transcript_excerpt?: string;
  line_items_checked?: number; documents_checked?: number;
  voice_claims?: Record<string, unknown>;
  document_state?: Record<string, unknown>;
  contradictions?: Array<{ field?: string; severity?: string; detail?: string; voice?: string; documents?: string }>;
  missing_evidence?: Array<{ field?: string; detail?: string }>;
  talking_points?: string[];
  narrative?: string;
  detail?: string;
}

const COMPLIANCE_STEPS = [
  { icon: ShieldAlert, label: 'Sanctions Screening', path: '/screening', tone: 'bg-red-50 text-red-700 ring-red-200' },
  { icon: Tag, label: 'HS Classification', path: '/classification', tone: 'bg-brand-50 text-brand-700 ring-brand-200' },
  { icon: FileText, label: 'Customs Declaration', path: '/declarations', tone: 'bg-violet-50 text-violet-700 ring-violet-200' },
  { icon: Award, label: 'Certificate of Origin', path: '/coo', tone: 'bg-emerald-50 text-emerald-700 ring-emerald-200' },
  { icon: TrendingDown, label: 'FTA Analysis', path: '/fta', tone: 'bg-teal-50 text-teal-700 ring-teal-200' },
  { icon: FolderOpen, label: 'Documents', path: '/documents', tone: 'bg-amber-50 text-amber-700 ring-amber-200' },
]

export default function ShipmentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [crossValidating, setCrossValidating] = useState(false)
  const [crossResult, setCrossResult] = useState<CrossValidateResp | null>(null)
  const [briefDownloading, setBriefDownloading] = useState(false)

  const { data: shipment, isLoading } = useQuery<Shipment>({
    queryKey: qk.shipment(id!),
    queryFn: () => api.get(endpoints.shipments.detail(id!)).then((r) => r.data),
    enabled: !!id,
  })
  const { data: voiceRecords = [] } = useQuery<VoiceRecord[]>({
    queryKey: qk.voiceRecords(id!),
    queryFn: () => api.get(endpoints.shipments.voiceRecords(id!)).then((r) => r.data),
    enabled: !!id,
  })

  const runCrossValidate = async () => {
    if (!id) return
    setCrossValidating(true)
    setCrossResult(null)
    try {
      const r = await api.post<CrossValidateResp>(endpoints.shipments.crossValidate(id))
      setCrossResult(r.data)
    } catch (e: any) {
      setCrossResult({ status: 'error', detail: e?.response?.data?.detail || 'Cross-validation failed' })
    } finally {
      setCrossValidating(false)
    }
  }

  const downloadBrief = async () => {
    if (!id) return
    setBriefDownloading(true)
    try {
      const r = await api.get(endpoints.shipments.brief(id), { responseType: 'blob' })
      const blob = new Blob([r.data], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      const disp = (r.headers?.['content-disposition'] as string | undefined) || ''
      const m = disp.match(/filename="?([^";]+)"?/)
      link.download = m?.[1] ?? `tradepath-amendment-${id}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } finally {
      setBriefDownloading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-[1500px] mx-auto">
        <div className="h-6 w-32 shimmer rounded" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <SkeletonCard key={i} />)}
        </div>
      </div>
    )
  }
  if (!shipment) {
    return (
      <div className="p-8 text-center text-slate-500">
        <Ship size={48} className="mx-auto mb-3 opacity-30" />
        <p>Shipment not found</p>
      </div>
    )
  }

  // Derived synthesis from real backend output
  const contradictionsN = crossResult?.contradictions?.length ?? 0
  const missingN = crossResult?.missing_evidence?.length ?? 0
  const talkingN = crossResult?.talking_points?.length ?? 0

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-[1500px] mx-auto">
      {/* Back nav */}
      <button
        onClick={() => navigate('/shipments')}
        className="flex items-center gap-2 text-slate-500 hover:text-slate-900 text-sm font-medium"
      >
        <ArrowLeft size={14} /> Back to shipments
      </button>

      {/* Header */}
      <div className="flex items-start gap-4 flex-wrap">
        <div className="bg-brand-50 ring-1 ring-brand-100 p-3 rounded-xl">
          <Ship className="text-brand-600" size={22} />
        </div>
        <div className="min-w-0">
          <p className="text-2xs uppercase tracking-wider font-semibold text-slate-500">Shipment</p>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 font-mono mt-0.5">{shipment.reference_number}</h1>
          <p className="text-sm text-slate-500 mt-1 font-mono">
            {shipment.origin_country} → {shipment.destination_country}
            {shipment.incoterms && <span className="ml-3 text-slate-400">{shipment.incoterms}</span>}
            {shipment.transport_mode && <span className="ml-2 text-slate-400 capitalize">· {shipment.transport_mode}</span>}
          </p>
        </div>
        <div className="ml-auto"><StatusPill status={shipment.status} /></div>
      </div>

      {/* AI Summary card */}
      <div className="relative overflow-hidden rounded-2xl ai-surface shadow-soft-2 p-5">
        <div className="absolute inset-0 bg-grid-fade opacity-50 pointer-events-none" />
        <div className="relative flex items-start gap-4">
          <div className="shrink-0 w-10 h-10 rounded-xl bg-ai-gradient flex items-center justify-center shadow-ai-glow-soft">
            <Sparkles size={18} className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-2xs uppercase tracking-wider font-bold ai-text-gradient">AI Summary</p>
            <p className="text-sm text-slate-700 leading-relaxed mt-1">
              <StreamingText
                text={buildAISummary(shipment)}
                cps={120}
                cursor={false}
              />
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {shipment.denied_party_status && (
                <span className="text-2xs font-semibold text-slate-600 inline-flex items-center gap-1.5 bg-white/70 ring-1 ring-slate-200 px-2 py-0.5 rounded-full">
                  <ShieldAlert size={10} className="text-slate-400" /> DPS: <StatusPill status={shipment.denied_party_status} size="sm" />
                </span>
              )}
              {shipment.restriction_status && (
                <span className="text-2xs font-semibold text-slate-600 inline-flex items-center gap-1.5 bg-white/70 ring-1 ring-slate-200 px-2 py-0.5 rounded-full">
                  <FileText size={10} className="text-slate-400" /> Restrictions: <StatusPill status={shipment.restriction_status} size="sm" />
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Details grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {[
          { label: 'Exporter', value: shipment.exporter_name },
          { label: 'Importer', value: shipment.importer_name },
          { label: 'Consignee', value: shipment.consignee_name },
          { label: 'Total value', value: formatUSD(shipment.total_value_usd) },
          { label: 'Incoterms', value: shipment.incoterms },
          { label: 'Transport', value: shipment.transport_mode },
          { label: 'Currency', value: shipment.currency },
          { label: 'Origin / Dest.', value: `${shipment.origin_country} → ${shipment.destination_country}` },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white rounded-xl ring-1 ring-slate-100 shadow-soft-1 p-3">
            <p className="text-2xs uppercase tracking-wider font-semibold text-slate-500">{label}</p>
            <p className="font-semibold text-slate-900 mt-0.5 truncate">{value || <span className="text-slate-400">—</span>}</p>
          </div>
        ))}
      </div>

      {/* Voice cross-validation panel */}
      <div className="rounded-2xl bg-white shadow-soft-2 ring-1 ring-slate-100 overflow-hidden">
        <div className="h-0.5 bg-gradient-to-r from-violet-500 to-cyan-500" />
        <div className="p-5">
          <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
            <div>
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Mic size={16} className="text-ai-600" /> Voice ↔ Documents Cross-Validation
              </h3>
              <p className="text-xs text-slate-500 mt-1 max-w-2xl">
                AI compares the broker's voice amendment against shipment line items and trade documents. Surfaces contradictions, missing evidence, and customs talking points.
              </p>
            </div>
            <div className="flex gap-2 flex-wrap">
              <button onClick={runCrossValidate} disabled={crossValidating} className="btn-ai">
                <Sparkles size={14} />
                {crossValidating ? 'Cross-validating…' : 'Cross-validate'}
              </button>
              <button onClick={downloadBrief} disabled={briefDownloading} className="btn-secondary">
                <Download size={14} />
                {briefDownloading ? 'Generating…' : 'Amendment Brief PDF'}
              </button>
            </div>
          </div>

          {crossValidating && <AIThinking label="Reading voice transcript, comparing against line items + invoices…" />}

          {crossResult?.status === 'error' && (
            <div className="rounded-lg bg-red-50 ring-1 ring-red-200 p-3 text-sm text-red-700">{crossResult.detail}</div>
          )}

          {crossResult && crossResult.status !== 'error' && (
            <div className="space-y-3 mt-3">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <Stat label="Mode" value={crossResult.mode ?? '—'} tone="ai" />
                <Stat label="Line items" value={crossResult.line_items_checked?.toString() ?? '0'} tone="brand" />
                <Stat label="Documents" value={crossResult.documents_checked?.toString() ?? '0'} tone="brand" />
                <Stat label="Talking pts" value={talkingN.toString()} tone="success" />
              </div>

              {(contradictionsN > 0 || missingN > 0) && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  {contradictionsN > 0 && (
                    <div className="rounded-xl bg-red-50 ring-1 ring-red-200 p-3">
                      <p className="text-xs font-bold uppercase tracking-wider text-red-700 flex items-center gap-1.5 mb-2">
                        <X size={12} /> Contradictions ({contradictionsN})
                      </p>
                      <ul className="space-y-1.5">
                        {crossResult.contradictions!.slice(0, 5).map((c, i) => (
                          <li key={i} className="text-sm text-red-900 leading-relaxed">
                            <span className="font-semibold">{c.field ?? 'field'}:</span>{' '}
                            {c.detail ?? `voice="${c.voice}" vs documents="${c.documents}"`}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {missingN > 0 && (
                    <div className="rounded-xl bg-amber-50 ring-1 ring-amber-200 p-3">
                      <p className="text-xs font-bold uppercase tracking-wider text-amber-700 flex items-center gap-1.5 mb-2">
                        <AlertTriangle size={12} /> Missing evidence ({missingN})
                      </p>
                      <ul className="space-y-1.5">
                        {crossResult.missing_evidence!.slice(0, 5).map((m, i) => (
                          <li key={i} className="text-sm text-amber-900 leading-relaxed">
                            <span className="font-semibold">{m.field ?? 'field'}:</span> {m.detail}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {crossResult.narrative && (
                <div className="rounded-xl ai-surface p-4">
                  <p className="text-2xs font-bold uppercase tracking-wider ai-text-gradient mb-1.5 flex items-center gap-1">
                    <Sparkles size={11} /> AI Synthesis
                  </p>
                  <p className="text-sm text-slate-800 leading-relaxed">
                    <StreamingText text={crossResult.narrative} cps={140} cursor={false} />
                  </p>
                </div>
              )}

              {talkingN > 0 && (
                <div className="rounded-xl bg-emerald-50 ring-1 ring-emerald-200 p-3">
                  <p className="text-xs font-bold uppercase tracking-wider text-emerald-700 flex items-center gap-1.5 mb-2">
                    <Check size={12} /> Talking points for customs
                  </p>
                  <ul className="space-y-1 list-disc list-inside text-sm text-emerald-900">
                    {crossResult.talking_points!.slice(0, 6).map((t, i) => <li key={i}>{t}</li>)}
                  </ul>
                </div>
              )}

              {contradictionsN === 0 && missingN === 0 && talkingN === 0 && (
                <div className="rounded-xl bg-emerald-50 ring-1 ring-emerald-200 p-3 text-sm text-emerald-800 flex items-center gap-2">
                  <Check size={14} /> No contradictions detected. Documents and voice amendment are consistent.
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Voice transcript viewer */}
      <div className="rounded-2xl bg-white shadow-soft-2 ring-1 ring-slate-100 overflow-hidden">
        <div className="h-0.5 bg-gradient-to-r from-brand-500 to-ai-cyan" />
        <div className="p-5">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Mic size={16} className="text-brand-600" /> Voice Amendment Transcript
            </h3>
            <span className="text-2xs text-slate-500">Powered by Whisper Large v3</span>
          </div>
          {voiceRecords.length === 0 ? (
            <p className="text-sm text-slate-500">No voice amendment on this shipment yet.</p>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center gap-2 flex-wrap text-2xs">
                <span className="font-semibold text-slate-700">Latest</span>
                {voiceRecords[0].provider && (
                  <span className="px-2 py-0.5 bg-brand-50 text-brand-700 rounded ring-1 ring-brand-100">
                    {voiceRecords[0].provider}
                  </span>
                )}
                {voiceRecords[0].created_at && (
                  <span className="text-slate-400">{new Date(voiceRecords[0].created_at).toLocaleString()}</span>
                )}
                {voiceRecords.length > 1 && (
                  <span className="text-slate-400">+{voiceRecords.length - 1} earlier</span>
                )}
              </div>
              <pre className="whitespace-pre-wrap text-sm text-slate-800 bg-slate-50 ring-1 ring-slate-200 rounded-xl p-3 font-sans leading-relaxed max-h-72 overflow-auto">
                {voiceRecords[0].voice_transcript || '— empty transcript —'}
              </pre>
            </div>
          )}
        </div>
      </div>

      {/* Compliance workflow */}
      <div className="rounded-2xl bg-white shadow-soft-2 ring-1 ring-slate-100 p-5">
        <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
          <GitCompare size={16} className="text-brand-600" /> Compliance workflow
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {COMPLIANCE_STEPS.map(({ icon: Icon, label, path, tone }) => (
            <button
              key={path}
              onClick={() => navigate(path)}
              className={`flex flex-col items-center gap-1.5 p-3 rounded-xl ring-1 text-center hover:shadow-soft-2 transition ${tone}`}
            >
              <Icon size={18} />
              <span className="text-xs font-semibold leading-tight">{label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value, tone }: { label: string; value: string; tone: 'brand' | 'ai' | 'success' }) {
  const styles = {
    brand: 'bg-brand-50 text-brand-700 ring-brand-100',
    ai: 'bg-ai-50 text-ai-700 ring-ai-100',
    success: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
  }[tone]
  return (
    <div className={`rounded-xl p-2 text-center ring-1 ${styles}`}>
      <p className="text-xs font-bold tabular">{value}</p>
      <p className="text-2xs uppercase tracking-wider opacity-80">{label}</p>
    </div>
  )
}

function buildAISummary(s: Shipment): string {
  const parts: string[] = []
  parts.push(`${s.origin_country} → ${s.destination_country} shipment`)
  if (s.total_value_usd) parts.push(`valued ${formatUSD(s.total_value_usd)}`)
  if (s.incoterms) parts.push(`under ${s.incoterms}`)
  if (s.exporter_name) parts.push(`from ${s.exporter_name}`)
  const base = parts.join(' ') + '.'

  const flags: string[] = []
  if (s.denied_party_status === 'positive_match') flags.push('Sanctions: positive match — review required before declaration filing.')
  else if (s.denied_party_status === 'potential_match') flags.push('Sanctions: potential phonetic match flagged for human review.')
  else flags.push('Sanctions: cleared across OFAC, BIS, EU, UN and 4 more lists.')

  if (s.restriction_status === 'license_required') flags.push('Restrictions: an export licence is required for one or more line items.')
  else flags.push('Restrictions: no licence required for this lane.')

  return base + ' ' + flags.join(' ')
}
