'use client'

import React, { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ArrowDownCircle, ArrowUpCircle, ArrowLeftRight } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useToast } from '@/components/ui/toaster'
import { parseShorthandAmount, formatAmountLive, getToday } from '@/lib/utils'
import { apiGet, apiJson, queryKeys } from '@/lib/api'
import { Select } from '@/components/ui/Select'
import { AmountInput } from '@/components/ui/AmountInput'
import { BankLogo } from '@/components/ui/BankLogo'

interface Account { id: string; name: string; icon: string; type: string }
interface Category { id: string; name: string; icon: string; color: string; type: string }
type TxType = 'income' | 'expense' | 'transfer'

interface RecurringItem {
  id: string
  type: string
  amount: number
  accountId?: string
  toAccountId?: string
  categoryId?: string
  description?: string
  frequency?: string
  daysOfWeek?: number[] | string | null
  startDate?: string
}

interface RecurringPayload {
  type: TxType
  amount: number
  accountId: string
  toAccountId: string | null
  categoryId: string | null
  description: string
  frequency: string
  daysOfWeek: number[] | null
  startDate: string
  isActive: boolean
  nextRunDate?: string
}

interface RecurringDrawerProps {
  item: RecurringItem | null
  onClose: () => void
  onSaved: () => void
}

const FREQ_OPTIONS = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekdays', label: 'Weekdays' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'yearly', label: 'Yearly' },
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
  const [selectedDays, setSelectedDays] = useState<number[]>([1, 2, 3, 4]) // default Mon-Income
  const [startDate, setStartDate] = useState(getToday())
  const [saving, setSaving] = useState(false)

  const { data: accounts = [] } = useQuery<Account[]>({
    queryKey: queryKeys.accounts,
    queryFn: () => apiGet<Account[]>('/api/accounts'),
  })

  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: queryKeys.categories(),
    queryFn: () => apiGet<Category[]>('/api/categories'),
  })

  useEffect(() => {
    if (item) {
      setTxType(item.type as TxType)
      setAmountRaw(String(item.amount))
      setDescription(item.description ?? '')
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
      const body: RecurringPayload = {
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

      const method = item ? 'PUT' : 'POST'

      await apiJson(item ? `/api/recurring/${item.id}` : '/api/recurring', {
        method,
        body,
      })

      toast(item ? 'Recurring schedule updated' : 'Recurring transaction created')
      onSaved()
    } catch {
      toast('Unable to save. Please try again.')
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
              {item ? 'Edit recurring schedule' : 'Create recurring transaction'}
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
                    <><ArrowDownCircle size={14} style={{ display: 'inline', marginRight: 4 }} />Expense</>
                  ) : t === 'income' ? (
                    <><ArrowUpCircle size={14} style={{ display: 'inline', marginRight: 4 }} />Income</>
                  ) : (
                    <><ArrowLeftRight size={14} style={{ display: 'inline', marginRight: 4 }} />Transfer</>
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
                Amount
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
                <label className="label">Name / Description</label>
                <input
                  type="text"
                  className="input"
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  placeholder="Example: Rent, Netflix, Salary..."
                />
              </div>

              {/* Frequency & Start Date */}
              <div className="drawer-field-grid">
                <div>
                  <label className="label">Repeat frequency</label>
                  <Select
                    value={frequency}
                    onChange={setFrequency}
                    options={FREQ_OPTIONS}
                  />
                </div>
                <div>
                  <label className="label">Start date</label>
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
                  <label className="label">Select weekdays</label>
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
                      Select at least 1 day
                    </div>
                  )}
                  <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 6 }}>
                    Will create {selectedDays.length} transactions/week
                  </div>
                </div>
              )}

              {/* Account */}
              <div>
                <label className="label">Accounts</label>
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
                  <label className="label">Destination account</label>
                  <Select
                    value={toAccountId}
                    onChange={setToAccountId}
                    placeholder="Select account..."
                    options={[
                      { value: '', label: 'Select account...' },
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
                  <label className="label">Category</label>
                  <div className="drawer-option-grid four">
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
              {saving ? 'Saving...' : item ? 'Update' : 'Create schedule'}
            </button>
          </div>
          <style jsx>{`
            .drawer-field-grid {
              display: grid;
              grid-template-columns: repeat(2, minmax(0, 1fr));
              gap: 12px;
            }

            .drawer-option-grid {
              display: grid;
              gap: 8px;
            }

            .drawer-option-grid.four {
              grid-template-columns: repeat(4, minmax(0, 1fr));
            }

            @media (max-width: 480px) {
              .drawer-field-grid,
              .drawer-option-grid.four {
                grid-template-columns: repeat(2, minmax(0, 1fr));
              }
            }
          `}</style>
        </motion.div>
      </>
    </AnimatePresence>,
    document.body
  )
}
