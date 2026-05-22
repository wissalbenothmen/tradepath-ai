import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { TrendingDown, DollarSign, Info } from 'lucide-react'
import api from '../api'
import AIThinking from '../components/AIThinking'
import ShipmentSelector from '../components/ShipmentSelector'
import { toast } from '../components/Toast'
import { formatUSD } from '../utils/format'

interface FTAResult {
  id: string; hs_code: string; applicable_ftas: string[] | null;
  mfn_duty_rate: number | null; preferential_duty_rate: number | null;
  duty_saving_usd: number | null; gpt_analysis: string | null;
}

export default function FTAPage() {
  const [form, setForm] = useState({ shipment_id: '', hs_code_6digit: '', product_description: '', declared_value_usd: '' })
  const [result, setResult] = useState<FTAResult | null>(null)

  const mutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/fta', body),
    onSuccess: (res) => {
      setResult(res.data)
      const saving = res.data.duty_saving_usd
      const ftas = res.data.applicable_ftas
      if (ftas && ftas.length > 0 && saving > 0) {
        toast(`FTA analysis complete — ${ftas[0]} qualifies. Estimated saving: ${formatUSD(saving)}`, 'success')
      } else if (ftas && ftas.length > 0) {
        toast(`FTA analysis complete — ${ftas[0]} may apply`, 'success')
      } else {
        toast('FTA analysis complete — no applicable FTAs found for this trade lane', 'info')
      }
    },
    onError: () => toast('FTA analysis failed — please try again', 'error'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate({
      shipment_id: form.shipment_id,
      hs_code_6digit: form.hs_code_6digit,
      product_description: form.product_description,
      declared_value_usd: parseFloat(form.declared_value_usd),
    })
  }

  return (
    <div className="p-4 sm:p-8 space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">FTA Analysis</h2>
        <p className="text-gray-500 mt-1">Identify applicable Free Trade Agreements and calculate duty savings</p>
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
                <label className="block text-sm font-medium text-gray-700 mb-1">HS Code (6-digit) <span className="text-red-500">*</span></label>
                <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  value={form.hs_code_6digit}
                  onChange={(e) => setForm({ ...form, hs_code_6digit: e.target.value })}
                  placeholder="847130" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Declared Value (USD) <span className="text-red-500">*</span></label>
                <input type="number" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  value={form.declared_value_usd}
                  onChange={(e) => setForm({ ...form, declared_value_usd: e.target.value })}
                  placeholder="50000" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Product Description <span className="text-red-500">*</span></label>
                <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  value={form.product_description} onChange={(e) => setForm({ ...form, product_description: e.target.value })}
                  placeholder="Laptop computers" required />
              </div>
            </div>
            <button type="submit" disabled={mutation.isPending}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-60">
              <TrendingDown size={16} />
              {mutation.isPending ? 'Analyzing FTAs...' : 'Run FTA Analysis'}
            </button>
          </form>
        </div>

        {/* Help panel */}
        <div className="space-y-4">
          <div className="bg-green-50 border border-green-100 rounded-xl p-5">
            <h3 className="font-semibold text-green-900 flex items-center gap-2 text-sm mb-3">
              <DollarSign size={15} /> Major FTAs Covered
            </h3>
            <ul className="space-y-1.5 text-xs text-green-800">
              {[
                'USMCA (US-Mexico-Canada)',
                'EU-Japan EPA',
                'CPTPP (11 countries)',
                'ASEAN FTA',
                'US-Korea (KORUS)',
                'EU-South Korea',
                'RCEP (15 Asia-Pacific)',
                'EU-Singapore FTA',
              ].map((fta) => (
                <li key={fta} className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" />
                  {fta}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
            <h3 className="font-semibold text-blue-900 text-sm flex items-center gap-2 mb-2">
              <Info size={14} /> How It Works
            </h3>
            <p className="text-xs text-blue-800 leading-relaxed">
              TradePath AI checks the shipment's origin-destination trade lane against all active FTAs,
              then calculates MFN vs preferential duty rates using your HS code and declared value.
              Results include estimated savings for customs filing decisions.
            </p>
          </div>
        </div>
      </div>

      {mutation.isPending && (
        <AIThinking label="Analyzing applicable Free Trade Agreements and calculating duty savings..." />
      )}

      {result && !mutation.isPending && (
        <div className="bg-white rounded-xl shadow-sm p-6 space-y-5">
          <div className="flex items-center gap-3">
            <TrendingDown className="text-blue-500" size={22} />
            <h3 className="text-lg font-semibold text-gray-900">FTA Analysis Result</h3>
          </div>

          {result.applicable_ftas && result.applicable_ftas.length > 0 ? (
            <div>
              <p className="text-sm text-gray-500 mb-2">Applicable FTAs</p>
              <div className="flex flex-wrap gap-2">
                {result.applicable_ftas.map((fta) => (
                  <span key={fta} className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">{fta}</span>
                ))}
              </div>
            </div>
          ) : (
            <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-600">No applicable FTAs found for this trade lane.</div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-xs text-gray-500">MFN Duty Rate</p>
              <p className="text-xl font-bold text-gray-900">{result.mfn_duty_rate !== null ? `${(result.mfn_duty_rate * 100).toFixed(1)}%` : '—'}</p>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <p className="text-xs text-gray-500">Preferential Rate</p>
              <p className="text-xl font-bold text-green-700">{result.preferential_duty_rate !== null ? `${(result.preferential_duty_rate * 100).toFixed(1)}%` : '—'}</p>
            </div>
            <div className="bg-blue-50 rounded-lg p-4 flex items-center gap-3">
              <DollarSign className="text-blue-600" size={20} />
              <div>
                <p className="text-xs text-gray-500">Estimated Duty Saving</p>
                <p className="text-xl font-bold text-blue-700">{result.duty_saving_usd !== null ? formatUSD(result.duty_saving_usd) : '—'}</p>
              </div>
            </div>
          </div>

          {result.gpt_analysis && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">AI Analysis</p>
              <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700 leading-relaxed">{result.gpt_analysis}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
