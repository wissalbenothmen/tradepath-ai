import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ShieldAlert, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react'
import api from '../api'
import Badge, { statusVariant } from '../components/Badge'
import AIThinking from '../components/AIThinking'
import ShipmentSelector from '../components/ShipmentSelector'
import { toast } from '../components/Toast'

interface ScreeningResult {
  id: string; party_name: string; party_type: string; party_country: string | null;
  overall_result: string; highest_score: number;
  matches: { matched_name: string; list: string; score: number; country: string | null }[] | null;
  lists_checked: string[] | null;
}

export default function ScreeningPage() {
  const [form, setForm] = useState({ shipment_id: '', party_name: '', party_type: 'consignee', party_country: '' })
  const [result, setResult] = useState<ScreeningResult | null>(null)

  const mutation = useMutation({
    mutationFn: (body: Record<string, string>) => api.post('/screening', body),
    onSuccess: (res) => {
      setResult(res.data)
      const outcome = res.data.overall_result
      if (outcome === 'positive_match') {
        toast(`POSITIVE MATCH — ${res.data.party_name} flagged on ${res.data.lists_checked?.length || 0} list(s). Shipment blocked.`, 'error')
      } else if (outcome === 'potential_match') {
        toast(`Potential match found for ${res.data.party_name} — manual review required`, 'warning')
      } else {
        toast(`${res.data.party_name} cleared across all ${res.data.lists_checked?.length || 0} lists`, 'success')
      }
    },
    onError: () => toast('Screening failed — please try again', 'error'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const body: Record<string, string> = {
      shipment_id: form.shipment_id,
      party_name: form.party_name,
      party_type: form.party_type,
    }
    if (form.party_country) body.party_country = form.party_country
    mutation.mutate(body)
  }

  const resultIcon = result ? {
    clear: <CheckCircle2 className="text-green-500" size={24} />,
    potential_match: <AlertTriangle className="text-yellow-500" size={24} />,
    positive_match: <XCircle className="text-red-500" size={24} />,
  }[result.overall_result] || null : null

  return (
    <div className="p-4 sm:p-8 space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Denied Party Screening</h2>
        <p className="text-gray-500 mt-1">Screen parties against 8 international sanctions and export control lists</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm p-6 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <ShipmentSelector
            value={form.shipment_id}
            onChange={(id) => setForm({ ...form, shipment_id: id })}
            required
            label="Linked Shipment"
          />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Party Name *</label>
            <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              value={form.party_name} onChange={(e) => setForm({ ...form, party_name: e.target.value })}
              placeholder="Full legal entity name" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Party Type</label>
            <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              value={form.party_type} onChange={(e) => setForm({ ...form, party_type: e.target.value })}>
              {['consignee', 'shipper', 'notify', 'manufacturer', 'freight_forwarder'].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Country (ISO 2)</label>
            <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              value={form.party_country} onChange={(e) => setForm({ ...form, party_country: e.target.value })}
              placeholder="e.g., IR" maxLength={2} />
          </div>
        </div>
        <button type="submit" disabled={mutation.isPending}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-60">
          <ShieldAlert size={16} />
          {mutation.isPending ? 'Screening...' : 'Run Screening'}
        </button>
      </form>
        </div>

        {/* Contextual help panel */}
        <div className="space-y-4">
          <div className="bg-red-50 border border-red-100 rounded-xl p-5">
            <h3 className="font-semibold text-red-900 flex items-center gap-2 mb-3">
              <ShieldAlert size={15} /> Lists Checked (8)
            </h3>
            <ul className="space-y-1 text-xs text-red-800">
              {['OFAC SDN (US Treasury)', 'BIS Entity List (US Commerce)', 'EU Consolidated Sanctions', 'UN Security Council List', 'OFAC Non-SDN (NSA)', 'UK OFSI Consolidated', 'Canada Autonomous Sanctions', 'Interpol Red Notices'].map((list) => (
                <li key={list} className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400 shrink-0" />
                  {list}
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
            <h3 className="font-semibold text-gray-800 text-sm mb-2">Score Thresholds</h3>
            <ul className="space-y-1.5 text-xs text-gray-700">
              <li className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-red-500 shrink-0" /> Score ≥ 90: Positive match — shipment blocked</li>
              <li className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-yellow-500 shrink-0" /> Score 70–89: Potential match — manual review</li>
              <li className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-green-500 shrink-0" /> Score &lt; 70: Clear — no action needed</li>
            </ul>
          </div>
        </div>
      </div>

      {mutation.isPending && (
        <AIThinking label="Checking party against 8 international sanctions and export control lists..." />
      )}

      {result && !mutation.isPending && (
        <div className="bg-white rounded-xl shadow-sm p-6 space-y-5">
          <div className="flex items-center gap-3">
            {resultIcon}
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{result.party_name}</h3>
              <div className="flex items-center gap-3 mt-1">
                <Badge label={result.overall_result.replace(/_/g, ' ')} variant={statusVariant(result.overall_result)} />
                <span className="text-sm text-gray-500">Score: {result.highest_score.toFixed(1)}/100</span>
              </div>
            </div>
          </div>

          {result.lists_checked && (
            <div>
              <p className="text-xs text-gray-500 mb-2">Lists checked ({result.lists_checked.length})</p>
              <div className="flex flex-wrap gap-1.5">
                {result.lists_checked.map((l) => (
                  <span key={l} className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded text-xs">{l.toUpperCase()}</span>
                ))}
              </div>
            </div>
          )}

          {result.matches && result.matches.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Matches Found ({result.matches.length})</p>
              <div className="space-y-2">
                {result.matches.map((m, i) => (
                  <div key={i} className={`rounded-lg p-3 border ${m.score >= 90 ? 'border-red-200 bg-red-50' : 'border-yellow-200 bg-yellow-50'}`}>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-gray-900">{m.matched_name}</span>
                      <span className={`text-sm font-bold ${m.score >= 90 ? 'text-red-600' : 'text-yellow-600'}`}>{m.score.toFixed(1)}%</span>
                    </div>
                    <div className="flex gap-3 mt-1 text-xs text-gray-500">
                      <span>List: {m.list.toUpperCase()}</span>
                      {m.country && <span>Country: {m.country}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.overall_result === 'clear' && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-800">
              No matches found across all checked lists. Party is cleared for this shipment.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
