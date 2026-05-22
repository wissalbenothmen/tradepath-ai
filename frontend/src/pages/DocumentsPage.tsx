import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { FolderOpen, Upload, CheckCircle2, XCircle, FileText } from 'lucide-react'
import api from '../api'
import AIThinking from '../components/AIThinking'
import ShipmentSelector from '../components/ShipmentSelector'
import { toast } from '../components/Toast'
import { formatUSD } from '../utils/format'

interface DocumentResult {
  id: string; document_type: string; filename: string; processing_status: string;
  ocr_confidence: number | null;
  ocr_extracted: {
    vendor_name: string | null; customer_name: string | null; invoice_number: string | null;
    total_amount: number | null; currency: string | null; total_amount_usd: number | null;
    line_items: { description: string; quantity: number | null; amount: number | null }[];
  } | null;
}

const ACCEPTED_TYPES = [
  ['Commercial Invoice', 'commercial_invoice'],
  ['Packing List', 'packing_list'],
  ['Bill of Lading', 'bill_of_lading'],
  ['Airway Bill', 'airway_bill'],
  ['Certificate of Origin', 'certificate_of_origin'],
  ['Import License', 'import_license'],
  ['Export License', 'export_license'],
  ['Other', 'other'],
]

export default function DocumentsPage() {
  const [shipmentId, setShipmentId] = useState('')
  const [docType, setDocType] = useState('commercial_invoice')
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<DocumentResult | null>(null)

  const mutation = useMutation({
    mutationFn: (formData: FormData) => api.post('/documents', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
    onSuccess: (res) => {
      setResult(res.data)
      const conf = res.data.ocr_confidence
      const confPct = conf ? `${Math.round(conf * 100)}%` : ''
      if (res.data.processing_status === 'completed') {
        toast(`Document processed successfully${confPct ? ` — OCR confidence ${confPct}` : ''}`, 'success')
      } else {
        toast('Document upload failed during processing', 'error')
      }
    },
    onError: () => toast('Document upload failed — please try again', 'error'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return
    const fd = new FormData()
    fd.append('shipment_id', shipmentId)
    fd.append('document_type', docType)
    fd.append('file', file)
    mutation.mutate(fd)
  }

  return (
    <div className="p-4 sm:p-8 space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Trade Documents</h2>
        <p className="text-gray-500 mt-1">Upload commercial invoices, packing lists, bills of lading with Azure DI OCR extraction</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-4">
          <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm p-6 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <ShipmentSelector
                value={shipmentId}
                onChange={setShipmentId}
                required
                label="Linked Shipment"
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Document Type</label>
                <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  value={docType} onChange={(e) => setDocType(e.target.value)}>
                  {ACCEPTED_TYPES.map(([label, value]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-blue-400 transition-colors">
              <input type="file" accept=".pdf,.png,.jpg,.jpeg,.tiff" className="hidden" id="file-upload"
                onChange={(e) => setFile(e.target.files?.[0] || null)} />
              <label htmlFor="file-upload" className="cursor-pointer block">
                <Upload className="mx-auto text-gray-400 mb-3" size={32} />
                {file ? (
                  <div>
                    <p className="text-sm font-medium text-blue-600">{file.name}</p>
                    <p className="text-xs text-gray-400 mt-1">{(file.size / 1024).toFixed(0)} KB · Click to change</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-medium text-gray-600">Click to upload or drag &amp; drop</p>
                    <p className="text-xs text-gray-400 mt-1">PDF, PNG, JPG, TIFF — max 10 MB</p>
                  </div>
                )}
              </label>
            </div>
            <button type="submit" disabled={mutation.isPending || !file}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-60">
              <FolderOpen size={16} />
              {mutation.isPending ? 'Processing with Azure DI OCR...' : 'Upload & Extract'}
            </button>
          </form>

          {mutation.isPending && (
            <AIThinking label="Extracting fields with Azure Document Intelligence OCR..." />
          )}

          {result && !mutation.isPending && (
            <div className="bg-white rounded-xl shadow-sm p-6 space-y-5">
              <div className="flex items-center gap-3">
                {result.processing_status === 'completed' ? (
                  <CheckCircle2 className="text-green-500" size={22} />
                ) : (
                  <XCircle className="text-red-500" size={22} />
                )}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">{result.filename}</h3>
                  <p className="text-sm text-gray-500 capitalize">{result.document_type.replace(/_/g, ' ')} · Status: {result.processing_status}</p>
                </div>
                {result.ocr_confidence !== null && (
                  <div className="ml-auto bg-blue-50 px-3 py-1.5 rounded-lg">
                    <p className="text-xs text-gray-500">OCR Confidence</p>
                    <p className="text-sm font-bold text-blue-700">{((result.ocr_confidence || 0) * 100).toFixed(0)}%</p>
                  </div>
                )}
              </div>

              {result.ocr_extracted && (
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
                  {[
                    { label: 'Vendor', value: result.ocr_extracted.vendor_name },
                    { label: 'Customer', value: result.ocr_extracted.customer_name },
                    { label: 'Invoice #', value: result.ocr_extracted.invoice_number },
                    { label: 'Total Amount', value: result.ocr_extracted.total_amount ? `${formatUSD(result.ocr_extracted.total_amount)} ${result.ocr_extracted.currency || 'USD'}` : null },
                    { label: 'Total (USD)', value: result.ocr_extracted.total_amount_usd ? formatUSD(result.ocr_extracted.total_amount_usd) : null },
                  ].filter((f) => f.value).map(({ label, value }) => (
                    <div key={label} className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-500">{label}</p>
                      <p className="font-medium">{value}</p>
                    </div>
                  ))}
                </div>
              )}

              {result.ocr_extracted?.line_items && result.ocr_extracted.line_items.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2">Extracted Line Items</p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs border border-gray-200 rounded-lg overflow-hidden">
                      <thead className="bg-gray-50 border-b border-gray-200">
                        <tr>
                          <th className="px-3 py-2 text-left text-gray-600 font-semibold">Description</th>
                          <th className="px-3 py-2 text-right text-gray-600 font-semibold">Qty</th>
                          <th className="px-3 py-2 text-right text-gray-600 font-semibold">Amount</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {result.ocr_extracted.line_items.map((item, i) => (
                          <tr key={i}>
                            <td className="px-3 py-2 text-gray-700">{item.description}</td>
                            <td className="px-3 py-2 text-right tabular-nums text-gray-600">{item.quantity ?? '—'}</td>
                            <td className="px-3 py-2 text-right tabular-nums text-gray-700">{item.amount != null ? formatUSD(item.amount) : '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Help panel */}
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
            <h3 className="font-semibold text-blue-900 text-sm flex items-center gap-2 mb-3">
              <FileText size={15} /> Supported Document Types
            </h3>
            <ul className="space-y-2 text-xs text-blue-800">
              {ACCEPTED_TYPES.slice(0, 6).map(([label]) => (
                <li key={label} className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
                  {label}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-amber-50 border border-amber-100 rounded-xl p-5">
            <h3 className="font-semibold text-amber-900 text-sm mb-2">OCR Extraction</h3>
            <p className="text-xs text-amber-800 leading-relaxed mb-2">
              Azure Document Intelligence automatically extracts:
            </p>
            <ul className="space-y-1 text-xs text-amber-800">
              <li>• Vendor &amp; customer names</li>
              <li>• Invoice number &amp; dates</li>
              <li>• Line items with quantities</li>
              <li>• Total amounts &amp; currency</li>
              <li>• Port codes &amp; Incoterms</li>
            </ul>
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
            <h3 className="font-semibold text-gray-800 text-sm mb-2">File Requirements</h3>
            <ul className="space-y-1 text-xs text-gray-600">
              <li>• Formats: PDF, PNG, JPG, TIFF</li>
              <li>• Max size: 10 MB per file</li>
              <li>• Best results: scanned at 300 DPI</li>
              <li>• Text must be machine-readable</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
