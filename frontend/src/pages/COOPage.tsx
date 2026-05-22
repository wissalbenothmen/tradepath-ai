import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Award, Download, Printer, Globe, CheckCircle2 } from 'lucide-react'
import api from '../api'
import AIThinking from '../components/AIThinking'
import ShipmentSelector from '../components/ShipmentSelector'
import { toast } from '../components/Toast'
import { formatUSD } from '../utils/format'

interface COOResult {
  id: string; coo_format: string; origin_criterion: string; fta_agreement: string | null;
  country_of_origin: string; origin_analysis: string | null; rvc_percentage: number | null;
  preferential_duty_saving_usd: number | null; document_content: string | null; is_certified: string;
}

/** Parse the raw document_content text and render as structured COO certificate */
function CertificateDocument({ content, result, exporter, importer }: {
  content: string; result: COOResult; exporter: string; importer: string
}) {
  const today = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })

  return (
    <div className="border-2 border-gray-300 rounded-xl overflow-hidden print:border-black" id="coo-document">
      {/* Header */}
      <div className="bg-blue-800 text-white px-8 py-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Globe size={28} className="opacity-80" />
          <div>
            <h2 className="text-lg font-bold tracking-wide uppercase">Certificate of Origin</h2>
            <p className="text-blue-200 text-sm">{result.coo_format.replace(/_/g, ' ').toUpperCase()} · TradePath AI Verified</p>
          </div>
        </div>
        <div className="text-right text-sm">
          <p className="text-blue-200">Certificate No.</p>
          <p className="font-mono font-bold">{result.id.slice(0, 8).toUpperCase()}</p>
        </div>
      </div>

      {/* Key metadata row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-0 divide-x divide-y divide-gray-200 border-b border-gray-200">
        <div className="px-5 py-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Format</p>
          <p className="font-semibold text-gray-900 mt-0.5">{result.coo_format.replace(/_/g, ' ').toUpperCase()}</p>
        </div>
        <div className="px-5 py-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Country of Origin</p>
          <p className="font-semibold text-gray-900 mt-0.5">{result.country_of_origin}</p>
        </div>
        <div className="px-5 py-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Origin Criterion</p>
          <p className="font-semibold text-gray-900 mt-0.5 capitalize">{result.origin_criterion.replace(/_/g, ' ')}</p>
        </div>
        <div className="px-5 py-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Issue Date</p>
          <p className="font-semibold text-gray-900 mt-0.5">{today}</p>
        </div>
      </div>

      {/* Parties */}
      <div className="grid grid-cols-1 sm:grid-cols-2 divide-x divide-gray-200 border-b border-gray-200">
        <div className="px-6 py-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">1. Exporter / Producer</p>
          <p className="font-semibold text-gray-900">{exporter || '—'}</p>
          <p className="text-xs text-gray-400 mt-1">Country: {result.country_of_origin}</p>
        </div>
        <div className="px-6 py-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">2. Importer / Consignee</p>
          <p className="font-semibold text-gray-900">{importer || '—'}</p>
        </div>
      </div>

      {/* FTA & RVC */}
      {(result.fta_agreement || result.rvc_percentage !== null) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 divide-x divide-gray-200 border-b border-gray-200">
          {result.fta_agreement && (
            <div className="px-6 py-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">3. FTA Agreement</p>
              <p className="font-semibold text-blue-700">{result.fta_agreement}</p>
            </div>
          )}
          {result.rvc_percentage !== null && (
            <div className="px-6 py-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">4. Regional Value Content (RVC)</p>
              <div className="flex items-center gap-3">
                <p className="text-2xl font-bold text-blue-700">{result.rvc_percentage}%</p>
                <div className="flex-1 bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${result.rvc_percentage >= 60 ? 'bg-green-500' : result.rvc_percentage >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${Math.min(100, result.rvc_percentage)}%` }}
                  />
                </div>
              </div>
              <p className="text-xs text-gray-400 mt-1">{result.rvc_percentage >= 60 ? 'Meets preferential threshold' : 'Below standard threshold'}</p>
            </div>
          )}
        </div>
      )}

      {/* Duty saving callout */}
      {result.preferential_duty_saving_usd !== null && result.preferential_duty_saving_usd > 0 && (
        <div className="mx-6 my-4 bg-green-50 border border-green-200 rounded-lg px-5 py-3 flex items-center gap-3">
          <CheckCircle2 className="text-green-600 shrink-0" size={18} />
          <div>
            <p className="text-sm font-semibold text-green-800">Estimated Preferential Duty Saving</p>
            <p className="text-2xl font-bold text-green-700">{formatUSD(result.preferential_duty_saving_usd)}</p>
          </div>
        </div>
      )}

      {/* AI Origin Analysis */}
      {result.origin_analysis && (
        <div className="px-6 py-4 border-t border-gray-200">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">5. AI Origin Analysis</p>
          <p className="text-sm text-gray-700 leading-relaxed">{result.origin_analysis}</p>
        </div>
      )}

      {/* Raw document if provided — shown in a readable preformatted block */}
      {content && (
        <details className="border-t border-gray-200">
          <summary className="px-6 py-3 text-xs text-gray-500 cursor-pointer hover:bg-gray-50 select-none uppercase tracking-wide">
            6. Full Certificate Text (click to expand)
          </summary>
          <pre className="px-6 pb-5 text-xs text-gray-700 whitespace-pre-wrap leading-relaxed font-mono bg-gray-50">
            {content}
          </pre>
        </details>
      )}

      {/* Signature block */}
      <div className="border-t-2 border-gray-300 grid grid-cols-2 divide-x divide-gray-300">
        <div className="px-6 py-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-6">Authorized Signatory</p>
          <div className="border-b border-gray-400 mb-1 w-48" />
          <p className="text-xs text-gray-400">Signature &amp; Date</p>
        </div>
        <div className="px-6 py-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-6">Issuing Authority</p>
          <div className="border-b border-gray-400 mb-1 w-48" />
          <p className="text-xs text-gray-400">Stamp &amp; Date</p>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-gray-50 border-t border-gray-200 px-6 py-2 flex items-center justify-between text-xs text-gray-400">
        <span>Generated by TradePath AI · AI-Verified Certificate</span>
        <span>ID: {result.id.slice(0, 8).toUpperCase()}</span>
      </div>
    </div>
  )
}

export default function COOPage() {
  const [form, setForm] = useState({
    shipment_id: '', coo_format: 'usmca', fta_agreement: '',
    exporter_name: '', importer_name: '', country_of_origin: '',
    transaction_value_usd: '', non_originating_materials_usd: '',
  })
  const [result, setResult] = useState<COOResult | null>(null)

  const mutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/coo', body),
    onSuccess: (res) => {
      setResult(res.data)
      const rvc = res.data.rvc_percentage
      const saving = res.data.preferential_duty_saving_usd
      if (rvc !== null) {
        toast(`Certificate of Origin generated — RVC ${rvc}%${saving ? `, duty saving ${formatUSD(saving)}` : ''}`, 'success')
      } else {
        toast('Certificate of Origin generated successfully', 'success')
      }
    },
    onError: () => toast('Failed to generate Certificate of Origin — please try again', 'error'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const body: Record<string, unknown> = {
      shipment_id: form.shipment_id,
      coo_format: form.coo_format,
      exporter_name: form.exporter_name,
      importer_name: form.importer_name,
      country_of_origin: form.country_of_origin,
    }
    if (form.fta_agreement) body.fta_agreement = form.fta_agreement
    if (form.transaction_value_usd) body.transaction_value_usd = parseFloat(form.transaction_value_usd)
    if (form.non_originating_materials_usd) body.non_originating_materials_usd = parseFloat(form.non_originating_materials_usd)
    mutation.mutate(body)
  }

  const handlePrint = () => window.print()

  return (
    <div className="p-4 sm:p-8 space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Certificate of Origin</h2>
        <p className="text-gray-500 mt-1">Generate Form A (GSP) · EUR.1 · USMCA · Bilateral COOs with AI origin analysis</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Form panel */}
        <div className="xl:col-span-2">
          <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm p-6 space-y-4">
            <h3 className="font-semibold text-gray-800 text-sm uppercase tracking-wide text-gray-500">COO Details</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <ShipmentSelector
                value={form.shipment_id}
                onChange={(id) => setForm({ ...form, shipment_id: id })}
                required
                label="Linked Shipment"
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">COO Format</label>
                <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  value={form.coo_format} onChange={(e) => setForm({ ...form, coo_format: e.target.value })}>
                  {[['form_a_gsp', 'Form A (GSP)'], ['eur1', 'EUR.1'], ['usmca', 'USMCA'], ['bilateral', 'Bilateral'], ['generic', 'Generic']].map(([v, l]) => (
                    <option key={v} value={v}>{l}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Exporter Name <span className="text-red-500">*</span></label>
                <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  value={form.exporter_name} onChange={(e) => setForm({ ...form, exporter_name: e.target.value })} required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Importer Name <span className="text-red-500">*</span></label>
                <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  value={form.importer_name} onChange={(e) => setForm({ ...form, importer_name: e.target.value })} required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Country of Origin <span className="text-red-500">*</span></label>
                <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  value={form.country_of_origin} onChange={(e) => setForm({ ...form, country_of_origin: e.target.value })}
                  placeholder="MX" maxLength={3} required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">FTA Agreement</label>
                <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  value={form.fta_agreement} onChange={(e) => setForm({ ...form, fta_agreement: e.target.value })}
                  placeholder="e.g., USMCA" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Transaction Value (USD)</label>
                <input type="number" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  value={form.transaction_value_usd} onChange={(e) => setForm({ ...form, transaction_value_usd: e.target.value })} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Non-Originating Materials (USD)</label>
                <input type="number" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  value={form.non_originating_materials_usd} onChange={(e) => setForm({ ...form, non_originating_materials_usd: e.target.value })} />
              </div>
            </div>
            <button type="submit" disabled={mutation.isPending}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-60">
              <Award size={16} />
              {mutation.isPending ? 'Generating COO...' : 'Generate Certificate of Origin'}
            </button>
          </form>
        </div>

        {/* Help panel — fills whitespace */}
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-5 space-y-3">
            <h3 className="font-semibold text-blue-900 flex items-center gap-2">
              <Award size={16} /> Supported COO Formats
            </h3>
            <ul className="space-y-2 text-sm text-blue-800">
              {[
                ['Form A (GSP)', 'Generalized System of Preferences — for developing countries'],
                ['EUR.1', 'EU movement certificate — EU FTA partners'],
                ['USMCA', 'US-Mexico-Canada Agreement origin certification'],
                ['Bilateral', 'Country-specific bilateral FTA certificate'],
                ['Generic', 'Universal format for non-specific requirements'],
              ].map(([fmt, desc]) => (
                <li key={fmt} className="flex flex-col">
                  <span className="font-medium">{fmt}</span>
                  <span className="text-blue-600 text-xs">{desc}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-amber-50 border border-amber-100 rounded-xl p-5">
            <h3 className="font-semibold text-amber-900 text-sm mb-2">RVC Thresholds</h3>
            <ul className="space-y-1 text-xs text-amber-800">
              <li>• USMCA: 60% RVC (net cost) or 75% (transaction value)</li>
              <li>• EU FTAs: typically 40–60% depending on product</li>
              <li>• ASEAN: 40% RVC minimum for most goods</li>
            </ul>
          </div>
        </div>
      </div>

      {mutation.isPending && (
        <AIThinking label="Calculating Regional Value Content and generating Certificate of Origin..." />
      )}

      {result && !mutation.isPending && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Certificate of Origin — Preview</h3>
            <div className="flex gap-2">
              <button
                onClick={handlePrint}
                className="flex items-center gap-1.5 border border-gray-300 text-gray-700 px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-gray-50"
              >
                <Printer size={14} /> Print
              </button>
              <button
                onClick={handlePrint}
                className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-xs font-medium"
              >
                <Download size={14} /> Export PDF
              </button>
            </div>
          </div>
          <CertificateDocument
            content={result.document_content || ''}
            result={result}
            exporter={form.exporter_name}
            importer={form.importer_name}
          />
        </div>
      )}
    </div>
  )
}
