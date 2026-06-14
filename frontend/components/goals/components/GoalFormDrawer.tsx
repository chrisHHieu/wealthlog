import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { Portal } from '@/components/ui/Portal'
import { useQueryClient } from '@tanstack/react-query'
import { useToast } from '@/components/ui/toaster'
import { Goal } from '@/types'
import { DatePicker } from '@/components/ui/DatePicker'
import { parseShorthandAmount, formatAmountLive } from '@/lib/utils'
import { apiJson, queryKeys } from '@/lib/api'

const GOAL_TYPES = [
  { key: 'emergency', label: 'Emergency fund', icon: '🛡️' },
  { key: 'savings', label: 'Savings', icon: '💰' },
  { key: 'purchase', label: 'Large purchase', icon: '🛒' },
  { key: 'investment', label: 'Investment fund', icon: '📈' },
  { key: 'debt', label: 'Debt repayment', icon: '💳' },
  { key: 'custom', label: 'Custom', icon: '🎯' },
]

const GOAL_COLORS = ['#00C896', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#d946ef', '#06b6d4', '#84cc16']
const GOAL_ICONS = ['🎯', '🏠', '🚗', '💻', '✈️', '🏖️', '💍', '🎓', '🛡️', '📈', '💰', '🏆']

interface GoalFormDrawerProps {
  isOpen: boolean
  onClose: () => void
  initialData: Goal | null
}

export function GoalFormDrawer({ isOpen, onClose, initialData }: GoalFormDrawerProps) {
  const { toast } = useToast()
  const qc = useQueryClient()

  const [formName, setFormName] = useState('')
  const [formType, setFormType] = useState('custom')
  const [formTarget, setFormTarget] = useState('')
  const [formCurrent, setFormCurrent] = useState('0')
  const [formDeadline, setFormDeadline] = useState('')
  const [formIcon, setFormIcon] = useState('🎯')
  const [formColor, setFormColor] = useState('#00C896')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (isOpen) {
      if (initialData) {
        setFormName(initialData.name)
        setFormType(initialData.type ?? 'custom')
        setFormTarget(String(initialData.targetAmount))
        setFormCurrent(String(initialData.currentAmount))
        setFormDeadline(initialData.deadline ?? '')
        setFormIcon(initialData.icon)
        setFormColor(initialData.color)
      } else {
        setFormName('')
        setFormType('custom')
        setFormTarget('')
        setFormCurrent('0')
        setFormDeadline('')
        setFormIcon('🎯')
        setFormColor('#00C896')
      }
    }
  }, [isOpen, initialData])

  async function handleSave() {
    if (!formName.trim() || !formTarget) return
    setSaving(true)
    try {
      const body = {
        name: formName.trim(),
        type: formType,
        targetAmount: parseShorthandAmount(formTarget) || 0,
        currentAmount: parseShorthandAmount(formCurrent) || 0,
        deadline: formDeadline || undefined,
        icon: formIcon,
        color: formColor,
      }

      if (initialData) {
        await apiJson(`/api/goals/${initialData.id}`, {
          method: 'PUT',
          body,
        })
        toast('Goal updated')
      } else {
        await apiJson('/api/goals', {
          method: 'POST',
          body,
        })
        toast('Goal created')
      }

      await qc.invalidateQueries({ queryKey: queryKeys.goals })
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <Portal>
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
            <motion.div className="drawer" style={{ height: '100dvh', display: 'flex', flexDirection: 'column' }} initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', stiffness: 300, damping: 30 }}>
              <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--surface-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <h2 style={{ fontSize: 17, fontWeight: 600 }}>{initialData ? 'Edit goal' : 'Create new goal'}</h2>
                <button onClick={onClose} className="btn btn-ghost" style={{ width: 32, height: 32, padding: 0, borderRadius: '50%' }} aria-label="Close">
                  <X size={16} />
                </button>
              </div>

              <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div>
                  <label className="label">Icon</label>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {GOAL_ICONS.map(i => (
                      <button key={i} onClick={() => setFormIcon(i)} style={{
                        fontSize: 22, width: 44, height: 44, borderRadius: 10,
                        border: `2px solid ${formIcon === i ? formColor : 'var(--surface-border)'}`,
                        background: formIcon === i ? `${formColor}20` : 'var(--surface)', cursor: 'pointer',
                      }}>{i}</button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="label">Color</label>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {GOAL_COLORS.map(c => (
                      <button key={c} onClick={() => setFormColor(c)} style={{
                        width: 32, height: 32, borderRadius: '50%', background: c,
                        border: `3px solid ${formColor === c ? 'var(--text-primary)' : 'transparent'}`, cursor: 'pointer',
                      }} />
                    ))}
                  </div>
                </div>

                <div>
                  <label className="label">Goal type</label>
                  <div className="goal-type-grid">
                    {GOAL_TYPES.map(t => (
                      <button key={t.key} onClick={() => { setFormType(t.key); setFormIcon(t.icon) }} style={{
                        padding: '8px 6px', borderRadius: 8, border: `1px solid ${formType === t.key ? formColor : 'var(--surface-border)'}`,
                        background: formType === t.key ? `${formColor}20` : 'var(--surface)', cursor: 'pointer', fontSize: 11,
                        color: formType === t.key ? formColor : 'var(--text-secondary)', textAlign: 'center',
                      }}>
                        <div style={{ fontSize: 18, marginBottom: 2 }}>{t.icon}</div>
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="label">Goal name</label>
                  <input type="text" value={formName} onChange={e => setFormName(e.target.value)} placeholder="Example: Japan trip" className="input" />
                </div>

                <div>
                  <label className="label">Goals (VND)</label>
                  <input type="text" value={formTarget} onChange={e => setFormTarget(formatAmountLive(e.target.value))} placeholder="0" className="input" />
                </div>

                <div>
                  <label className="label">Current amount (VND)</label>
                  <input type="text" value={formCurrent} onChange={e => setFormCurrent(formatAmountLive(e.target.value))} placeholder="0" className="input" />
                </div>

                <div style={{ zIndex: 10 }}>
                  <label className="label">Deadline (optional)</label>
                  <DatePicker value={formDeadline} onChange={setFormDeadline} placeholder="No deadline" />
                </div>
              </div>

              <div className="drawer-footer">
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>Cancel</button>
                <button className="btn btn-primary" style={{ flex: 2 }} onClick={handleSave} disabled={saving || !formName.trim() || !formTarget}>
                  {saving ? 'Saving...' : initialData ? 'Update' : 'Create goal'}
                </button>
              </div>
              <style jsx>{`
                .goal-type-grid {
                  display: grid;
                  grid-template-columns: repeat(3, minmax(0, 1fr));
                  gap: 6px;
                }

                @media (max-width: 480px) {
                  .goal-type-grid {
                    grid-template-columns: 1fr;
                  }
                }
              `}</style>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </Portal>
  )
}
