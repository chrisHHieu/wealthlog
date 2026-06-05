'use client'

import { useState } from 'react'
import { PageTransition } from '@/components/ui/PageTransition'
import { Portal } from '@/components/ui/Portal'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, ChevronLeft, ChevronRight, Target, Trash2, Edit2 } from 'lucide-react'
import { useToast } from '@/components/ui/toaster'
import { formatVND, formatVNDCompact, formatMonthVI, getCurrentMonth, getDaysRemaining, parseShorthandAmount, formatAmountLive } from '@/lib/utils'
import { apiDelete, apiGet, apiJson, queryKeys } from '@/lib/api'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { Select } from '@/components/ui/Select'

interface BudgetItem {
  id: string
  categoryId: string
  categoryName: string
  categoryIcon: string
  categoryColor: string
  amount: number
  month: string
  spent?: number
}

interface Category {
  id: string
  name: string
  icon: string
  color: string
  type: string
}

interface Transaction {
  id: string
  type: string
  amount: number
  categoryId?: string
  date: string
}

function prevMonth(yyyymm: string) {
  const [y, m] = yyyymm.split('-').map(Number)
  const d = new Date(y, m - 2, 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function nextMonth(yyyymm: string) {
  const [y, m] = yyyymm.split('-').map(Number)
  const d = new Date(y, m, 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function progressColor(pct: number) {
  if (pct >= 100) return 'var(--accent-red)'
  if (pct >= 90) return '#f97316'
  if (pct >= 70) return 'var(--accent-yellow)'
  return 'var(--accent-green)'
}

export function BudgetPage() {
  const { toast } = useToast()
  const qc = useQueryClient()

  const [month, setMonth] = useState(getCurrentMonth())
  const [showForm, setShowForm] = useState(false)
  const [formCategoryId, setFormCategoryId] = useState('')
  const [formAmount, setFormAmount] = useState('')
  const [saving, setSaving] = useState(false)

  const { data: budgets = [] } = useQuery<BudgetItem[]>({
    queryKey: queryKeys.budget(month),
    queryFn: () => apiGet<BudgetItem[]>('/api/budgets', { month }),
  })

  const { data: transactions = [] } = useQuery<Transaction[]>({
    queryKey: ['transactions', 'budget', month],
    queryFn: () => apiGet<Transaction[]>('/api/transactions', {
      startDate: `${month}-01`,
      endDate: `${month}-31`,
    }),
  })

  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: queryKeys.categories(),
    queryFn: () => apiGet<Category[]>('/api/categories'),
  })

  // Calculate spending per category this month
  const spendingMap: Record<string, number> = {}
  transactions.filter(t => t.type === 'expense').forEach(t => {
    if (t.categoryId) spendingMap[t.categoryId] = (spendingMap[t.categoryId] ?? 0) + t.amount
  })

  const budgetsWithSpent = budgets.map(b => ({
    ...b,
    spent: spendingMap[b.categoryId] ?? 0,
  }))

  const totalBudget = budgetsWithSpent.reduce((s, b) => s + b.amount, 0)
  const totalSpent = budgetsWithSpent.reduce((s, b) => s + b.spent, 0)
  const daysInMonth = new Date(parseInt(month.split('-')[0]), parseInt(month.split('-')[1]), 0).getDate()
  const today = new Date()
  const daysLeft = getDaysRemaining(`${month}-${daysInMonth}`)
  const isCurrentMonth = month === getCurrentMonth()

  const chartData = budgetsWithSpent.map(b => ({
    name: `${b.categoryIcon} ${b.categoryName}`,
    'Budget': b.amount,
    'Spent': b.spent,
  }))

  const expenseCategories = categories.filter(c => c.type === 'expense' || c.type === 'both')
  const setBudgetCategories = new Set(budgets.map(b => b.categoryId))

  async function handleSave() {
    if (!formCategoryId || !formAmount) return
    setSaving(true)
    try {
      await apiJson('/api/budgets', {
        method: 'POST',
        body: { categoryId: formCategoryId, amount: parseShorthandAmount(formAmount) || 0, month },
      })
      await qc.invalidateQueries({ queryKey: ['budgets'] })
      toast('Budget set')
      setShowForm(false)
      setFormAmount('')
      setFormCategoryId('')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    await apiDelete(`/api/budgets?id=${id}`)
    await qc.invalidateQueries({ queryKey: ['budgets'] })
    toast('Budget deleted')
  }

  return (
    <PageTransition>
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Budget</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 13, color: 'var(--text-secondary)' }}>
            <button onClick={() => setMonth(prevMonth(month))} className="btn btn-ghost btn-sm" style={{ padding: '2px 6px' }}>
              <ChevronLeft size={16} />
            </button>
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{formatMonthVI(month)}</span>
            <button 
              onClick={() => month >= getCurrentMonth() ? null : setMonth(nextMonth(month))} 
              className="btn btn-ghost btn-sm" 
              style={{ padding: '2px 6px', opacity: month >= getCurrentMonth() ? 0.3 : 1 }}
              disabled={month >= getCurrentMonth()}
            >
              <ChevronRight size={16} />
            </button>
            {isCurrentMonth && (
              <span style={{ fontSize: 12, color: 'var(--accent-yellow)' }}>🕒 Left {daysLeft} days</span>
            )}
          </div>
        </div>
        <button id="add-budget-btn" onClick={() => setShowForm(true)} className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Plus size={15} /> Set budget
        </button>
      </div>

      {/* Summary */}
      <div className="budget-summary-grid">
        <div className="kpi-card">
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>Total budget</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>{formatVNDCompact(totalBudget)}</div>
        </div>
        <div className="kpi-card">
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>Spent</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--accent-red)' }}>{formatVNDCompact(totalSpent)}</div>
        </div>
        <div className="kpi-card">
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>Remaining</div>
          <div style={{
            fontSize: 22, fontWeight: 700,
            color: totalBudget - totalSpent >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'
          }}>
            {formatVNDCompact(totalBudget - totalSpent)}
          </div>
        </div>
      </div>

      {/* Budget Alerts */}
      {(() => {
        const exceeded = budgetsWithSpent.filter(b => b.spent > b.amount)
        const nearLimit = budgetsWithSpent.filter(b => {
          const pct = b.amount > 0 ? (b.spent / b.amount) * 100 : 0
          return pct >= 80 && pct < 100
        })
        if (exceeded.length === 0 && nearLimit.length === 0) return null
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>
            {exceeded.map(b => (
              <motion.div
                key={`alert-${b.id}`}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  background: 'rgba(255, 77, 109, 0.08)',
                  border: '1px solid rgba(255, 77, 109, 0.3)',
                  borderRadius: 12,
                  padding: '14px 18px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                }}
              >
                <div style={{
                  width: 36, height: 36, borderRadius: 10,
                  background: 'rgba(255, 77, 109, 0.15)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 18, flexShrink: 0,
                }}>
                  {b.categoryIcon}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent-red)', marginBottom: 2 }}>
                    🚨 Budget exceeded {b.categoryName}!
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    Spent {formatVND(b.spent)} / {formatVND(b.amount)} — over {formatVND(b.spent - b.amount)}
                  </div>
                </div>
                <div style={{
                  fontSize: 20, fontWeight: 800, color: 'var(--accent-red)',
                  fontVariantNumeric: 'tabular-nums',
                }}>
                  {b.amount > 0 ? Math.round((b.spent / b.amount) * 100) : 0}%
                </div>
              </motion.div>
            ))}
            {nearLimit.map(b => {
              const pct = b.amount > 0 ? Math.round((b.spent / b.amount) * 100) : 0
              return (
                <motion.div
                  key={`warn-${b.id}`}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  style={{
                    background: 'rgba(249, 115, 22, 0.08)',
                    border: '1px solid rgba(249, 115, 22, 0.25)',
                    borderRadius: 12,
                    padding: '14px 18px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                  }}
                >
                  <div style={{
                    width: 36, height: 36, borderRadius: 10,
                    background: 'rgba(249, 115, 22, 0.15)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 18, flexShrink: 0,
                  }}>
                    {b.categoryIcon}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#f97316', marginBottom: 2 }}>
                      ⚡ Budget almost used {b.categoryName}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      Left {formatVND(b.amount - b.spent)} - spent {pct}%
                    </div>
                  </div>
                  <div style={{
                    fontSize: 20, fontWeight: 800, color: '#f97316',
                    fontVariantNumeric: 'tabular-nums',
                  }}>
                    {pct}%
                  </div>
                </motion.div>
              )
            })}
          </div>
        )
      })()}

      {/* Budget list */}
      {budgetsWithSpent.length === 0 ? (
        <div className="empty-state card" style={{ padding: '48px 24px' }}>
          <span style={{ fontSize: 48 }}>📊</span>
          <p style={{ fontSize: 15, fontWeight: 600 }}>No budgets yet</p>
          <p style={{ fontSize: 13 }}>Set budgets to track spending</p>
          <button className="btn btn-primary" onClick={() => setShowForm(true)} style={{ marginTop: 8 }}>
            <Plus size={15} /> Set budget
          </button>
        </div>
      ) : (
        <div className="budget-content-grid">
          {/* Budget List */}
          <div className="card" style={{ padding: '20px' }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 16 }}>Expense details by category</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {budgetsWithSpent.map(b => {
                const pct = b.amount > 0 ? (b.spent / b.amount) * 100 : 0
                const color = progressColor(pct)
                const isOver = pct >= 100
                return (
                  <div key={b.id}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                      <div style={{
                        width: 32, height: 32, borderRadius: 8,
                        background: `${b.categoryColor}20`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 16, flexShrink: 0,
                      }}>
                        {b.categoryIcon}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                          <span style={{ fontSize: 13, fontWeight: 500 }}>{b.categoryName}</span>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ fontSize: 12, fontWeight: 600, color }}>
                              {pct.toFixed(0)}%
                              {isOver && ' 🔴'}
                            </span>
                            <button
                              onClick={() => handleDelete(b.id)}
                              className="btn btn-ghost btn-sm"
                              style={{ width: 22, height: 22, padding: 0, borderRadius: '50%', color: 'var(--text-tertiary)' }}
                            >
                              <Trash2 size={11} />
                            </button>
                          </div>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 6 }}>
                          <span>{formatVND(b.spent)} / {formatVND(b.amount)}</span>
                          <span style={{ color: color }}>left {formatVND(Math.max(0, b.amount - b.spent))}</span>
                        </div>
                        <div className="progress-bar">
                          <motion.div
                            className="progress-bar-fill"
                            style={{
                              background: isOver
                                ? `linear-gradient(90deg, var(--accent-red), #ff6b8a)`
                                : color,
                              animation: isOver ? 'pulse 1s infinite' : undefined,
                            }}
                            initial={{ width: 0 }}
                            animate={{ width: `${Math.min(pct, 100)}%` }}
                            transition={{ duration: 0.8, ease: 'easeOut', delay: 0.2 }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Bar Chart */}
          <div className="card" style={{ padding: '20px', height: '100%' }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 16 }}>Budget vs actual spending</div>
            <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 60)}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 0, right: 20, top: 0, bottom: 0 }} barGap={4} barCategoryGap="25%">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--surface-border)" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }} tickFormatter={v => formatVNDCompact(v)} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} width={200} />
                <Tooltip
                  cursor={{ fill: 'transparent' }}
                  formatter={(v, name) => [formatVND(Number(v ?? 0)), String(name)]}
                  contentStyle={{ background: 'var(--bg-tertiary)', border: '1px solid var(--surface-border)', borderRadius: 8, fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Budget" fill="rgba(61,142,248,0.6)" radius={[0, 4, 4, 0]} maxBarSize={20} />
                <Bar dataKey="Spent" fill="rgba(255,77,109,0.8)" radius={[0, 4, 4, 0]} maxBarSize={20} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Add Form Modal */}
      <Portal>
      <AnimatePresence>
        {showForm && (
          <>
            <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowForm(false)} />
            <motion.div className="modal" style={{ padding: '28px' }} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}>
              <h3 style={{ fontSize: 17, fontWeight: 600, marginBottom: 20 }}>Set budget — {formatMonthVI(month)}</h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div style={{ zIndex: 10 }}>
                  <label className="label">Category</label>
                  <Select
                    value={formCategoryId}
                    onChange={setFormCategoryId}
                    placeholder="Select category..."
                    options={[
                      { value: '', label: 'Select category...' },
                      ...expenseCategories.map(c => ({
                        value: c.id,
                        label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>{c.icon} {c.name} <span style={{color: 'var(--text-tertiary)'}}>{setBudgetCategories.has(c.id) ? '(budget already set)' : ''}</span></span>
                      }))
                    ]}
                  />
                </div>
                <div>
                  <label className="label">Budget (VND)</label>
                  <input type="text" value={formAmount} onChange={e => setFormAmount(formatAmountLive(e.target.value))} placeholder="Example: 3,000,000" className="input" />
                </div>
              </div>

              <div style={{ display: 'flex', gap: 10, marginTop: 24 }}>
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setShowForm(false)}>Cancel</button>
                <button className="btn btn-primary" style={{ flex: 2 }} onClick={handleSave} disabled={saving || !formCategoryId || !formAmount}>
                  {saving ? 'Saving...' : 'Set budget'}
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
      </Portal>
      <style jsx>{`
        .budget-summary-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 16px;
          margin-bottom: 24px;
        }

        .budget-content-grid {
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
          gap: 24px;
        }

        @media (max-width: 1180px) {
          .budget-content-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
    </PageTransition>
  )
}
