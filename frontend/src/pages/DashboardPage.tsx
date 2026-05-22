import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import {
  Ship, ShieldAlert, Tag, AlertTriangle, CheckCircle2, Clock, TrendingDown,
  DollarSign, Activity, Sparkles, ArrowRight, ChevronRight, Brain, ShieldCheck,
} from 'lucide-react'
import api, { endpoints, qk } from '../api'
import KpiCard from '../components/KpiCard'
import AISummaryCard from '../components/AISummaryCard'
import Sparkline from '../components/Sparkline'
import StatusPill from '../components/StatusPill'
import EmptyState from '../components/EmptyState'
import { formatUSD, formatNumber } from '../utils/format'

interface Dashboard {
  shipments: { total: number; blocked: number; on_hold: number; cleared: number; in_progress: number; total_value_usd: number; status_distribution: { status: string; count: number }[] }
  screening: { positive_matches: number; potential_matches: number; clear: number }
  classification: { total: number; confirmed: number; avg_confidence: number }
  savings: { fta_duty_savings_usd: number; coo_duty_savings_usd: number; duty_paid_usd: number; total_savings_usd: number }
  declarations: { total: number; submitted: number }
  documents: { total: number }
  risk_score: number
}
interface TrendsResp { months: number; series: { month: string; shipments: number; cleared: number; blocked: number; value_usd: number; fta_savings_usd: number }[] }
interface JurResp { jurisdictions: { country: string; shipments: number; value_usd: number }[] }
interface ActionItem { kind: 'shipment' | 'screening' | 'classification'; severity: 'high' | 'medium' | 'low'; id: string; shipment_id?: string; title: string; subtitle: string; at: string | null }
interface ActionResp { items: ActionItem[] }
interface AIInsight { tone: 'positive' | 'warning' | 'danger' | 'neutral'; icon?: string; title: string; body: string }

export default function DashboardPage() {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery<Dashboard>({
    queryKey: qk.dashboard(),
    queryFn: () => api.get(endpoints.analytics.dashboard).then((r) => r.data),
  })
  const { data: trends } = useQuery<TrendsResp>({
    queryKey: qk.trends(6),
    queryFn: () => api.get(endpoints.analytics.trends, { params: { months: 6 } }).then((r) => r.data),
  })
  const { data: actions } = useQuery<ActionResp>({
    queryKey: qk.actionQueue(),
    queryFn: () => api.get(endpoints.analytics.actionQueue, { params: { limit: 6 } }).then((r) => r.data),
  })
  const { data: aiInsights } = useQuery<{ insights: AIInsight[] }>({
    queryKey: qk.aiInsights(),
    queryFn: () => api.get(endpoints.analytics.aiInsights).then((r) => r.data),
  })
  const { data: jurisdictions } = useQuery<JurResp>({
    queryKey: qk.byJurisdiction(),
    queryFn: () => api.get(endpoints.analytics.byJurisdiction).then((r) => r.data),
  })

  if (isLoading || !data) {
    return (
      <div className="p-6 space-y-6">
        <div className="h-32 rounded-2xl shimmer" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-28 rounded-2xl shimmer" />)}
        </div>
        <div className="h-64 rounded-2xl shimmer" />
      </div>
    )
  }

  const complianceRate = data.shipments.total > 0
    ? Math.round((data.shipments.cleared / data.shipments.total) * 100)
    : 0

  const shipmentSpark = (trends?.series ?? []).map((s) => s.shipments)
  const savingsSpark = (trends?.series ?? []).map((s) => s.fta_savings_usd)
  const valueSpark = (trends?.series ?? []).map((s) => s.value_usd)

  const riskTone = data.risk_score < 15 ? 'success' : data.risk_score < 35 ? 'warning' : 'danger'

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-[1500px] mx-auto">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-2xs uppercase tracking-wider font-semibold text-slate-500 flex items-center gap-1.5">
            <Sparkles size={11} className="text-ai-500" /> Trade Compliance Command Center
          </p>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1">
            Welcome back. Here's where your compliance stands today.
          </h1>
        </div>
        <button
          onClick={() => navigate('/shipments')}
          className="btn-primary"
        >
          <Ship size={14} /> View all shipments
        </button>
      </div>

      {/* Hero: savings + risk + cleared */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Savings hero */}
        <div className="lg:col-span-2 relative overflow-hidden rounded-2xl text-white p-6 shadow-soft-3"
             style={{ backgroundImage: 'linear-gradient(135deg, #0b1f4d 0%, #1734bd 45%, #1d44e8 100%)' }}>
          <div className="absolute inset-0 bg-grid-fade opacity-40 pointer-events-none" />
          <div className="absolute -right-12 -top-12 w-64 h-64 rounded-full"
               style={{ background: 'radial-gradient(circle, rgb(124 58 237 / 0.45), transparent 70%)' }} />
          <div className="relative">
            <div className="flex items-center gap-2 text-brand-200 text-2xs uppercase tracking-wider font-semibold">
              <DollarSign size={12} /> Total Duty Savings · FTA + CoO optimisation
            </div>
            <p className="text-4xl sm:text-5xl font-extrabold mt-2 tabular">
              {formatUSD(data.savings.total_savings_usd)}
            </p>
            <p className="text-brand-200 text-sm mt-2">
              {formatUSD(data.savings.fta_duty_savings_usd)} from FTA analysis
              {' · '}
              {formatUSD(data.savings.coo_duty_savings_usd)} from preferential certificates of origin
            </p>
            <div className="mt-4 flex items-center gap-4 text-xs text-brand-200">
              <span className="inline-flex items-center gap-1"><TrendingDown size={12} /> {complianceRate}% compliance rate</span>
              <span>·</span>
              <span>{data.shipments.cleared} cleared</span>
              <span>·</span>
              <span>{formatUSD(data.shipments.total_value_usd)} in shipped goods</span>
            </div>
            {savingsSpark.length > 1 && (
              <div className="mt-4">
                <Sparkline values={savingsSpark} width={300} height={40} tone="ai" />
              </div>
            )}
          </div>
        </div>

        {/* Compliance risk score */}
        <div className="rounded-2xl bg-white shadow-soft-2 ring-1 ring-slate-100 p-6 flex flex-col">
          <div className="flex items-center justify-between">
            <p className="text-2xs uppercase tracking-wider font-semibold text-slate-500">Compliance Risk Score</p>
            <ShieldCheck size={16} className={riskTone === 'success' ? 'text-emerald-500' : riskTone === 'warning' ? 'text-amber-500' : 'text-red-500'} />
          </div>
          <p className={`mt-3 text-5xl font-extrabold tabular ${riskTone === 'success' ? 'text-emerald-600' : riskTone === 'warning' ? 'text-amber-600' : 'text-red-600'}`}>
            {data.risk_score}
            <span className="text-lg ml-1 font-bold text-slate-400">/ 100</span>
          </p>
          <p className="text-xs text-slate-500 mt-2 leading-relaxed">
            Computed from blocked / on-hold ratios + positive sanctions matches across {data.shipments.total} active shipments. Lower is safer.
          </p>
          <div className="mt-auto pt-4">
            <div className="flex items-center justify-between text-2xs">
              <span className="font-medium text-slate-500">Avg HS confidence</span>
              <span className="font-bold tabular text-slate-900">{Math.round(data.classification.avg_confidence * 100)}%</span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-slate-100 overflow-hidden">
              <div className="h-1.5 bg-gradient-to-r from-ai-600 to-ai-cyan" style={{ width: `${Math.round(data.classification.avg_confidence * 100)}%` }} />
            </div>
          </div>
        </div>
      </section>

      {/* KPI strip */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Shipments"
          value={formatNumber(data.shipments.total)}
          icon={<Ship size={16} />}
          tone="brand"
          spark={shipmentSpark}
        />
        <KpiCard
          label="Cleared"
          value={formatNumber(data.shipments.cleared)}
          icon={<CheckCircle2 size={16} />}
          tone="success"
          delta={{ value: `${complianceRate}% rate`, positive: true }}
        />
        <KpiCard
          label="On Hold + Blocked"
          value={data.shipments.on_hold + data.shipments.blocked}
          icon={<AlertTriangle size={16} />}
          tone={data.shipments.blocked > 0 ? 'danger' : 'warning'}
        />
        <KpiCard
          label="In Progress"
          value={data.shipments.in_progress}
          icon={<Clock size={16} />}
          tone="ai"
        />
      </section>

      {/* Two-column: AI insights + action queue */}
      <section className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        <div className="lg:col-span-3">
          <AISummaryCard
            insights={aiInsights?.insights ?? []}
            title="Live AI Insights"
          />
        </div>
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-soft-2 ring-1 ring-slate-100 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 flex items-center gap-2">
              <Activity size={14} className="text-brand-500" /> Action Queue
            </h3>
            <Link to="/shipments" className="text-xs text-brand-600 hover:text-brand-700 font-medium inline-flex items-center gap-1">
              View all <ChevronRight size={12} />
            </Link>
          </div>
          {(actions?.items?.length ?? 0) === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="Inbox zero"
              description="No items need your review right now."
              tone="brand"
            />
          ) : (
            <div className="space-y-2">
              {actions!.items.map((it) => {
                const dotClass =
                  it.severity === 'high' ? 'bg-red-500' :
                  it.severity === 'medium' ? 'bg-amber-500' : 'bg-brand-500'
                const target = it.kind === 'shipment' ? `/shipments/${it.id}` :
                  it.kind === 'screening' ? '/screening' : '/classification'
                return (
                  <button
                    key={`${it.kind}-${it.id}`}
                    onClick={() => navigate(target)}
                    className="w-full flex items-start gap-3 p-2.5 rounded-lg hover:bg-slate-50 text-left transition-colors group"
                  >
                    <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${dotClass} animate-pulse`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-slate-900 truncate">{it.title}</p>
                      <p className="text-xs text-slate-500 truncate">{it.subtitle}</p>
                    </div>
                    <ArrowRight size={14} className="text-slate-300 group-hover:text-brand-500 mt-2 shrink-0" />
                  </button>
                )
              })}
            </div>
          )}
        </div>
      </section>

      {/* Compliance signals */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Status distribution */}
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-soft-2 ring-1 ring-slate-100 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Shipment Pipeline</h3>
            <span className="text-2xs text-emerald-700 bg-emerald-50 ring-1 ring-emerald-100 px-2.5 py-0.5 rounded-full font-semibold">
              {complianceRate}% cleared
            </span>
          </div>
          <div className="space-y-2">
            {data.shipments.status_distribution.length === 0 ? (
              <p className="text-sm text-slate-500">No shipments yet.</p>
            ) : data.shipments.status_distribution.map((item) => {
              const pct = data.shipments.total > 0 ? Math.round((item.count / data.shipments.total) * 100) : 0
              return (
                <div key={item.status} className="flex items-center gap-3">
                  <div className="w-36 shrink-0">
                    <StatusPill status={item.status} size="sm" />
                  </div>
                  <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-2 rounded-full transition-[width] duration-700 ease-out"
                      style={{
                        width: `${pct}%`,
                        background:
                          item.status === 'blocked' ? '#dc2626' :
                          item.status === 'hold' ? '#d97706' :
                          item.status === 'cleared' ? '#16a34a' :
                          item.status === 'screening' || item.status === 'classification' ? 'linear-gradient(90deg,#7c3aed,#06b6d4)' :
                          '#1d44e8',
                      }}
                    />
                  </div>
                  <span className="text-sm font-bold tabular text-slate-900 w-6 text-right">{item.count}</span>
                  <span className="text-2xs text-slate-400 tabular w-9 text-right">{pct}%</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Compliance modules */}
        <div className="bg-white rounded-2xl shadow-soft-2 ring-1 ring-slate-100 p-5">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-4">Compliance Modules</h3>
          <div className="space-y-3">
            <ModuleStat icon={<Tag size={14} className="text-brand-600" />} label="HS Classifications" value={`${data.classification.confirmed} / ${data.classification.total} confirmed`} tone="brand" />
            <ModuleStat icon={<ShieldAlert size={14} className="text-red-600" />} label="Sanctions Hits" value={`${data.screening.positive_matches} positive · ${data.screening.potential_matches} potential`} tone={data.screening.positive_matches ? 'danger' : 'success'} />
            <ModuleStat icon={<Brain size={14} className="text-ai-600" />} label="Avg AI Confidence" value={`${Math.round(data.classification.avg_confidence * 100)}%`} tone="ai" />
            <ModuleStat icon={<TrendingDown size={14} className="text-emerald-600" />} label="Duty Saved (FTA)" value={formatUSD(data.savings.fta_duty_savings_usd)} tone="success" />
          </div>
        </div>
      </section>

      {/* Lanes / jurisdictions */}
      {jurisdictions && jurisdictions.jurisdictions.length > 0 && (
        <section className="bg-white rounded-2xl shadow-soft-2 ring-1 ring-slate-100 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Top Destinations</h3>
            <span className="text-2xs text-slate-500">By shipment count + value</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {jurisdictions.jurisdictions.slice(0, 10).map((j) => (
              <div key={j.country} className="bg-slate-50 rounded-xl p-3 ring-1 ring-slate-100">
                <p className="font-mono text-sm font-bold text-slate-900">{j.country}</p>
                <p className="text-xs text-slate-500 mt-0.5">{j.shipments} shipments</p>
                <p className="text-xs font-semibold tabular text-brand-700 mt-1">{formatUSD(j.value_usd)}</p>
              </div>
            ))}
          </div>
          {valueSpark.length > 1 && (
            <div className="mt-4 flex items-center justify-between text-2xs text-slate-500">
              <span>6-month shipped value trend</span>
              <Sparkline values={valueSpark} width={200} height={32} tone="brand" />
            </div>
          )}
        </section>
      )}
    </div>
  )
}

function ModuleStat({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: string; tone: 'brand' | 'success' | 'danger' | 'ai' }) {
  const toneBg = tone === 'brand' ? 'bg-brand-50' : tone === 'success' ? 'bg-emerald-50' : tone === 'danger' ? 'bg-red-50' : 'bg-ai-50'
  return (
    <div className="flex items-center gap-3">
      <div className={`p-2 rounded-lg ${toneBg}`}>{icon}</div>
      <div className="min-w-0 flex-1">
        <p className="text-2xs uppercase tracking-wider font-semibold text-slate-500">{label}</p>
        <p className="text-sm font-bold text-slate-900 truncate">{value}</p>
      </div>
    </div>
  )
}
