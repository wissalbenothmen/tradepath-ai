import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Ship, ChevronRight, Search, Filter, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import api, { endpoints, qk } from '../api'
import StatusPill from '../components/StatusPill'
import EmptyState from '../components/EmptyState'
import { SkeletonRow } from '../components/Skeleton'
import { toast } from '../components/Toast'
import { formatUSD } from '../utils/format'

interface Shipment {
  id: string; reference_number: string; status: string; origin_country: string;
  destination_country: string; exporter_name: string | null; total_value_usd: number | null;
  denied_party_status: string | null; restriction_status: string | null;
}

const STATUS_FILTERS = [
  { value: '', label: 'All' },
  { value: 'draft', label: 'Draft' },
  { value: 'screening', label: 'Screening' },
  { value: 'classification', label: 'Classification' },
  { value: 'declaration_ready', label: 'Ready' },
  { value: 'filed', label: 'Filed' },
  { value: 'cleared', label: 'Cleared' },
  { value: 'hold', label: 'On hold' },
  { value: 'blocked', label: 'Blocked' },
] as const

export default function ShipmentsPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [showForm, setShowForm] = useState(false)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [form, setForm] = useState({
    origin_country: '', destination_country: '', transport_mode: '',
    incoterms: '', exporter_name: '', consignee_name: '', total_value_usd: '',
  })

  const { data: shipments = [], isLoading, error } = useQuery<Shipment[]>({
    queryKey: qk.shipments(),
    queryFn: () => api.get(endpoints.shipments.list).then((r) => r.data),
  })

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return shipments.filter((s) => {
      if (statusFilter && s.status !== statusFilter) return false
      if (!q) return true
      return (
        s.reference_number.toLowerCase().includes(q) ||
        (s.exporter_name ?? '').toLowerCase().includes(q) ||
        s.origin_country.toLowerCase().includes(q) ||
        s.destination_country.toLowerCase().includes(q)
      )
    })
  }, [shipments, query, statusFilter])

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post(endpoints.shipments.list, body),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: qk.shipments() })
      qc.invalidateQueries({ queryKey: qk.dashboard() })
      setShowForm(false)
      setForm({ origin_country: '', destination_country: '', transport_mode: '', incoterms: '', exporter_name: '', consignee_name: '', total_value_usd: '' })
      toast(`Shipment ${res.data.reference_number} created`, 'success')
    },
    onError: () => toast('Failed to create shipment — please try again', 'error'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const body: Record<string, unknown> = {
      origin_country: form.origin_country.toUpperCase(),
      destination_country: form.destination_country.toUpperCase(),
    }
    if (form.transport_mode) body.transport_mode = form.transport_mode
    if (form.incoterms) body.incoterms = form.incoterms
    if (form.exporter_name) body.exporter_name = form.exporter_name
    if (form.consignee_name) body.consignee_name = form.consignee_name
    if (form.total_value_usd) body.total_value_usd = parseFloat(form.total_value_usd)
    createMutation.mutate(body)
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-5 max-w-[1500px] mx-auto">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <p className="text-2xs uppercase tracking-wider font-semibold text-slate-500">Shipments</p>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1">
            All shipments
          </h1>
          <p className="text-sm text-slate-500 mt-1">{shipments.length} shipments · click any row to drill into compliance status.</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary">
          {showForm ? <X size={14} /> : <Plus size={14} />}
          {showForm ? 'Cancel' : 'New shipment'}
        </button>
      </div>

      {/* New shipment form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-soft-2 ring-1 ring-brand-100 p-5 space-y-4">
          <h3 className="font-semibold text-slate-900">New shipment</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {(['origin_country', 'destination_country', 'transport_mode', 'incoterms', 'exporter_name', 'consignee_name'] as const).map((field) => (
              <div key={field}>
                <label className="block text-2xs font-semibold uppercase tracking-wider text-slate-500 mb-1">{field.replace(/_/g, ' ')}</label>
                <input
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  value={form[field]}
                  onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                  required={field === 'origin_country' || field === 'destination_country'}
                  placeholder={field === 'origin_country' ? 'CHN' : field === 'destination_country' ? 'USA' : ''}
                />
              </div>
            ))}
            <div>
              <label className="block text-2xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Total value (USD)</label>
              <input
                type="number"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none"
                value={form.total_value_usd}
                onChange={(e) => setForm({ ...form, total_value_usd: e.target.value })}
              />
            </div>
          </div>
          <div className="flex gap-3">
            <button type="submit" disabled={createMutation.isPending} className="btn-primary">
              {createMutation.isPending ? 'Creating…' : 'Create shipment'}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="btn-ghost">Cancel</button>
          </div>
        </form>
      )}

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search reference, exporter, lane…"
            className="w-full bg-white pl-9 pr-3 py-2 rounded-lg text-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 outline-none"
          />
        </div>
        <div className="flex items-center gap-1.5 overflow-x-auto">
          <Filter size={14} className="text-slate-400" />
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={`px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap transition-colors ${
                statusFilter === f.value
                  ? 'bg-brand-600 text-white shadow-soft-1'
                  : 'bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-2xl bg-red-50 ring-1 ring-red-200 p-4 text-red-700 text-sm">
          Couldn't load shipments. Please refresh.
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-2xl shadow-soft-2 ring-1 ring-slate-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[760px]">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left text-2xs font-bold uppercase tracking-wider text-slate-500">Reference</th>
                <th className="px-4 py-3 text-left text-2xs font-bold uppercase tracking-wider text-slate-500">Status</th>
                <th className="px-4 py-3 text-left text-2xs font-bold uppercase tracking-wider text-slate-500">Route</th>
                <th className="px-4 py-3 text-left text-2xs font-bold uppercase tracking-wider text-slate-500">Exporter</th>
                <th className="px-4 py-3 text-left text-2xs font-bold uppercase tracking-wider text-slate-500 hidden sm:table-cell">Value</th>
                <th className="px-4 py-3 text-left text-2xs font-bold uppercase tracking-wider text-slate-500 hidden md:table-cell">DPS</th>
                <th className="px-4 py-3 text-left text-2xs font-bold uppercase tracking-wider text-slate-500 hidden lg:table-cell">Restrictions</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading && Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} />)}
              {!isLoading && filtered.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-8">
                  <EmptyState
                    icon={Ship}
                    title={query || statusFilter ? 'No matches' : 'No shipments yet'}
                    description={query || statusFilter
                      ? 'Try a different search or clear the status filter.'
                      : 'Create your first shipment using the button above.'}
                    tone="brand"
                  />
                </td></tr>
              )}
              {!isLoading && filtered.map((s) => (
                <tr
                  key={s.id}
                  className="hover:bg-brand-50/40 transition-colors cursor-pointer group"
                  onClick={() => navigate(`/shipments/${s.id}`)}
                >
                  <td className="px-4 py-3 font-mono text-xs font-bold text-brand-700">{s.reference_number}</td>
                  <td className="px-4 py-3"><StatusPill status={s.status} size="sm" /></td>
                  <td className="px-4 py-3 font-medium whitespace-nowrap text-slate-900">
                    <span className="font-mono">{s.origin_country}</span>
                    <span className="text-slate-400 mx-1">→</span>
                    <span className="font-mono">{s.destination_country}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-600 truncate max-w-[200px]">{s.exporter_name || <span className="text-slate-400">—</span>}</td>
                  <td className="px-4 py-3 font-semibold tabular hidden sm:table-cell text-slate-900">{formatUSD(s.total_value_usd)}</td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    {s.denied_party_status ? <StatusPill status={s.denied_party_status} size="sm" /> : <span className="text-slate-400">—</span>}
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell">
                    {s.restriction_status ? <StatusPill status={s.restriction_status} size="sm" /> : <span className="text-slate-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-slate-300 group-hover:text-brand-500 transition-colors">
                    <ChevronRight size={14} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
