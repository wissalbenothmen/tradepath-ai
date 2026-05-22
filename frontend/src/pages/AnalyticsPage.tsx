import { useQuery } from '@tanstack/react-query'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend,
  PieChart, Pie, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { Activity, TrendingDown, Sparkles, ShieldAlert, Globe2 } from 'lucide-react'
import api, { endpoints, qk } from '../api'
import { formatUSD, formatNumber } from '../utils/format'
import StatusPill from '../components/StatusPill'

interface Dashboard {
  shipments: { total: number; blocked: number; on_hold: number; cleared: number; in_progress: number; total_value_usd: number; status_distribution: { status: string; count: number }[] }
  screening: { positive_matches: number; potential_matches: number; clear: number }
  classification: { total: number; confirmed: number; avg_confidence: number }
  savings: { fta_duty_savings_usd: number; coo_duty_savings_usd: number; duty_paid_usd: number; total_savings_usd: number }
  risk_score: number
}
interface TrendsResp { months: number; series: { month: string; shipments: number; cleared: number; blocked: number; value_usd: number; fta_savings_usd: number }[] }
interface JurResp { jurisdictions: { country: string; shipments: number; value_usd: number }[] }
interface FTAResp { ftas: { agreement: string; coo_count: number; analysis_count: number; savings_usd: number }[] }

const STATUS_COLOR_HEX: Record<string, string> = {
  draft: '#94a3b8',
  screening: '#7c3aed',
  classification: '#8b5cf6',
  declaration_ready: '#1d44e8',
  filed: '#3460ff',
  cleared: '#16a34a',
  hold: '#d97706',
  blocked: '#dc2626',
}

export default function AnalyticsPage() {
  const { data: dash } = useQuery<Dashboard>({
    queryKey: qk.dashboard(),
    queryFn: () => api.get(endpoints.analytics.dashboard).then((r) => r.data),
  })
  const { data: trends } = useQuery<TrendsResp>({
    queryKey: qk.trends(6),
    queryFn: () => api.get(endpoints.analytics.trends, { params: { months: 6 } }).then((r) => r.data),
  })
  const { data: jurisdictions } = useQuery<JurResp>({
    queryKey: qk.byJurisdiction(),
    queryFn: () => api.get(endpoints.analytics.byJurisdiction).then((r) => r.data),
  })
  const { data: ftas } = useQuery<FTAResp>({
    queryKey: qk.topFtas(),
    queryFn: () => api.get(endpoints.analytics.topFtas).then((r) => r.data),
  })

  if (!dash || !trends) {
    return (
      <div className="p-6 space-y-4">
        {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-32 rounded-2xl shimmer" />)}
      </div>
    )
  }

  const screeningPie = [
    { name: 'Positive', value: dash.screening.positive_matches, color: '#dc2626' },
    { name: 'Potential', value: dash.screening.potential_matches, color: '#d97706' },
    { name: 'Clear', value: dash.screening.clear, color: '#16a34a' },
  ].filter((d) => d.value > 0)

  const blockRate = dash.shipments.total > 0
    ? Math.round((dash.shipments.blocked / dash.shipments.total) * 100) : 0
  const confirmRate = dash.classification.total > 0
    ? Math.round((dash.classification.confirmed / dash.classification.total) * 100) : 0

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-[1500px] mx-auto">
      {/* Page header */}
      <div>
        <p className="text-2xs uppercase tracking-wider font-semibold text-slate-500 flex items-center gap-1.5">
          <Activity size={11} className="text-brand-500" /> Analytics
        </p>
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1">
          The full picture — across <span className="ai-text-gradient">{dash.shipments.total}</span> shipments
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          {trends.series.length} months of compliance history · {formatUSD(dash.shipments.total_value_usd)} in shipped goods
        </p>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi label="Total Savings" value={formatUSD(dash.savings.total_savings_usd)} tone="success" icon={<TrendingDown size={14} />} />
        <Kpi label="Block Rate" value={`${blockRate}%`} tone={blockRate > 0 ? 'danger' : 'success'} icon={<ShieldAlert size={14} />} />
        <Kpi label="Classification Rate" value={`${confirmRate}%`} tone="brand" icon={<Sparkles size={14} />} />
        <Kpi label="Risk Score" value={`${dash.risk_score}/100`} tone={dash.risk_score < 15 ? 'success' : dash.risk_score < 35 ? 'warning' : 'danger'} icon={<Activity size={14} />} />
      </div>

      {/* Time-series: shipments + savings stacked */}
      <Panel
        title="Shipment Volume & Duty Savings"
        subtitle="Monthly volume with overlaid FTA savings."
        accent="brand"
      >
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={trends.series} margin={{ top: 5, right: 25, left: 0, bottom: 5 }}>
            <defs>
              <linearGradient id="gradShipments" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#1d44e8" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#1d44e8" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradCleared" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#16a34a" stopOpacity={0.30} />
                <stop offset="100%" stopColor="#16a34a" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradSavings" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.30} />
                <stop offset="100%" stopColor="#06b6d4" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#64748b' }} />
            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
            <Tooltip
              contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12, boxShadow: '0 4px 16px rgba(15,23,42,0.08)' }}
              formatter={(v: number, name: string) => {
                if (name === 'FTA Savings (USD)') return [formatUSD(v), name]
                return [v, name]
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Area type="monotone" dataKey="shipments" stroke="#1d44e8" strokeWidth={2} fill="url(#gradShipments)" name="Shipments" />
            <Area type="monotone" dataKey="cleared" stroke="#16a34a" strokeWidth={2} fill="url(#gradCleared)" name="Cleared" />
            <Area yAxisId={0} type="monotone" dataKey="fta_savings_usd" stroke="#7c3aed" strokeWidth={2} fill="url(#gradSavings)" name="FTA Savings (USD)" />
          </AreaChart>
        </ResponsiveContainer>
      </Panel>

      {/* Two-column: FTA savings + status distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        {/* FTA Savings by Agreement */}
        <Panel
          title="FTA Duty Savings by Agreement"
          subtitle="Aggregated across certificates of origin and FTA analyses."
          className="lg:col-span-3"
          accent="ai"
          chip={ftas?.ftas?.length
            ? `${formatUSD((ftas.ftas ?? []).reduce((s, x) => s + x.savings_usd, 0))} total`
            : undefined}
        >
          {(ftas?.ftas?.length ?? 0) === 0 ? (
            <p className="text-sm text-slate-500">No FTA analyses yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={ftas!.ftas.slice(0, 8)} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                <YAxis type="category" dataKey="agreement" tick={{ fontSize: 12, fill: '#0f172a' }} width={110} />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }}
                  formatter={(v: number) => [formatUSD(v), 'Savings']}
                />
                <Bar dataKey="savings_usd" radius={[0, 8, 8, 0]}>
                  {ftas!.ftas.slice(0, 8).map((_, i) => (
                    <Cell key={i} fill={`url(#gradFta${i})`} />
                  ))}
                </Bar>
                <defs>
                  {ftas!.ftas.slice(0, 8).map((_, i) => (
                    <linearGradient key={i} id={`gradFta${i}`} x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.85} />
                      <stop offset="100%" stopColor="#06b6d4" stopOpacity={0.85} />
                    </linearGradient>
                  ))}
                </defs>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Panel>

        {/* Pipeline */}
        <Panel
          title="Pipeline"
          subtitle="Where shipments live right now."
          className="lg:col-span-2"
          accent="brand"
        >
          <div className="space-y-2">
            {dash.shipments.status_distribution.map((item) => {
              const pct = dash.shipments.total > 0 ? Math.round((item.count / dash.shipments.total) * 100) : 0
              return (
                <div key={item.status} className="flex items-center gap-3">
                  <div className="w-36 shrink-0">
                    <StatusPill status={item.status} size="sm" />
                  </div>
                  <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-2 rounded-full transition-[width] duration-700"
                      style={{ width: `${pct}%`, background: STATUS_COLOR_HEX[item.status] || '#1d44e8' }}
                    />
                  </div>
                  <span className="text-sm font-bold tabular text-slate-900 w-6 text-right">{item.count}</span>
                </div>
              )
            })}
          </div>
        </Panel>
      </div>

      {/* Screening + jurisdictions */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        <Panel
          title="Sanctions Screening Mix"
          subtitle="OFAC, BIS, EU, UN, UK and 3 more lists checked."
          className="lg:col-span-2"
          accent="danger"
        >
          {screeningPie.length === 0 ? (
            <p className="text-sm text-slate-500">No screenings yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={screeningPie}
                  dataKey="value"
                  nameKey="name"
                  cx="50%" cy="50%"
                  innerRadius={48}
                  outerRadius={85}
                  paddingAngle={2}
                  label={({ name, percent }) => percent > 0.04 ? `${name} ${(percent * 100).toFixed(0)}%` : ''}
                  labelLine={false}
                >
                  {screeningPie.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Panel>
        <Panel
          title="Top Destinations"
          subtitle="By shipment count + value."
          className="lg:col-span-3"
          accent="brand"
        >
          {(jurisdictions?.jurisdictions?.length ?? 0) === 0 ? (
            <p className="text-sm text-slate-500">No shipments yet.</p>
          ) : (
            <div className="space-y-2">
              {jurisdictions!.jurisdictions.slice(0, 8).map((j) => {
                const maxValue = Math.max(...(jurisdictions!.jurisdictions.map((x) => x.value_usd)))
                const pct = maxValue > 0 ? (j.value_usd / maxValue) * 100 : 0
                return (
                  <div key={j.country} className="flex items-center gap-3">
                    <div className="w-12 shrink-0 flex items-center gap-1.5">
                      <Globe2 size={12} className="text-brand-500" />
                      <span className="font-mono text-sm font-bold text-slate-900">{j.country}</span>
                    </div>
                    <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-2 rounded-full bg-gradient-to-r from-brand-500 to-ai-cyan transition-[width] duration-700"
                           style={{ width: `${pct}%` }} />
                    </div>
                    <div className="w-24 text-right shrink-0">
                      <span className="text-2xs text-slate-400 tabular">{j.shipments} ship · </span>
                      <span className="text-xs font-bold text-brand-700 tabular">{formatUSD(j.value_usd)}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </Panel>
      </div>

      {/* Footnote / data provenance */}
      <p className="text-2xs text-slate-400 text-center">
        Every figure on this page is computed live from your tenant data. No synthetic backfills.
      </p>
    </div>
  )
}

function Kpi({ label, value, icon, tone }: { label: string; value: string; icon?: React.ReactNode; tone: 'brand' | 'success' | 'danger' | 'warning' }) {
  const styles = {
    brand: 'text-brand-600 bg-brand-50',
    success: 'text-emerald-600 bg-emerald-50',
    danger: 'text-red-600 bg-red-50',
    warning: 'text-amber-600 bg-amber-50',
  }[tone]
  return (
    <div className="bg-white rounded-2xl shadow-soft-1 ring-1 ring-slate-100 p-4 flex items-center gap-3">
      {icon && <div className={`p-2 rounded-lg ${styles}`}>{icon}</div>}
      <div>
        <p className="text-2xs uppercase tracking-wider font-semibold text-slate-500">{label}</p>
        <p className="text-xl font-bold text-slate-900 tabular">{value}</p>
      </div>
    </div>
  )
}

function Panel({
  title, subtitle, children, className = '', accent = 'brand', chip,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
  className?: string
  accent?: 'brand' | 'ai' | 'danger'
  chip?: string
}) {
  const accentColor = accent === 'ai' ? 'from-ai-500 to-ai-cyan' : accent === 'danger' ? 'from-red-500 to-amber-500' : 'from-brand-500 to-brand-700'
  return (
    <div className={`bg-white rounded-2xl shadow-soft-2 ring-1 ring-slate-100 overflow-hidden ${className}`}>
      <div className={`h-0.5 bg-gradient-to-r ${accentColor}`} />
      <div className="p-5">
        <div className="flex items-start justify-between mb-3 gap-3">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">{title}</h3>
            {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
          </div>
          {chip && (
            <span className="text-2xs font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-100 px-2.5 py-0.5 rounded-full">
              {chip}
            </span>
          )}
        </div>
        {children}
      </div>
    </div>
  )
}
