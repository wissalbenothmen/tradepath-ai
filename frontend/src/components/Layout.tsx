import { useState, useEffect, useMemo } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  LayoutDashboard, Ship, Tag, ShieldAlert, FileText,
  Award, TrendingDown, FolderOpen, BarChart3, LogOut, Menu, X,
  Command as CommandIcon, Sparkles, Search,
} from 'lucide-react'
import { Toaster } from './Toast'
import CommandPalette from './CommandPalette'
import api, { endpoints, qk, logout as apiLogout } from '../api'

interface Me {
  id: string
  email: string
  full_name: string
  role: string
  company_id: string | null
}

const NAV_SECTIONS = [
  {
    title: 'Workflow',
    items: [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
      { to: '/shipments', icon: Ship, label: 'Shipments' },
    ],
  },
  {
    title: 'AI Compliance',
    items: [
      { to: '/classification', icon: Tag, label: 'HS Classification', ai: true },
      { to: '/screening', icon: ShieldAlert, label: 'Sanctions Screening', ai: true },
      { to: '/declarations', icon: FileText, label: 'Declarations' },
      { to: '/coo', icon: Award, label: 'Certificate of Origin' },
      { to: '/fta', icon: TrendingDown, label: 'FTA Analysis', ai: true },
      { to: '/documents', icon: FolderOpen, label: 'Documents (OCR)', ai: true },
    ],
  },
  {
    title: 'Insights',
    items: [
      { to: '/analytics', icon: BarChart3, label: 'Analytics' },
    ],
  },
] as const

export default function Layout() {
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)

  const { data: me } = useQuery<Me>({
    queryKey: qk.me(),
    queryFn: () => api.get(endpoints.auth.me).then((r) => r.data),
    staleTime: 5 * 60_000,
  })

  const logout = () => {
    apiLogout()
    navigate('/login')
  }
  const handleNavClick = () => {
    if (window.innerWidth < 768) setSidebarOpen(false)
  }

  // Cmd+K / Ctrl+K opens the palette; ESC closes the sidebar.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((v) => !v)
      } else if (e.key === 'Escape') {
        setSidebarOpen(false)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const initials = useMemo(() => {
    const name = me?.full_name || me?.email || '?'
    return name
      .split(/[\s@.]/)
      .filter(Boolean)
      .slice(0, 2)
      .map((s) => s[0]?.toUpperCase())
      .join('') || '?'
  }, [me])

  return (
    <div className="flex h-screen bg-surface-subtle overflow-hidden">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <button
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-20 md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close menu"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed md:static inset-y-0 left-0 z-30
          w-64 text-white flex flex-col
          transform transition-transform duration-200 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          md:translate-x-0
          bg-brand-950
        `}
        style={{ backgroundImage: 'linear-gradient(180deg, #0b1f4d 0%, #080f2b 100%)' }}
      >
        {/* Header / brand */}
        <div className="px-5 py-5 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-ai-gradient flex items-center justify-center shadow-ai-glow-soft">
              <Sparkles size={16} className="text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight leading-none">TradePath AI</h1>
              <p className="text-2xs text-brand-200 mt-0.5">Compliance OS · Beta</p>
            </div>
          </div>
          <button
            className="md:hidden text-brand-200 hover:text-white"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>

        {/* Cmd+K launcher */}
        <button
          onClick={() => setPaletteOpen(true)}
          className="mx-3 mt-3 flex items-center justify-between gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 ring-1 ring-white/10 text-brand-100 text-xs transition-colors"
        >
          <span className="inline-flex items-center gap-2">
            <Search size={14} />
            Search or ask AI…
          </span>
          <span className="inline-flex items-center gap-1 text-brand-300">
            <kbd className="font-mono px-1.5 py-0.5 rounded bg-white/10 text-2xs">⌘</kbd>
            <kbd className="font-mono px-1.5 py-0.5 rounded bg-white/10 text-2xs">K</kbd>
          </span>
        </button>

        {/* Nav */}
        <nav className="flex-1 px-3 py-3 overflow-y-auto">
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="mb-3">
              <p className="px-3 pb-1 text-2xs font-bold uppercase tracking-wider text-brand-300/80 flex items-center gap-1">
                {section.title === 'AI Compliance' && <Sparkles size={9} className="text-ai-cyan" />}
                {section.title}
              </p>
              <div className="space-y-0.5">
                {section.items.map(({ to, icon: Icon, label, ai }: any) => (
                  <NavLink
                    key={to}
                    to={to}
                    onClick={handleNavClick}
                    className={({ isActive }) =>
                      `relative flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-white/10 text-white shadow-soft-1'
                          : 'text-brand-100/80 hover:bg-white/5 hover:text-white'
                      }`
                    }
                  >
                    <Icon size={16} />
                    <span className="flex-1">{label}</span>
                    {ai && (
                      <span className="text-2xs text-ai-cyan/80 inline-flex items-center gap-0.5">
                        <Sparkles size={8} />
                      </span>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* User chip + logout */}
        <div className="border-t border-white/10 p-3">
          <div className="flex items-center gap-2.5 px-2 py-2 rounded-lg bg-white/5 ring-1 ring-white/10">
            <div className="w-8 h-8 rounded-full bg-ai-gradient flex items-center justify-center text-2xs font-bold text-white shrink-0">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold truncate text-white">{me?.full_name ?? 'Loading…'}</p>
              <p className="text-2xs text-brand-300 truncate">{me?.role?.replace(/_/g, ' ') ?? '—'}</p>
            </div>
            <button
              onClick={logout}
              className="text-brand-300 hover:text-white transition-colors p-1"
              title="Logout"
            >
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar — mobile shows hamburger; all sizes get Cmd+K hint on desktop */}
        <header className="md:hidden flex items-center gap-3 bg-brand-950 text-white px-4 py-3">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-brand-200 hover:text-white"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
          <h1 className="text-base font-bold tracking-tight">TradePath AI</h1>
          <button
            onClick={() => setPaletteOpen(true)}
            className="ml-auto text-brand-200"
            aria-label="Open command palette"
          >
            <CommandIcon size={18} />
          </button>
        </header>

        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>

      <Toaster />
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  )
}
