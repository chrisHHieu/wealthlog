import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Portal } from '@/components/ui/Portal'
import { useQueryClient } from '@tanstack/react-query'
import { useToast } from '@/components/ui/toaster'
import { Goal } from '@/types'
import { DatePicker } from '@/components/ui/DatePicker'
import { parseShorthandAmount, formatAmountLive } from '@/lib/utils'
import { API_URL } from '@/lib/api'

const GOAL_TYPES = [
  { key: 'emergency', label: 'Quỹ khẩn cấp', icon: '🛡️' },
  { key: 'savings', label: 'Tiết kiệm', icon: '💰' },
  { key: 'purchase', label: 'Mua sắm lớn', icon: '🛒' },
  { key: 'investment', label: 'Quỹ đầu tư', icon: '📈' },
  { key: 'debt', label: 'Trả nợ', icon: '💳' },
  { key: 'custom', label: 'Tùy chỉnh', icon: '🎯' },
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
        await fetch(`${API_URL}/api/goals/${initialData.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        toast('Đã cập nhật mục tiêu')
      } else {
        await fetch(`${API_URL}/api/goals`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        toast('Đã tạo mục tiêu mới')
      }

      await qc.invalidateQueries({ queryKey: ['goals'] })
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
                <h2 style={{ fontSize: 17, fontWeight: 600 }}>{initialData ? 'Sửa mục tiêu' : 'Tạo mục tiêu mới'}</h2>
                <button onClick={onClose} className="btn btn-ghost" style={{ width: 32, height: 32, padding: 0, borderRadius: '50%' }}>✕</button>
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
                  <label className="label">Màu</label>
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
                  <label className="label">Loại mục tiêu</label>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
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
                  <label className="label">Tên mục tiêu</label>
                  <input type="text" value={formName} onChange={e => setFormName(e.target.value)} placeholder="VD: Du lịch Nhật Bản" className="input" />
                </div>

                <div>
                  <label className="label">Mục tiêu (đ)</label>
                  <input type="text" value={formTarget} onChange={e => setFormTarget(formatAmountLive(e.target.value))} placeholder="0" className="input" />
                </div>

                <div>
                  <label className="label">Số tiền hiện có (đ)</label>
                  <input type="text" value={formCurrent} onChange={e => setFormCurrent(formatAmountLive(e.target.value))} placeholder="0" className="input" />
                </div>

                <div style={{ zIndex: 10 }}>
                  <label className="label">Hạn chót (tuỳ chọn)</label>
                  <DatePicker value={formDeadline} onChange={setFormDeadline} placeholder="Không xác định" />
                </div>
              </div>

              <div className="drawer-footer">
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>Hủy</button>
                <button className="btn btn-primary" style={{ flex: 2 }} onClick={handleSave} disabled={saving || !formName.trim() || !formTarget}>
                  {saving ? 'Đang lưu...' : initialData ? 'Cập nhật' : 'Tạo mục tiêu'}
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </Portal>
  )
}
