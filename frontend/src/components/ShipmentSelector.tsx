import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, Search, Ship } from 'lucide-react'
import api from '../api'

interface Shipment {
  id: string
  reference_number: string
  origin_country: string
  destination_country: string
  status: string
}

interface ShipmentSelectorProps {
  value: string
  onChange: (id: string) => void
  required?: boolean
  label?: string
}

const STATUS_COLORS: Record<string, string> = {
  cleared: 'bg-green-100 text-green-700',
  blocked: 'bg-red-100 text-red-700',
  hold: 'bg-orange-100 text-orange-700',
  screening: 'bg-yellow-100 text-yellow-700',
  draft: 'bg-gray-100 text-gray-600',
  filed: 'bg-purple-100 text-purple-700',
}

function statusBadge(status: string) {
  const cls = STATUS_COLORS[status.toLowerCase()] ?? 'bg-blue-100 text-blue-700'
  return (
    <span className={`text-xs font-medium px-1.5 py-0.5 rounded capitalize shrink-0 ${cls}`}>
      {status}
    </span>
  )
}

export default function ShipmentSelector({
  value,
  onChange,
  required = false,
  label = 'Shipment',
}: ShipmentSelectorProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  const { data: shipments = [], isLoading } = useQuery<Shipment[]>({
    queryKey: ['shipments'],
    queryFn: () => api.get('/shipments').then((r) => r.data),
  })

  const selected = shipments.find((s) => s.id === value) ?? null

  const filtered = search.trim()
    ? shipments.filter(
        (s) =>
          s.reference_number.toLowerCase().includes(search.toLowerCase()) ||
          s.origin_country.toLowerCase().includes(search.toLowerCase()) ||
          s.destination_country.toLowerCase().includes(search.toLowerCase()) ||
          s.status.toLowerCase().includes(search.toLowerCase())
      )
    : shipments

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
        setSearch('')
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Focus search when opening
  useEffect(() => {
    if (open) {
      setTimeout(() => searchRef.current?.focus(), 50)
    }
  }, [open])

  const handleSelect = (id: string) => {
    onChange(id)
    setOpen(false)
    setSearch('')
  }

  return (
    <div ref={containerRef} className="relative">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label} {required && <span className="text-red-500">*</span>}
      </label>

      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        disabled={isLoading}
        className={`w-full flex items-center justify-between border rounded-lg px-3 py-2 text-sm bg-white text-left transition-colors
          ${open ? 'border-blue-500 ring-2 ring-blue-100' : 'border-gray-300 hover:border-gray-400'}
          ${isLoading ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        {isLoading ? (
          <span className="text-gray-400">Loading shipments...</span>
        ) : selected ? (
          <span className="flex items-center gap-2 min-w-0">
            <Ship size={13} className="text-blue-500 shrink-0" />
            <span className="font-mono font-semibold text-blue-700 shrink-0">{selected.reference_number}</span>
            <span className="text-gray-400 text-xs truncate">{selected.origin_country} → {selected.destination_country}</span>
            {statusBadge(selected.status)}
          </span>
        ) : (
          <span className="text-gray-400">— Select a shipment —</span>
        )}
        <ChevronDown size={15} className={`text-gray-400 shrink-0 ml-2 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute z-50 mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
          {/* Search bar */}
          <div className="px-3 pt-2.5 pb-2 border-b border-gray-100">
            <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-2.5 py-1.5">
              <Search size={13} className="text-gray-400 shrink-0" />
              <input
                ref={searchRef}
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by reference, country, status..."
                className="w-full bg-transparent text-xs text-gray-700 placeholder-gray-400 focus:outline-none"
              />
            </div>
          </div>

          {/* Options list */}
          <ul className="max-h-60 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <li className="px-4 py-3 text-sm text-gray-400 text-center">No shipments match your search</li>
            ) : (
              filtered.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(s.id)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2.5 text-left hover:bg-blue-50 transition-colors
                      ${s.id === value ? 'bg-blue-50' : ''}`}
                  >
                    <Ship size={13} className="text-blue-400 shrink-0" />
                    <span className="font-mono font-semibold text-blue-700 text-xs shrink-0">{s.reference_number}</span>
                    <span className="text-xs text-gray-500 flex-1 truncate">{s.origin_country} → {s.destination_country}</span>
                    {statusBadge(s.status)}
                  </button>
                </li>
              ))
            )}
          </ul>

          {/* Footer count */}
          <div className="px-3 py-1.5 border-t border-gray-100 text-xs text-gray-400">
            {filtered.length} of {shipments.length} shipments
          </div>
        </div>
      )}

      {/* Hidden native input for form validation */}
      {required && (
        <input
          type="text"
          value={value}
          required
          readOnly
          tabIndex={-1}
          className="absolute inset-0 w-full opacity-0 pointer-events-none"
          aria-hidden="true"
        />
      )}
    </div>
  )
}
