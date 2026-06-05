'use client'

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, XCircle, Info, RotateCcw, X } from 'lucide-react'

interface Toast {
  id: string
  message: string
  type: 'success' | 'error' | 'info'
  undo?: () => void | Promise<void>
  duration?: number
}

interface ToasterContextType {
  toast: (message: string, options?: Partial<Omit<Toast, 'id' | 'message'>>) => void
}

export const ToasterContext = createContext<ToasterContextType>({
  toast: () => {},
})

export function useToast() {
  return useContext(ToasterContext)
}

export function Toaster({ children }: { children?: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const toast = useCallback((
    message: string,
    options: Partial<Omit<Toast, 'id' | 'message'>> = {}
  ) => {
    const id = crypto.randomUUID()
    const duration = options.duration ?? (options.undo ? 4000 : 3000)

    setToasts(prev => [...prev, { id, message, type: 'success', ...options }])
    setTimeout(() => removeToast(id), duration)
  }, [removeToast])

  return (
    <ToasterContext.Provider value={{ toast }}>
      {children}
      <div className="toast-container">
        <AnimatePresence mode="popLayout">
          {toasts.map(t => (
            <motion.div
              key={t.id}
              className="toast"
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            >
              {t.type === 'success' && <CheckCircle size={16} style={{ color: 'var(--accent-green)', flexShrink: 0 }} />}
              {t.type === 'error' && <XCircle size={16} style={{ color: 'var(--accent-red)', flexShrink: 0 }} />}
              {t.type === 'info' && <Info size={16} style={{ color: 'var(--accent-blue)', flexShrink: 0 }} />}

              <span style={{ flex: 1, color: 'var(--text-primary)', fontSize: 13 }}>{t.message}</span>

              {t.undo && (
                <button
                  onClick={async () => { await t.undo!(); removeToast(t.id) }}
                  style={{
                    background: 'rgba(0,200,150,0.15)', border: 'none', color: 'var(--accent-green)',
                    fontSize: 12, fontWeight: 600, padding: '4px 10px', borderRadius: 6, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0,
                  }}
                >
                  <RotateCcw size={12} /> Undo
                </button>
              )}

              <button
                onClick={() => removeToast(t.id)}
                style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer', padding: 2 }}
              >
                <X size={14} />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToasterContext.Provider>
  )
}
