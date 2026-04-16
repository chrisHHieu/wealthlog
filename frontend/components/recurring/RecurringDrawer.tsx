'use client'

import React, { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ArrowDownCircle, ArrowUpCircle, ArrowLeftRight } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useToast } from '@/components/ui/toaster'
import { parseShorthandAmount, formatAmountLive, getToday } from '@/lib/utils'
import { API_URL } from '@/lib/api'
import { Select } from '@/components/ui/Select'
import { AmountInput } from '@/components/ui/AmountInput'
import { BankLogo } from '@/components/ui/BankLogo'

interface Account { id: string; name: string; icon: string; type: string }
interface Category { id: string; name: string; icon: string; color: string; type: string }
type TxType = 'income' | 'expense' | 'transfer'

interface RecurringDrawerProps {
  item: any | null
  onClose: () => void
  onSaved: () => void
}

const FREQ_OPTIONS = [
  { value: 'daily', label: 'Hàng ngày' },
  { value: 'weekdays', label: 'Ngày trong tuần' },
  { value: 'weekly', label: 'Hàng tuần' },
  { value: 'monthly', label: 'Hàng tháng' },
  { value: 'yearly', label: 'Hàng năm' },
]

// 0=CN, 1=T2, 2=T3, 3=T4, 4=T5, 5=T6, 6=T7
const DAYS_VI = [
  { label: 'T2', value: 1 },
  { label: 'T3', value: 2 },
  { label: 'T4', value: 3 },
  { label: 'T5', value: 4 },
  { label: 'T6', value: 5 },
  { label: 'T7', value: 6 },
  { label: 'CN', value: 0 },
]

function firstAllowedDay(startDate: string, allowed: number[]): string {
  if (allowed.length === 0) return startDate
  let d = new Date(startDate + 'T00:00:00')
  for (let i = 0; i < 7; i++) {
    if (allowed.includes(d.getDay())) {
      return d.toISOString().slice(0, 10)
    }
    d.setDate(d.getDate() + 1)
  }
  return startDate
}

const TAB_COLORS: Record<TxType, string> = {
  income: 'var(--accent-green)',
  expense: 'var(--accent-red)',
  transfer: 'var(--accent-blue)',
}

export function RecurringDrawer({ item, onClose, onSaved }: RecurringDrawerProps) {
  const { toast } = useToast()

  const [txType, setTxType] = useState<TxType>('expense')
  const [amountRaw, setAmountRaw] = useState('')
  const [description, setDescription] = useState('')
  const [accountId, setAccountId] = useState('')
  const [toAccountId, setToAccountId] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [frequency, setFrequency] = useState('monthly')
  const [selectedDays, setSelectedDays] = useState<number[]>([1, 2, 3, 4]) // default Mon-Thu
  const [startDate, setStartDate] = useState(getToday())
  const [saving, setSaving] = useState(false)

  const { data: accounts = [] } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: () => fetch(`${API_URL}/api/accounts`).then(r => r.json()),
  })

  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: () => fetch(`${API_URL}/api/categories`).then(r => r.json()),
  })

  useEffect(() => {
    if (item) {
      setTxType(item.type)
      setAmountRaw(String(item.amount))
      setDescription(item.description)
      setAccountId(item.accountId || '')
      setToAccountId(item.toAccountId || '')
      setCategoryId(item.categoryId || '')
      // If item has daysOfWeek, show as 'weekdays' mode in UI
      setFrequency(item.daysOfWeek ? 'weekdays' : (item.frequency || 'monthly'))
      setSelectedDays(item.daysOfWeek ? (Array.isArray(item.daysOfWeek) ? item.daysOfWeek : JSON.parse(item.daysOfWeek)) : [1, 2, 3, 4])
      setStartDate(item.startDate || getToday())
    } else {
      setTxType('expense')
      setAmountRaw('')
      setDescription('')
      setCategoryId('')
      setToAccountId('')
      setFrequency('monthly')
      setSelectedDays([1, 2, 3, 4])
      setStartDate(getToday())
    }
  }, [item])

  useEffect(() => {
    if (accounts.length > 0 && !accountId) {
      setAccountId(accounts[0].id)
    }
  }, [accounts, accountId])

  const filteredCategories = categories.filter(c => c.type === txType || c.type === 'both')
  const parsedAmount = parseShorthandAmount(amountRaw) ?? 0
  const isValid = parsedAmount > 0 && description.trim() && accountId &&
    (txType !== 'transfer' || (toAccountId && toAccountId !== accountId)) &&
    (frequency !== 'weekdays' || selectedDays.length > 0)

  async function handleSubmit() {
    if (!isValid) return
    setSaving(true)
    try {
      const isWeekdays = frequency === 'weekdays'
      const body: Record<string, any> = {
        type: txType,
        amount: parsedAmount,
        accountId,
        toAccountId: txType === 'transfer' ? toAccountId || null : null,
        categoryId: categoryId || null,
        description: description.trim(),
        // weekdays mode stores as 'daily' in DB (CHECK constraint), daysOfWeek column holds the actual days
        frequency: isWeekdays ? 'daily' : frequency,
        daysOfWeek: isWeekdays ? selectedDays.sort((a, b) => a - b) : null,
        startDate,
        isActive: true,
      }

      if (item) {
        const scheduleChanged = startDate !== item.startDate || frequency !== (item.daysOfWeek ? 'weekdays' : item.frequency)
        if (scheduleChanged) {
          const today = getToday()
          const baseDate = startDate > today ? startDate : today
          body.nextRunDate = isWeekdays ? firstAllowedDay(baseDate, selectedDays) : baseDate
        }
      } else {
        // Creating: first run is at first eligible day >= startDate
        body.nextRunDate = isWeekdays ? firstAllowedDay(startDate, selectedDays) : startDate
      }

      const url = item ? `${API_URL}/api/recurring/${item.id}` : `${API_URL}/api/recurring`
      const method = item ? 'PUT' : 'POST'

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!res.ok) throw new Error('Lỗi lưu dữ liệu')

      toast(item ? 'Đã cập nhật lịch định kỳ' : 'Đã tạo giao dịch định kỳ')
      onSaved()
    } catch {
      toast('Lỗi lưu dữ liệu. Thử lại nhé.')
    } finally {
      setSaving(false)
    }
  }

  return createPortal(
    <AnimatePresence>
      <>
        {/* Overlay — exact same as TransactionDrawer */}
        <motion.div
          className="overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        />

        {/* Drawer — exact same structure as TransactionDrawer */}
        <motion.div
          className="drawer"
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          style={{ display: 'flex', flexDirection: 'column', height: '100dvh' }}
        >
          {/* Header — exact same as TransactionDrawer */}
          <div style={{
            padding: '20px 24px',
            borderBottom: '1px solid var(--surface-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0,
          }}>
            <h2 style={{ fontSize: 17, fontWeight: 600 }}>
              {item ? 'Sửa định kỳ' : 'Tạo giao dịch định kỳ'}
            </h2>
            <button
              onClick={onClose}
              className="btn btn-ghost"
              style={{ width: 32, height: 32, padding: 0, borderRadius: '50%' }}
            >
              <X size={18} />
            </button>
          </div>

          {/* Type tabs — exact same as TransactionDrawer */}
          <div style={{ padding: '16px 24px 0', flexShrink: 0 }}>
            <div className="tabs">
              {(['expense', 'income', 'transfer'] as TxType[]).map(t => (
                <button
                  key={t}
                  onClick={() => { setTxType(t); setCategoryId('') }}
                  className={`tab-btn ${txType === t ? 'active' : ''}`}
                  style={{
                    ...(txType === t ? {
                      background: t === 'expense' ? 'var(--accent-red)'
                        : t === 'income' ? 'var(--accent-green)'
                        : 'var(--accent-blue)',
                      color: '#fff',
                    } : {})
                  }}
                >
                  {t === 'expense' ? (
                    <><ArrowDownCircle size={14} style={{ display: 'inline', marginRight: 4 }} />Chi</>
                  ) : t === 'income' ? (
                    <><ArrowUpCircle size={14} style={{ display: 'inline', marginRight: 4 }} />Thu</>
                  ) : (
                    <><ArrowLeftRight size={14} style={{ display: 'inline', marginRight: 4 }} />Chuyển</>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Form — scrollable body, exact same structure as TransactionDrawer */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
            {/* Amount */}
            <div style={{ textAlign: 'center', marginBottom: 28 }}>
              <div style={{ fontSize: 11, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                Số tiền
              </div>
              <AmountInput
                value={amountRaw}
                onChange={(val: string) => setAmountRaw(formatAmountLive(val))}
                color={TAB_COLORS[txType]}
                autoFocus
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Description */}
              <div>
                <label className="label">Tên / Mô tả</label>
                <input
                  type="text"
                  className="input"
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  placeholder="VD: Tiền nhà, Netflix, Lương..."
                />
              </div>

              {/* Frequency & Start Date */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label className="label">Chu kỳ lặp</label>
                  <Select
                    value={frequency}
                    onChange={setFrequency}
                    options={FREQ_OPTIONS}
                  />
                </div>
                <div>
                  <label className="label">Bắt đầu từ ngày</label>
                  <input
                    type="date"
                    className="input"
                    value={startDate}
                    onChange={e => setStartDate(e.target.value)}
                  />
                </div>
              </div>

              {/* Day picker — only shown for weekdays mode */}
              {frequency === 'weekdays' && (
                <div>
                  <label className="label">Chọn ngày trong tuần</label>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {DAYS_VI.map(day => {
                      const active = selectedDays.includes(day.value)
                      return (
                        <button
                          key={day.value}
                          type="button"
                          onClick={() => setSelectedDays(prev =>
                            active ? prev.filter(d => d !== day.value) : [...prev, day.value]
                          )}
                          style={{
                            width: 40, height: 40,
                            borderRadius: 10,
                            border: `1px solid ${active ? 'var(--accent-green)' : 'var(--surface-border)'}`,
                            background: active ? 'rgba(0,200,150,0.15)' : 'var(--surface)',
                            color: active ? 'var(--accent-green)' : 'var(--text-secondary)',
                            fontWeight: active ? 700 : 400,
                            fontSize: 12,
                            cursor: 'pointer',
                            transition: 'all 0.15s',
                          }}
                        >
                          {day.label}
                        </button>
                      )
                    })}
                  </div>
                  {selectedDays.length === 0 && (
                    <div style={{ fontSize: 11, color: 'var(--accent-red)', marginTop: 6 }}>
                      Chọn ít nhất 1 ngày
                    </div>
                  )}
                  <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 6 }}>
                    Sẽ tạo {selectedDays.length} giao dịch/tuần
                  </div>
                </div>
              )}

              {/* Account */}
              <div>
                <label className="label">Tài khoản</label>
                <Select
                  value={accountId}
                  onChange={setAccountId}
                  options={accounts.map(a => ({
                    value: a.id,
                    label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <BankLogo iconStr={a.icon} color="var(--text-primary)" size={20} /> {a.name}
                    </span>
                  }))}
                />
              </div>

              {/* To account (transfer only) */}
              {txType === 'transfer' && (
                <div>
                  <label className="label">Tài khoản đích</label>
                  <Select
                    value={toAccountId}
                    onChange={setToAccountId}
                    placeholder="Chọn tài khoản..."
                    options={[
                      { value: '', label: 'Chọn tài khoản...' },
                      ...accounts.filter(a => a.id !== accountId).map(a => ({
                        value: a.id,
                        label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <BankLogo iconStr={a.icon} color="var(--text-primary)" size={20} /> {a.name}
                        </span>
                      }))
                    ]}
                  />
                </div>
              )}

              {/* Category */}
              {txType !== 'transfer' && (
                <div>
                  <label className="label">Danh mục</label>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                    {filteredCategories.map(cat => (
                      <button
                        key={cat.id}
                        onClick={() => setCategoryId(cat.id === categoryId ? '' : cat.id)}
                        style={{
                          padding: '8px 4px', borderRadius: 8,
                          border: `1px solid ${categoryId === cat.id ? cat.color : 'var(--surface-border)'}`,
                          background: categoryId === cat.id ? `${cat.color}20` : 'var(--surface)',
                          cursor: 'pointer', textAlign: 'center', transition: 'all 0.15s',
                        }}
                      >
                        <div style={{ fontSize: 20, lineHeight: 1 }}>{cat.icon}</div>
                        <div style={{
                          fontSize: 10,
                          color: categoryId === cat.id ? cat.color : 'var(--text-secondary)',
                          marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        }}>
                          {cat.name}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Footer — exact same as TransactionDrawer */}
          <div className="drawer-footer">
            <button
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={!isValid || saving}
              style={{ flex: 1 }}
            >
              {saving ? 'Đang lưu...' : item ? 'Cập nhật' : 'Tạo lịch định kỳ'}
            </button>
          </div>
        </motion.div>
      </>
    </AnimatePresence>,
    document.body
  )
}
