import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Portal } from '@/components/ui/Portal'
import { useQueryClient } from '@tanstack/react-query'
import { useToast } from '@/components/ui/toaster'
import { formatVND, getToday } from '@/lib/utils'
import { API_URL } from '@/lib/api'
import { Goal } from '@/types'

interface ContributeModalProps {
  goal: Goal | null
  onClose: () => void
}

export function ContributeModal({ goal, onClose }: ContributeModalProps) {
  const [amount, setAmount] = useState('')
  const [saving, setSaving] = useState(false)
  const qc = useQueryClient()
  const { toast } = useToast()

  async function handleContribute() {
    if (!goal || !amount) return
    setSaving(true)
    try {
      await fetch(`${API_URL}/api/goals/${goal.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          addAmount: parseFloat(amount),
          date: getToday(),
        }),
      })
      await qc.invalidateQueries({ queryKey: ['goals'] })
      toast(`Đã thêm ${formatVND(parseFloat(amount))} vào mục tiêu`)
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <Portal>
      <AnimatePresence>
        {goal && (
          <>
            <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
            <motion.div className="modal" style={{ padding: '28px' }} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}>
              <div style={{ textAlign: 'center', marginBottom: 20 }}>
                <div style={{ fontSize: 36, marginBottom: 8 }}>{goal.icon}</div>
                <h3 style={{ fontSize: 17, fontWeight: 600 }}>{goal.name}</h3>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                  {formatVND(goal.currentAmount)} / {formatVND(goal.targetAmount)}
                </p>
              </div>
              <div style={{ marginBottom: 16 }}>
                <label className="label">Số tiền thêm vào (đ)</label>
                <input
                  type="number"
                  value={amount}
                  onChange={e => setAmount(e.target.value)}
                  placeholder="0"
                  className="input"
                  autoFocus
                />
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>Hủy</button>
                <button className="btn btn-primary" style={{ flex: 2 }} onClick={handleContribute} disabled={saving || !amount}>
                  {saving ? 'Đang lưu...' : 'Thêm vào mục tiêu'}
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </Portal>
  )
}
