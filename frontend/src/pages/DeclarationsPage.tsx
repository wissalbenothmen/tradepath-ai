import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { FileText, AlertCircle, Info } from 'lucide-react'
import api from '../api'
import Badge, { statusVariant } from '../components/Badge'
import AIThinking from '../components/AIThinking'
import ShipmentSelector from '../components/ShipmentSelector'
import { toast } from '../components/Toast'
import { formatUSD } from '../utils/format'

interface Declaration {
  id: string; declaration_type: string; status: string; port_of_entry: string | null;
  declared_value_usd: number | null; total_duty_usd: number | null; total_tax_usd: number | null;
  inconsistencies: { field: string; issue: string; severity: string }[] | null;
  gpt_validation_notes: string | null; edi_content: string | null;
}

export default function DeclarationsPage() {
  const [form, setForm] = useState({
    shipment_id: '', declaration_type: 'cbp_entry_01', port_of_entry: '',
    declared_value_usd: '', cif_value_usd: '', fob_value_usd: '',
  })
  const [declaration, setDeclaration] = useState<Declaration | null>(null)
  const [showEDI, setShowEDI] = useState(false)

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/declarations', body),
    onSuccess: (res) => {
      setDeclaration(res.data)
      toast(`Declaration ${res.data.declaration_type.toUpperCase().replace(/_/g, ' ')} created successfully`, 'success')
    },
    onError: () => toast('Failed to create declaration — please try again', 'error'),
  })
  const validateMutation = useMutation({
    mutationFn: (id: string) => api.post(`/declarations/${id}/validate`),
    onSuccess: (res) => {
      setDeclaration(res.data)
      const issues = res.data.inconsistencies?.length || 0
      if (issues === 0) {
        toast('Declaration validated — no inconsistencies found', 'success')
      } else {
        toast(`Validation found ${issues} issue${issues > 1 ? 's' : ''} — review required`, 'warning')
      }
    },
    onError: () => toast('Validation failed — please try again', 'error'),
  })
  const ediMutation = useMutation({
    mutationFn: (id: string) => api.post(`/declarations/${id}/generate-edi`),
    onSuccess: (res) => {
      setDeclaration(res.data)
      setShowEDI(true)
      toast('EDI document generated successfully', 'success')
    },
    onError: () => toast('EDI generation failed — please try again', 'error'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const body: Record<string, unknown> = {
      shipment_id: form.shipment_id,
      declaration_type: form.declaration_type,
    }
    if (form.port_of_entry) body.port_of_entry = form.port_of_entry
    if (form.declared_value_usd) body.declared_value_usd = parseFloat(form.declared_value_usd)
    if (form.cif_value_usd) body.cif_value_usd = parseFloat(form.cif_value_usd)
    if (form.fob_value_usd) body.fob_value_usd = parseFloat(form.fob_value_usd)
    createMutation.mutate(body)
  }

  return (
    <div className="p-4 sm:p-8 space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Customs Declarations</h2>
        <p className="text-gray-500 mt-1">CBP Entry 01 (US) · EU SAD · UK C88 · AES Filing with EDI generation</p>
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
            <label className="block text-sm font-medium text-gray-700 mb-1">Declaration Type</label>
            <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              value={form.declaration_type} onChange={(e) => setForm({ ...form, declaration_type: e.target.value })}>
              {[['cbp_entry_01', 'CBP Entry Type 01 (US Formal)'], ['eu_sad', 'EU SAD'], ['uk_c88', 'UK C88'], ['aes_filing', 'AES Filing']].map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Port of Entry</label>
            <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              value={form.port_of_entry} onChange={(e) => setForm({ ...form, port_of_entry: e.target.value })} placeholder="USNYC" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Declared Value (USD)</label>
            <input type="number" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              value={form.declared_value_usd} onChange={(e) => setForm({ ...form, declared_value_usd: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">CIF Value (USD)</label>
            <input type="number" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              value={form.cif_value_usd} onChange={(e) => setForm({ ...form, cif_value_usd: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">FOB Value (USD)</label>
            <input type="number" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              value={form.fob_value_usd} onChange={(e) => setForm({ ...form, fob_value_usd: e.target.value })} />
          </div>
        </div>
        <button type="submit" disabled={createMutation.isPending}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-60">
          <FileText size={16} />
          {createMutation.isPending ? 'Creating...' : 'Create Declaration'}
        </button>
      </form>
        </div>

        {/* Help panel */}
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-5 space-y-3">
            <h3 className="font-semibold text-blue-900 flex items-center gap-2 text-sm">
              <Info size={15} /> Declaration Types
            </h3>
            <ul className="space-y-2 text-xs text-blue-800">
              {[
                ['CBP Entry Type 01', 'US formal customs entry for commercial imports'],
                ['EU SAD', 'Single Administrative Document for EU customs clearance'],
                ['UK C88', 'UK customs entry declaration (post-Brexit)'],
                ['AES Filing', 'Automated Export System filing for US export control'],
              ].map(([type, desc]) => (
                <li key={type} className="flex flex-col gap-0.5">
                  <span className="font-semibold">{type}</span>
                  <span className="text-blue-600">{desc}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-green-50 border border-green-100 rounded-xl p-5">
            <h3 className="font-semibold text-green-900 text-sm mb-2">Workflow Steps</h3>
            <ol className="space-y-2 text-xs text-green-800">
              <li className="flex gap-2"><span className="font-bold shrink-0">1.</span> Create the declaration with shipment values</li>
              <li className="flex gap-2"><span className="font-bold shrink-0">2.</span> Run AI Validate to check for inconsistencies</li>
              <li className="flex gap-2"><span className="font-bold shrink-0">3.</span> Generate EDI for electronic filing</li>
            </ol>
          </div>
        </div>
      </div>

      {createMutation.isPending && (
        <AIThinking label="Creating customs declaration..." />
      )}
      {validateMutation.isPending && (
        <AIThinking label="Running AI validation — checking field consistency, value logic, and port codes..." />
      )}
      {ediMutation.isPending && (
        <AIThinking label="Generating EDI document..." />
      )}

      {declaration && (
        <div className="bg-white rounded-xl shadow-sm p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileText className="text-blue-500" size={22} />
              <h3 className="text-lg font-semibold text-gray-900">{declaration.declaration_type.toUpperCase().replace(/_/g, ' ')}</h3>
              <Badge label={declaration.status} variant={statusVariant(declaration.status)} />
            </div>
            <div className="flex gap-2">
              <button onClick={() => validateMutation.mutate(declaration.id)} disabled={validateMutation.isPending}
                className="border border-blue-300 text-blue-700 px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-blue-50 disabled:opacity-60">
                {validateMutation.isPending ? 'Validating...' : 'AI Validate'}
              </button>
              <button onClick={() => ediMutation.mutate(declaration.id)} disabled={ediMutation.isPending}
                className="border border-gray-300 text-gray-700 px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-gray-50 disabled:opacity-60">
                {ediMutation.isPending ? 'Generating...' : 'Generate EDI'}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 text-sm">
            {declaration.total_duty_usd !== null && (
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">Total Duty</p>
                <p className="font-bold">{formatUSD(declaration.total_duty_usd)}</p>
              </div>
            )}
            {declaration.total_tax_usd !== null && (
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">Total Tax/VAT</p>
                <p className="font-bold">{formatUSD(declaration.total_tax_usd)}</p>
              </div>
            )}
          </div>

          {declaration.inconsistencies && declaration.inconsistencies.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Validation Issues</p>
              <div className="space-y-2">
                {declaration.inconsistencies.map((inc, i) => (
                  <div key={i} className={`rounded-lg p-3 flex items-start gap-2 ${inc.severity === 'error' ? 'bg-red-50 border border-red-200' : 'bg-yellow-50 border border-yellow-200'}`}>
                    <AlertCircle size={14} className={inc.severity === 'error' ? 'text-red-500 mt-0.5' : 'text-yellow-500 mt-0.5'} />
                    <div>
                      <span className="text-xs font-medium">{inc.field}:</span>
                      <span className="text-xs text-gray-700 ml-1">{inc.issue}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {declaration.gpt_validation_notes && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">AI Validation Notes</p>
              <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700">{declaration.gpt_validation_notes}</div>
            </div>
          )}

          {showEDI && declaration.edi_content && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">EDI Content</p>
              <pre className="bg-gray-900 text-green-400 rounded-lg p-4 text-xs overflow-x-auto font-mono">
                {declaration.edi_content}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
