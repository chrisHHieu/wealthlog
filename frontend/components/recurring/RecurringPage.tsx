'use client'

import React, { useState, useEffect } from 'react'
import { PageTransition } from '@/components/ui/PageTransition'
import { PageHeader } from '@/components/ui/PageHeader'
import { ArrowLeftRight, Plus, Repeat, Settings2, Power, PowerOff, Trash2 } from 'lucide-react'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { formatVND, formatDateVI } from '@/lib/utils'
import { apiDelete, apiGet, apiJson } from '@/lib/api'
import { RecurringDrawer } from './RecurringDrawer'

interface RecurringItem {
  id: string
  type: string
  amount: number
  description?: string
  frequency: string
  daysOfWeek?: number[] | string | null
  nextRunDate: string
  accountName?: string
  categoryIcon?: string
  categoryColor?: string
  isActive: boolean
}

export function RecurringPage() {
  const [items, setItems] = useState<RecurringItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedItem, setSelectedItem] = useState<RecurringItem | null>(null)
  const [showDrawer, setShowDrawer] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const fetchItems = async () => {
    setIsLoading(true)
    try {
      setItems(await apiGet<RecurringItem[]>('/api/recurring'))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchItems()
  }, [])

  const toggleActive = async (id: string, current: boolean) => {
    await apiJson(`/api/recurring/${id}`, {
      method: 'PATCH',
      body: { isActive: !current },
    })
    fetchItems()
  }

  const handleDelete = async () => {
    if (!deleteId) return
    await apiDelete(`/api/recurring/${deleteId}`)
    setDeleteId(null)
    fetchItems()
  }

  const DAY_LABELS: Record<number, string> = { 0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat' }

  const freqLabel = (item: RecurringItem) => {
    if (item.daysOfWeek) {
      const days: number[] = Array.isArray(item.daysOfWeek) ? item.daysOfWeek : JSON.parse(item.daysOfWeek)
      return days.sort((a, b) => a - b).map(d => DAY_LABELS[d] ?? d).join(', ')
    }
    const map: Record<string, string> = { daily: 'Daily', weekly: 'Weekly', monthly: 'Monthly', yearly: 'Yearly' }
    return map[item.frequency] || item.frequency
  }

  return (
    <PageTransition>
    <div>
      {/* Header */}
      <PageHeader
        eyebrow="Scheduled"
        title="Recurring"
        subtitle={
          <>
            Automate fixed income and expenses.
            {items.length > 0 && (
              <span style={{ color: 'var(--text-tertiary)' }}> • {items.filter(i => i.isActive).length} active</span>
            )}
          </>
        }
        actions={
          <button
            className="btn btn-primary"
            onClick={() => { setSelectedItem(null); setShowDrawer(true) }}
          >
            <Plus size={16} /> Add new
          </button>
        }
      />

      {/* Content */}
      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[...Array(3)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 96, borderRadius: 'var(--radius-lg)' }} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state card" style={{ padding: '60px 24px' }}>
          <div className="icon-tile" style={{ width: 56, height: 56 }}>
            <Repeat size={26} />
          </div>
          <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 8 }}>No recurring transactions yet</div>
          <div style={{ fontSize: 13, color: 'var(--text-tertiary)', maxWidth: 360, margin: '0 auto' }}>
            Add rent, subscriptions, internet bills, salary, and other fixed items so the system can record them automatically.
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {items.map(item => (
            <div
              key={item.id}
              className="card"
              style={{
                padding: '16px 20px',
                borderLeft: `3px solid ${item.type.toLowerCase() === 'expense' ? 'var(--accent-red)' : item.type.toLowerCase() === 'income' ? 'var(--accent-green)' : 'var(--accent-blue)'}`,
                opacity: item.isActive ? 1 : 0.5,
                transition: 'opacity 0.2s',
              }}
            >
              {/* Row 1: Icon + Name + Frequency */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 10,
                  background: item.type === 'transfer' ? 'var(--accent-blue-subtle)' : `${item.categoryColor || '#888'}15`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 20, flexShrink: 0,
                }}>
                  {item.type === 'transfer'
                    ? <ArrowLeftRight size={18} style={{ color: 'var(--accent-blue)' }} />
                    : (item.categoryIcon || '📦')}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.description || 'Untitled'}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                    {freqLabel(item)} • Next: {formatDateVI(item.nextRunDate)}
                    {item.accountName && <span> • {item.accountName}</span>}
                  </div>
                </div>
              </div>

              {/* Row 2: Amount left + Actions right */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div className="num-meta" style={{
                  fontWeight: 700, fontSize: 15,
                  color: item.type.toLowerCase() === 'income' ? 'var(--accent-green)' : item.type.toLowerCase() === 'transfer' ? 'var(--accent-blue)' : 'var(--text-primary)',
                }}>
                  {item.type.toLowerCase() === 'income' ? '+' : item.type.toLowerCase() === 'expense' ? '-' : ''}{formatVND(item.amount)}
                </div>
                <div style={{ display: 'flex', gap: 2, flexShrink: 0 }}>
                  <button
                    onClick={() => toggleActive(item.id, item.isActive)}
                    className="btn-icon"
                    title={item.isActive ? 'Pause' : 'Activate'}
                    style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', color: item.isActive ? 'var(--accent-green)' : 'var(--text-tertiary)' }}
                  >
                    {item.isActive ? <Power size={15} /> : <PowerOff size={15} />}
                  </button>
                  <button
                    onClick={() => { setSelectedItem(item); setShowDrawer(true) }}
                    className="btn-icon"
                    title="Edit"
                    style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                  >
                    <Settings2 size={15} />
                  </button>
                  <button
                    onClick={() => setDeleteId(item.id)}
                    className="btn-icon"
                    title="Delete"
                    style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-red)' }}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showDrawer && (
        <RecurringDrawer
          item={selectedItem}
          onClose={() => setShowDrawer(false)}
          onSaved={() => {
            setShowDrawer(false)
            fetchItems()
          }}
        />
      )}

      <ConfirmModal
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={handleDelete}
        title="Delete recurring schedule?"
        description="This schedule will stop creating transactions. Existing transactions are kept."
      />
    </div>
    </PageTransition>
  )
}
