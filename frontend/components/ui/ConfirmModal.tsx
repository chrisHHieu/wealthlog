import { motion, AnimatePresence } from 'framer-motion'
import { Portal } from './Portal'

interface ConfirmModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  description?: string
  icon?: string
  confirmText?: string
  cancelText?: string
  variant?: 'danger' | 'primary'
}

export function ConfirmModal({
  isOpen, onClose, onConfirm,
  title, description, icon = '⚠️',
  confirmText = 'Confirm', cancelText = 'Cancel',
  variant = 'danger'
}: ConfirmModalProps) {
  return (
    <Portal>
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              className="overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onClose}
            />
            <motion.div
              className="modal"
              style={{ padding: '28px', textAlign: 'center' }}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
            >
              <div style={{ fontSize: 40, marginBottom: 12 }}>{icon}</div>
              <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 8 }}>{title}</h3>
              {description && (
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24 }}>
                  {description}
                </p>
              )}
              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>
                  {cancelText}
                </button>
                <button
                  className={`btn btn-${variant}`}
                  style={{ flex: 1 }}
                  onClick={() => { onConfirm(); onClose() }}
                >
                  {confirmText}
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </Portal>
  )
}
