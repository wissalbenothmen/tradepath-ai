import { useState, useCallback, useEffect, createContext, useContext } from 'react'
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from 'lucide-react'

type ToastVariant = 'success' | 'error' | 'warning' | 'info'

interface Toast {
  id: string
  message: string
  variant: ToastVariant
}

interface ToastContextValue {
  toast: (message: string, variant?: ToastVariant) => void
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} })

let _globalToast: ((message: string, variant?: ToastVariant) => void) | null = null

export function useToast() {
  return useContext(ToastContext)
}

// Standalone toast function that can be called outside React tree
export const toast = (message: string, variant: ToastVariant = 'info') => {
  if (_globalToast) _globalToast(message, variant)
}

const variantConfig = {
  success: { icon: CheckCircle2, bg: 'bg-green-50 border-green-200', text: 'text-green-800', icon_color: 'text-green-500' },
  error: { icon: XCircle, bg: 'bg-red-50 border-red-200', text: 'text-red-800', icon_color: 'text-red-500' },
  warning: { icon: AlertTriangle, bg: 'bg-yellow-50 border-yellow-200', text: 'text-yellow-800', icon_color: 'text-yellow-500' },
  info: { icon: Info, bg: 'bg-blue-50 border-blue-200', text: 'text-blue-800', icon_color: 'text-blue-500' },
}

export function Toaster() {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((message: string, variant: ToastVariant = 'info') => {
    const id = Math.random().toString(36).slice(2)
    setToasts((prev) => [...prev, { id, message, variant }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }, [])

  useEffect(() => {
    _globalToast = addToast
    return () => { _globalToast = null }
  }, [addToast])

  const remove = (id: string) => setToasts((prev) => prev.filter((t) => t.id !== id))

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-sm w-full pointer-events-none">
        {toasts.map((t) => {
          const cfg = variantConfig[t.variant]
          const Icon = cfg.icon
          return (
            <div
              key={t.id}
              className={`flex items-start gap-3 p-4 rounded-xl border shadow-lg ${cfg.bg} pointer-events-auto animate-slide-in`}
            >
              <Icon size={18} className={`${cfg.icon_color} mt-0.5 flex-shrink-0`} />
              <p className={`text-sm font-medium flex-1 ${cfg.text}`}>{t.message}</p>
              <button onClick={() => remove(t.id)} className={`${cfg.icon_color} hover:opacity-70`}>
                <X size={14} />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}
