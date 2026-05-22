import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Tag, CheckCircle2, AlertTriangle, Info } from 'lucide-react'
import api from '../api'
import AIThinking from '../components/AIThinking'
import { toast } from '../components/Toast'
import { formatHSCode, formatPct } from '../utils/format'

interface ClassificationResult {
  id: string; hs_code_6digit: string; hs_code_us_hts: string | null;
  hs_code_eu_taric: string | null; hs_code_uk_gt: string | null;
  confidence: number; gri_rules_applied: number[] | null;
  top_candidates: { hs_code: string; description: string; confidence: number }[] | null;
  gpt_reasoning: string | null; is_itar_ear_flagged: string;
  duty_rate_us: number | null; duty_rate_eu: number | null;
}

export default function ClassificationPage() {
  const [form, setForm] = useState({ product_description: '', materials: '', intended_use: '', country_of_origin: '' })
  const [result, setResult] = useState<ClassificationResult | null>(null)

  const mutation = useMutation({
    mutationFn: (body: Record<string, string>) => api.post('/classification', body),
    onSuccess: (res) => {
      setResult(res.data)
      const code = res.data.hs_code_6digit
      const conf = Math.round((res.data.confidence || 0) * 100)
      if (code && code !== '000000') {
        toast(`Classified as HS ${formatHSCode(code)} with ${conf}% confidence`, 'success')
      } else {
        toast('Classification returned low confidence — manual review required', 'warning')
      }
    },
    onError: () => toast('Classification failed — please try again', 'error'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const body: Record<string, string> = { product_description: form.product_description }
    if (form.materials) body.materials = form.materials
    if (form.intended_use) body.intended_use = form.intended_use
    if (form.country_of_origin) body.country_of_origin = form.country_of_origin
    mutation.mutate(body)
  }

  const isPending = mutation.isPending

  return (
    <div className="p-4 sm:p-8 space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">HS Code Classification</h2>
        <p className="text-gray-500 mt-1">AI-powered classification using WCO GRI rules 1–6</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <div className="xl:col-span-2">
      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Product Description *</label>
          <textarea rows={3}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            value={form.product_description}
            onChange={(e) => setForm({ ...form, product_description: e.target.value })}
            placeholder="Describe the product in detail, e.g. Industrial hydraulic pump, cast iron housing, stainless steel shaft, 250 bar rated operating pressure"
            required
          />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Materials/Composition</label>
            <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              value={form.materials} onChange={(e) => setForm({ ...form, materials: e.target.value })}
              placeholder="e.g., 100% cotton, cast iron, PTFE" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Intended Use</label>
            <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              value={form.intended_use} onChange={(e) => setForm({ ...form, intended_use: e.target.value })}
              placeholder="e.g., industrial fluid transfer" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Country of Origin</label>
            <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              value={form.country_of_origin} onChange={(e) => setForm({ ...form, country_of_origin: e.target.value })}
              placeholder="e.g., CN" maxLength={3} />
          </div>
        </div>
        <button type="submit" disabled={isPending}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-60 transition-colors">
          <Tag size={16} />
          {isPending ? 'Classifying...' : 'Classify Product'}
        </button>
      </form>
      </div>

      {/* Help panel — fills whitespace */}
      <div className="space-y-4">
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
          <h3 className="font-semibold text-blue-900 flex items-center gap-2 text-sm mb-3">
            <Info size={15} /> GRI Classification Rules
          </h3>
          <ol className="space-y-1.5 text-xs text-blue-800">
            {[
              ['GRI 1', 'Headings and section/chapter notes'],
              ['GRI 2', 'Incomplete articles and mixtures'],
              ['GRI 3', 'Most specific description wins'],
              ['GRI 4', 'Most akin goods'],
              ['GRI 5', 'Packing materials and containers'],
              ['GRI 6', 'Subheading comparison (same level)'],
            ].map(([rule, desc]) => (
              <li key={rule} className="flex gap-2">
                <span className="font-bold shrink-0 text-blue-700">{rule}:</span>
                <span>{desc}</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="bg-amber-50 border border-amber-100 rounded-xl p-5">
          <h3 className="font-semibold text-amber-900 text-sm mb-2">ITAR/EAR Flags</h3>
          <p className="text-xs text-amber-800 leading-relaxed">
            Certain HS codes trigger automatic ITAR (International Traffic in Arms Regulations)
            or EAR (Export Administration Regulations) review flags. A positive flag does not
            block the shipment — it requires export license verification before filing.
          </p>
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
          <h3 className="font-semibold text-gray-800 text-sm mb-2">Jurisdictions Covered</h3>
          <ul className="space-y-1 text-xs text-gray-600">
            <li>• WCO HS 2022 (6-digit universal)</li>
            <li>• US HTS (10-digit, Schedule B)</li>
            <li>• EU TARIC (10-digit)</li>
            <li>• UK Global Tariff (10-digit)</li>
          </ul>
        </div>
      </div>
      </div>

      {isPending && (
        <AIThinking label="Running GRI analysis using WCO Harmonized System 2022..." />
      )}

      {result && !isPending && (
        <div className="bg-white rounded-xl shadow-sm p-6 space-y-5">
          <div className="flex items-center gap-3 flex-wrap">
            <CheckCircle2 className="text-green-500" size={22} />
            <h3 className="text-lg font-semibold text-gray-900">Classification Result</h3>
            {result.is_itar_ear_flagged === 'true' && (
              <span className="flex items-center gap-1 bg-red-100 text-red-700 px-3 py-1 rounded-full text-xs font-medium border border-red-200">
                <AlertTriangle size={12} /> ITAR/EAR Flagged — Review export controls
              </span>
            )}
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'WCO HS Code (6-digit)', value: formatHSCode(result.hs_code_6digit) },
              { label: 'US HTS (10-digit)', value: result.hs_code_us_hts ? formatHSCode(result.hs_code_us_hts) : '—' },
              { label: 'EU TARIC (10-digit)', value: result.hs_code_eu_taric ? formatHSCode(result.hs_code_eu_taric) : '—' },
              { label: 'UK Global Tariff', value: result.hs_code_uk_gt ? formatHSCode(result.hs_code_uk_gt) : '—' },
            ].map(({ label, value }) => (
              <div key={label} className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500 mb-1">{label}</p>
                <p className="font-mono font-bold text-gray-900 text-lg">{value}</p>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-4">
            <div>
              <p className="text-xs text-gray-500">Confidence</p>
              <p className="text-xl font-bold text-gray-900">{formatPct(result.confidence)}</p>
            </div>
            <div className="flex-1 bg-gray-200 rounded-full h-2.5">
              <div
                className={`h-2.5 rounded-full transition-all ${result.confidence >= 0.8 ? 'bg-green-500' : result.confidence >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'}`}
                style={{ width: `${(result.confidence || 0) * 100}%` }}
              />
            </div>
            {result.gri_rules_applied && result.gri_rules_applied.length > 0 && (
              <div>
                <p className="text-xs text-gray-500">GRI Rules</p>
                <p className="text-sm font-medium text-blue-700">{result.gri_rules_applied.map(r => `GRI ${r}`).join(', ')}</p>
              </div>
            )}
          </div>

          {(result.duty_rate_us !== null || result.duty_rate_eu !== null) && (
            <div className="grid grid-cols-2 gap-3 text-sm">
              {result.duty_rate_us !== null && (
                <div className="bg-blue-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">US MFN Duty Rate</p>
                  <p className="font-bold text-blue-700 text-lg">{formatPct(result.duty_rate_us)}</p>
                </div>
              )}
              {result.duty_rate_eu !== null && (
                <div className="bg-blue-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">EU Duty Rate</p>
                  <p className="font-bold text-blue-700 text-lg">{formatPct(result.duty_rate_eu)}</p>
                </div>
              )}
            </div>
          )}

          {result.gpt_reasoning && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">GRI Analysis Reasoning</p>
              <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700 leading-relaxed whitespace-pre-wrap border border-gray-200">
                {result.gpt_reasoning}
              </div>
            </div>
          )}

          {result.top_candidates && result.top_candidates.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Alternative Candidates (confidence &lt; 85%)</p>
              <div className="space-y-2">
                {result.top_candidates.map((c, i) => (
                  <div key={i} className="flex items-center gap-3 bg-yellow-50 rounded-lg p-3 border border-yellow-200">
                    <span className="font-mono text-sm font-bold text-gray-800">{formatHSCode(c.hs_code)}</span>
                    <span className="flex-1 text-sm text-gray-600">{c.description}</span>
                    <span className="text-xs text-gray-500 font-medium">{formatPct(c.confidence)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
