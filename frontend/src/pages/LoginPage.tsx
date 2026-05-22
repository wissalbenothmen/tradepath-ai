import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Eye, EyeOff, ShieldCheck, Globe, FileText, TrendingDown, Sparkles, Mic,
} from 'lucide-react'
import api, { endpoints } from '../api'

const FEATURES = [
  { icon: ShieldCheck, title: 'Sanctions screening',  desc: 'OFAC SDN · BIS · EU · UN +4 lists' },
  { icon: FileText,    title: 'HS classification',    desc: 'AI-powered WCO GRI 1–6' },
  { icon: Globe,       title: 'Certificate of Origin', desc: 'USMCA · EUR.1 · Form A (GSP)' },
  { icon: TrendingDown,title: 'FTA duty savings',     desc: 'USMCA · CPTPP · EU-Korea · 8 more' },
  { icon: Mic,         title: 'Voice amendments',     desc: 'Whisper Large v3 ↔ documents' },
  { icon: Sparkles,    title: 'AI cross-validation',  desc: 'Reconciles voice ↔ invoice ↔ CoO' },
]

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const form = new URLSearchParams({ username: email, password })
      const { data } = await api.post(endpoints.auth.login, form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      localStorage.setItem('token', data.access_token)
      navigate('/dashboard')
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (err?.response?.status === 401) setError('Invalid email or password.')
      else if (err?.response?.status === 429) setError('Too many login attempts. Try again in a minute.')
      else if (typeof detail === 'string') setError(detail)
      else setError('Could not reach the server. Check your connection.')
    } finally {
      setLoading(false)
    }
  }

  const fillDemo = () => {
    setEmail('demo@tradepath.ai')
    setPassword('DemoPass1!')
  }

  return (
    <div className="min-h-screen relative overflow-hidden flex items-center justify-center p-4"
         style={{ backgroundImage: 'linear-gradient(135deg, #080f2b 0%, #0b1f4d 45%, #1734bd 100%)' }}>
      {/* Decorative glow */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-[-12%] left-[-10%] w-[40rem] h-[40rem] rounded-full"
             style={{ background: 'radial-gradient(circle, rgb(124 58 237 / 0.35), transparent 70%)' }} />
        <div className="absolute bottom-[-15%] right-[-10%] w-[40rem] h-[40rem] rounded-full"
             style={{ background: 'radial-gradient(circle, rgb(6 182 212 / 0.30), transparent 70%)' }} />
      </div>

      <div className="relative w-full max-w-5xl flex rounded-3xl shadow-2xl overflow-hidden ring-1 ring-white/10">
        {/* Left value-prop panel */}
        <div className="hidden lg:flex flex-col justify-between bg-brand-950/80 backdrop-blur-xl border-r border-white/10 p-10 w-[26rem] shrink-0">
          <div>
            <div className="flex items-center gap-3 mb-8">
              <div className="w-10 h-10 rounded-xl bg-ai-gradient flex items-center justify-center shadow-ai-glow-soft">
                <Sparkles size={18} className="text-white" />
              </div>
              <div>
                <h1 className="text-white font-bold text-base leading-none">TradePath AI</h1>
                <p className="text-brand-300 text-2xs mt-1">Trade Compliance · AI-Native</p>
              </div>
            </div>

            <h2 className="text-3xl font-extrabold text-white leading-tight tracking-tight mb-3">
              The <span className="ai-text-gradient">compliance backbone</span><br />for international trade.
            </h2>
            <p className="text-brand-200 text-sm leading-relaxed mb-8">
              One system of record for HS classification, sanctions screening, customs declarations, certificates of origin, FTA duty savings — and AI cross-validates them all against the broker's voice notes.
            </p>

            <div className="grid grid-cols-2 gap-3">
              {FEATURES.map(({ icon: Icon, title, desc }) => (
                <div key={title} className="flex items-start gap-2.5 p-2.5 bg-white/5 rounded-lg ring-1 ring-white/10">
                  <Icon size={14} className="text-ai-cyan mt-0.5 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-white text-xs font-semibold leading-none">{title}</p>
                    <p className="text-brand-300 text-2xs mt-1 leading-snug">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Trust signals */}
          <div className="border-t border-white/10 pt-5 space-y-2">
            <p className="text-brand-300 text-2xs font-semibold uppercase tracking-wider">Compliance coverage</p>
            <div className="flex flex-wrap gap-1.5">
              {['OFAC SDN', 'BIS Entity', 'EU Consolidated', 'UN SC', 'HM Treasury', 'ITAR / EAR'].map((tag) => (
                <span key={tag} className="bg-white/5 text-brand-200 px-2 py-0.5 rounded text-2xs ring-1 ring-white/10">{tag}</span>
              ))}
            </div>
          </div>
        </div>

        {/* Right login form */}
        <div className="flex-1 bg-white p-8 sm:p-10 flex flex-col justify-center">
          <div className="lg:hidden text-center mb-8">
            <h1 className="text-2xl font-bold text-brand-900">TradePath AI</h1>
            <p className="text-slate-500 text-sm mt-1">AI-Powered Trade Compliance</p>
          </div>

          <div className="max-w-sm mx-auto w-full">
            <h2 className="text-xl font-bold text-slate-900 mb-1">Sign in</h2>
            <p className="text-sm text-slate-500 mb-6">Access your compliance command center.</p>

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label htmlFor="li-email" className="block text-2xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Email</label>
                <input
                  id="li-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
                  placeholder="broker@company.com"
                  autoComplete="email"
                />
              </div>

              <div>
                <label htmlFor="li-password" className="block text-2xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Password</label>
                <div className="relative">
                  <input
                    id="li-password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2.5 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
                    placeholder="••••••••"
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {error && (
                <div className="flex items-center gap-2 bg-red-50 ring-1 ring-red-200 rounded-lg px-3 py-2">
                  <ShieldCheck size={14} className="text-red-500 shrink-0" />
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full btn-primary justify-center py-2.5"
              >
                {loading ? 'Signing in…' : 'Sign in to TradePath AI'}
              </button>
            </form>

            {/* Demo credential helper */}
            <button
              onClick={fillDemo}
              type="button"
              className="mt-4 w-full text-center text-xs text-brand-700 hover:text-brand-900 font-medium inline-flex items-center justify-center gap-1.5"
            >
              <Sparkles size={11} className="text-ai-500" /> Try the demo tenant (demo@tradepath.ai)
            </button>

            <div className="lg:hidden mt-8 pt-6 border-t border-slate-100">
              <p className="text-2xs text-slate-400 text-center mb-3 uppercase tracking-wider">Compliance lists</p>
              <div className="flex flex-wrap justify-center gap-1.5">
                {['OFAC SDN', 'BIS Entity', 'EU', 'UN'].map((tag) => (
                  <span key={tag} className="bg-slate-100 text-slate-500 px-2 py-0.5 rounded text-2xs">{tag}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
