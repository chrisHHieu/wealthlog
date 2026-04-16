'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ArrowDownCircle, ArrowUpCircle, ArrowLeftRight } from 'lucide-react'
import { useAppStore } from '@/store/useAppStore'
import { useQueryClient, useQuery } from '@tanstack/react-query'
import { useToast } from '@/components/ui/toaster'
import { parseShorthandAmount, formatVND, formatAmountLive, getToday } from '@/lib/utils'
import { API_URL } from '@/lib/api'
import { Select } from '@/components/ui/Select'
import { DatePicker } from '@/components/ui/DatePicker'
import { AmountInput } from '@/components/ui/AmountInput'
import { BankLogo } from '@/components/ui/BankLogo'
import { useSearchParams } from 'next/navigation'

interface Account {
  id: string
  name: string
  icon: string
  type: string
}

interface Category {
  id: string
  name: string
  icon: string
  color: string
  type: string
}

type TxType = 'income' | 'expense' | 'transfer'

export function TransactionDrawer() {
  const { addTransactionOpen, transactionDefaultType, editTransactionId, closeAddTransaction } = useAppStore()
  const { toast } = useToast()
  const qc = useQueryClient()
  const searchParams = useSearchParams()

  const [txType, setTxType] = useState<TxType>('expense')
  const [amountRaw, setAmountRaw] = useState('')
  const [description, setDescription] = useState('')
  const [accountId, setAccountId] = useState('')
  const [toAccountId, setToAccountId] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [date, setDate] = useState(getToday())
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveAndAdd, setSaveAndAdd] = useState(false)

  const { data: accounts = [] } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: () => fetch(`${API_URL}/api/accounts`).then(r => r.json()),
  })

  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: () => fetch(`${API_URL}/api/categories`).then(r => r.json()),
  })

  // Fetch edit data if needed
  const { data: editData } = useQuery({
    queryKey: ['transaction', editTransactionId],
    queryFn: () => fetch(`${API_URL}/api/transactions/${editTransactionId}`).then(r => r.json()),
    enabled: !!editTransactionId,
  })

  function resetForm() {
    setTxType(transactionDefaultType || 'expense')
    setAmountRaw('')
    setDescription('')
    setNote('')
    setCategoryId('')
    setDate(getToday())
    setToAccountId('')
  }

  // Pre-fill form when editing
  useEffect(() => {
    if (addTransactionOpen) {
      if (editTransactionId && editData) {
        setTxType(editData.type as TxType)
        setAmountRaw(String(editData.amount))
        setDescription(editData.description)
        setAccountId(editData.accountId)
        if (editData.type === 'transfer' && editData.toAccountId) {
          setToAccountId(editData.toAccountId)
        } else {
          setToAccountId('')
        }
        setCategoryId(editData.categoryId || '')
        setDate(editData.date.substring(0, 10))
        setNote(editData.note || '')
      } else if (!editTransactionId) {
        resetForm()
      }
    }
  }, [addTransactionOpen, editTransactionId, editData, transactionDefaultType])

  // Set default account
  useEffect(() => {
    if (accounts.length > 0 && !accountId && !editTransactionId) {
      setAccountId(accounts[0].id)
    }
  }, [accounts, accountId, editTransactionId])

  const filteredCategories = categories.filter(
    c => c.type === txType || c.type === 'both'
  )

  const parsedAmount = parseShorthandAmount(amountRaw) ?? 0
  const isValid = parsedAmount > 0 && description.trim() && accountId &&
    (txType !== 'transfer' || (toAccountId && toAccountId !== accountId))

  async function handleSubmit(addMore = false) {
    if (!isValid) return
    setSaving(true)
    setSaveAndAdd(addMore)

    try {
      const body = {
        type: txType,
        amount: parsedAmount,
        accountId,
        toAccountId: txType === 'transfer' ? toAccountId || undefined : undefined,
        categoryId: categoryId || undefined,
        description: description.trim(),
        date,
        note: note.trim() || undefined,
      }

      const url = editTransactionId
        ? `${API_URL}/api/transactions/${editTransactionId}`
        : `${API_URL}/api/transactions`
      const method = editTransactionId ? 'PUT' : 'POST'

      await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      await qc.invalidateQueries({ queryKey: ['transactions'] })
      await qc.invalidateQueries({ queryKey: ['dashboard'] })
      await qc.invalidateQueries({ queryKey: ['accounts'] })

      toast(editTransactionId ? 'Đã cập nhật giao dịch' : 'Đã thêm giao dịch')

      // Check budget warning for expense transactions
      if (txType === 'expense' && categoryId) {
        const txMonth = date.substring(0, 7)
        try {
          const res = await fetch(`${API_URL}/api/budgets/check?categoryId=${categoryId}&month=${txMonth}`)
          const budgetStatus = await res.json()
          if (budgetStatus) {
            if (budgetStatus.isExceeded) {
              toast(
                `⚠️ Vượt ngân sách ${budgetStatus.categoryIcon} ${budgetStatus.categoryName}! Đã chi ${formatVND(budgetStatus.totalSpent)} / ${formatVND(budgetStatus.budgetAmount)} (${budgetStatus.percent}%)`,
                { type: 'error', duration: 5000 }
              )
            } else if (budgetStatus.isWarning) {
              toast(
                `⚡ Sắp hết ngân sách ${budgetStatus.categoryIcon} ${budgetStatus.categoryName}: còn ${formatVND(budgetStatus.remaining)} (${budgetStatus.percent}%)`,
                { type: 'info', duration: 4000 }
              )
            }
          }
        } catch {
          // Silently ignore budget check errors
        }
      }

      if (addMore) {
        // Reset form except type
        setAmountRaw('')
        setDescription('')
        setNote('')
        setDate(getToday())
        setCategoryId('')
      } else {
        closeAddTransaction()
      }
    } finally {
      setSaving(false)
      setSaveAndAdd(false)
    }
  }


  const TAB_COLORS: Record<TxType, string> = {
    income: 'var(--accent-green)',
    expense: 'var(--accent-red)',
    transfer: 'var(--accent-blue)',
  }

  return (
    <AnimatePresence>
      {addTransactionOpen && (
        <>
          <motion.div
            className="overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeAddTransaction}
          />
          <motion.div
            className="drawer"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            style={{ display: 'flex', flexDirection: 'column', height: '100dvh' }}
          >
            {/* Header */}
            <div style={{
              padding: '20px 24px',
              borderBottom: '1px solid var(--surface-border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexShrink: 0,
            }}>
              <h2 style={{ fontSize: 17, fontWeight: 600 }}>
                {editTransactionId ? 'Sửa giao dịch' : 'Thêm giao dịch'}
              </h2>
              <button
                onClick={closeAddTransaction}
                className="btn btn-ghost"
                style={{ width: 32, height: 32, padding: 0, borderRadius: '50%' }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Type tabs */}
            <div style={{ padding: '16px 24px 0', flexShrink: 0 }}>
              <div className="tabs">
                {(['expense', 'income', 'transfer'] as TxType[]).map(t => (
                  <button
                    key={t}
                    id={`tx-type-${t}`}
                    onClick={() => setTxType(t)}
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

            {/* Form */}
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
                  <label className="label" htmlFor="tx-description">Mô tả</label>
                  <input
                    id="tx-description"
                    type="text"
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    placeholder="VD: Ăn trưa với đồng nghiệp"
                    className="input"
                  />
                </div>

                {/* Account */}
                <div>
                  <label className="label" htmlFor="tx-account">Tài khoản</label>
                  <Select
                    value={accountId}
                    onChange={setAccountId}
                    options={accounts.map(a => ({ value: a.id, label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><BankLogo iconStr={a.icon} color="var(--text-primary)" size={20} /> {a.name}</span> }))}
                  />
                </div>

                {/* To Account (for transfer) */}
                {txType === 'transfer' && (
                  <div>
                    <label className="label" htmlFor="tx-to-account">Tài khoản đích</label>
                    <Select
                      value={toAccountId}
                      onChange={setToAccountId}
                      placeholder="Chọn tài khoản..."
                      options={[
                        { value: '', label: 'Chọn tài khoản...' },
                        ...accounts.filter(a => a.id !== accountId).map(a => ({ value: a.id, label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><BankLogo iconStr={a.icon} color="var(--text-primary)" size={20} /> {a.name}</span> }))
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
                          id={`cat-${cat.id}`}
                          onClick={() => setCategoryId(cat.id === categoryId ? '' : cat.id)}
                          style={{
                            padding: '8px 4px',
                            borderRadius: 8,
                            border: `1px solid ${categoryId === cat.id ? cat.color : 'var(--surface-border)'}`,
                            background: categoryId === cat.id ? `${cat.color}20` : 'var(--surface)',
                            cursor: 'pointer',
                            textAlign: 'center',
                            transition: 'all 0.15s',
                          }}
                        >
                          <div style={{ fontSize: 20, lineHeight: 1 }}>{cat.icon}</div>
                          <div style={{
                            fontSize: 10,
                            color: categoryId === cat.id ? cat.color : 'var(--text-secondary)',
                            marginTop: 4,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}>
                            {cat.name}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Date */}
                <div style={{ zIndex: 11 }}>
                  <label className="label" htmlFor="tx-date">Ngày</label>
                  <DatePicker
                    value={date}
                    onChange={setDate}
                    disableFuture={true}
                  />
                </div>
              </div>
            </div>

            <div className="drawer-footer">
              <button
                id="tx-save-add-btn"
                className="btn btn-secondary"
                onClick={() => handleSubmit(true)}
                disabled={!isValid || saving}
                style={{ flex: 'none' }}
              >
                Lưu & thêm tiếp
              </button>
              <button
                id="tx-save-btn"
                className="btn btn-primary"
                onClick={() => handleSubmit(false)}
                disabled={!isValid || saving}
                style={{ flex: 1 }}
              >
                {saving && !saveAndAdd ? 'Đang lưu...' : 'Lưu giao dịch'}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
