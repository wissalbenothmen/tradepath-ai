import { Search, Sparkles, ArrowRight, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

interface Command {
  id: string
  label: string
  hint?: string
  path?: string
  action?: () => void
  group: 'Navigate' | 'AI' | 'Action'
}

interface Props {
  open: boolean
  onClose: () => void
}

export default function CommandPalette({ open, onClose }: Props) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [activeIdx, setActiveIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement | null>(null)

  const commands: Command[] = useMemo(() => [
    { id: 'nav-dashboard', label: 'Go to Dashboard', path: '/dashboard', group: 'Navigate', hint: 'Compliance overview' },
    { id: 'nav-shipments', label: 'Open Shipments', path: '/shipments', group: 'Navigate' },
    { id: 'nav-classification', label: 'Run HS Classification', path: '/classification', group: 'Navigate', hint: 'WCO GRI 1–6' },
    { id: 'nav-screening', label: 'Sanctions Screening', path: '/screening', group: 'Navigate', hint: 'OFAC · BIS · EU · UN' },
    { id: 'nav-declarations', label: 'Customs Declarations', path: '/declarations', group: 'Navigate' },
    { id: 'nav-coo', label: 'Generate Certificate of Origin', path: '/coo', group: 'Navigate', hint: 'USMCA · EUR.1 · Form A' },
    { id: 'nav-fta', label: 'FTA Duty Analysis', path: '/fta', group: 'Navigate' },
    { id: 'nav-documents', label: 'Upload Document (OCR)', path: '/documents', group: 'Navigate', hint: 'Azure DI' },
    { id: 'nav-analytics', label: 'Open Analytics', path: '/analytics', group: 'Navigate' },
    { id: 'ai-ask', label: 'Ask AI about a shipment…', group: 'AI', hint: 'Streaming response · GPT-4.1 mini' },
    { id: 'ai-explain', label: 'Explain my last classification', group: 'AI', hint: 'GRI rule walk-through' },
    { id: 'ai-savings', label: 'Find more FTA duty savings', group: 'AI', hint: 'Cross-lane optimization' },
    { id: 'act-new', label: 'New shipment', path: '/shipments', group: 'Action' },
  ], [])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return commands
    return commands.filter((c) =>
      c.label.toLowerCase().includes(q) || (c.hint ?? '').toLowerCase().includes(q)
    )
  }, [commands, query])

  useEffect(() => {
    if (!open) return
    setQuery('')
    setActiveIdx(0)
    setTimeout(() => inputRef.current?.focus(), 30)
  }, [open])

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); onClose() }
      else if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActiveIdx((i) => Math.min(i + 1, filtered.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActiveIdx((i) => Math.max(i - 1, 0))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        const sel = filtered[activeIdx]
        if (sel) runCommand(sel)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, filtered, activeIdx])

  const runCommand = (c: Command) => {
    onClose()
    if (c.path) navigate(c.path)
    c.action?.()
  }

  if (!open) return null

  const grouped: Record<Command['group'], Command[]> = { Navigate: [], AI: [], Action: [] }
  filtered.forEach((c) => grouped[c.group].push(c))

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center pt-[15vh] px-4">
      <button
        className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
        aria-label="Close command palette"
      />
      <div className="relative w-full max-w-xl bg-white rounded-2xl shadow-soft-3 overflow-hidden animate-slide-in ring-1 ring-slate-200">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-100">
          <Search size={16} className="text-slate-400" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setActiveIdx(0) }}
            placeholder="Type a command, or ask AI…"
            className="flex-1 outline-none text-sm placeholder:text-slate-400"
          />
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600" aria-label="Close">
            <X size={16} />
          </button>
        </div>
        <div className="max-h-[60vh] overflow-y-auto py-2">
          {filtered.length === 0 && (
            <p className="px-4 py-8 text-center text-sm text-slate-500">No matching commands.</p>
          )}
          {(['Navigate', 'AI', 'Action'] as const).map((group) => {
            const items = grouped[group]
            if (items.length === 0) return null
            return (
              <div key={group} className="mb-2">
                <p className="px-4 py-1 text-2xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  {group === 'AI' && <Sparkles size={10} className="text-ai-500" />}
                  {group}
                </p>
                {items.map((c) => {
                  const idx = filtered.indexOf(c)
                  const active = idx === activeIdx
                  return (
                    <button
                      key={c.id}
                      onMouseEnter={() => setActiveIdx(idx)}
                      onClick={() => runCommand(c)}
                      className={`w-full flex items-center justify-between px-4 py-2 text-left text-sm transition-colors ${
                        active ? 'bg-brand-50 text-brand-900' : 'hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        {group === 'AI' && <Sparkles size={12} className="text-ai-500 shrink-0" />}
                        <span className="truncate">{c.label}</span>
                        {c.hint && <span className="text-2xs text-slate-400 truncate">{c.hint}</span>}
                      </div>
                      {active && <ArrowRight size={14} className="text-brand-500 shrink-0" />}
                    </button>
                  )
                })}
              </div>
            )
          })}
        </div>
        <div className="border-t border-slate-100 px-4 py-2 flex items-center gap-3 text-2xs text-slate-400 bg-slate-50">
          <span><kbd className="px-1 py-0.5 rounded bg-white border border-slate-200">↑↓</kbd> navigate</span>
          <span><kbd className="px-1 py-0.5 rounded bg-white border border-slate-200">↵</kbd> select</span>
          <span><kbd className="px-1 py-0.5 rounded bg-white border border-slate-200">esc</kbd> close</span>
        </div>
      </div>
    </div>
  )
}
