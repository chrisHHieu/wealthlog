'use client'

import React, { useState, useEffect } from 'react'
import { PageTransition } from '@/components/ui/PageTransition'
import { Plus, Settings2, Power, PowerOff, Loader2, Trash2 } from 'lucide-react'
import { formatVND, formatDateVI } from '@/lib/utils'
import { API_URL } from '@/lib/api'
import { RecurringDrawer } from './RecurringDrawer'

export function RecurringPage() {
  const [items, setItems] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedItem, setSelectedItem] = useState<any | null>(null)
  const [showDrawer, setShowDrawer] = useState(false)

  const fetchItems = async () => {
    setIsLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/recurring`)
      if (res.ok) {
        setItems(await res.json())
      }
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchItems()
  }, [])

  const toggleActive = async (id: string, current: boolean) => {
    await fetch(`${API_URL}/api/recurring/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ isActive: !current }),
    })
    fetchItems()
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Bạn có chắc muốn xóa lịch định kỳ này?')) return
    await fetch(`${API_URL}/api/recurring/${id}`, { method: 'DELETE' })
    fetchItems()
  }

  const DAYS_VI: Record<number, string> = { 0: 'CN', 1: 'T2', 2: 'T3', 3: 'T4', 4: 'T5', 5: 'T6', 6: 'T7' }

  const freqLabel = (item: any) => {
    if (item.daysOfWeek) {
      const days: number[] = Array.isArray(item.daysOfWeek) ? item.daysOfWeek : JSON.parse(item.daysOfWeek)
      return days.sort((a, b) => a - b).map(d => DAYS_VI[d] ?? d).join(', ')
    }
    const map: Record<string, string> = { daily: 'Hàng ngày', weekly: 'Hàng tuần', monthly: 'Hàng tháng', yearly: 'Hàng năm' }
    return map[item.frequency] || item.frequency
  }

  return (
    <PageTransition>
    <div>
      {/* Header — matches TransactionsPage style */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700 }}>Giao dịch định kỳ</h1>
          <button
            className="btn btn-primary"
            onClick={() => { setSelectedItem(null); setShowDrawer(true) }}
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <Plus size={16} /> Thêm mới
          </button>
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          Tự động hóa các khoản thu chi cố định.
          {items.length > 0 && (
            <span style={{ color: 'var(--text-tertiary)' }}> • {items.filter(i => i.isActive).length} đang hoạt động</span>
          )}
        </p>
      </div>

      {/* Content */}
      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
          <Loader2 className="spinner" size={24} style={{ color: 'var(--text-tertiary)' }} />
        </div>
      ) : items.length === 0 ? (
        <div className="card" style={{ padding: '60px 24px', textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>📅</div>
          <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 8 }}>Chưa có giao dịch lặp lại</div>
          <div style={{ fontSize: 13, color: 'var(--text-tertiary)', maxWidth: 360, margin: '0 auto' }}>
            Thêm tiền nhà, Netflix, tiền mạng, lương... để hệ thống tự động ghi nhận mỗi tháng.
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
                  background: item.type === 'transfer' ? 'rgba(61,142,248,0.1)' : `${item.categoryColor || '#888'}15`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 20, flexShrink: 0,
                }}>
                  {item.type === 'transfer' ? '↔️' : (item.categoryIcon || '📦')}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.description || 'Không tên'}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                    {freqLabel(item)} • Kế tiếp: {formatDateVI(item.nextRunDate)}
                    {item.accountName && <span> • {item.accountName}</span>}
                  </div>
                </div>
              </div>

              {/* Row 2: Amount left + Actions right */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{
                  fontWeight: 700, fontSize: 15,
                  color: item.type.toLowerCase() === 'income' ? 'var(--accent-green)' : item.type.toLowerCase() === 'transfer' ? 'var(--accent-blue)' : 'var(--text-primary)',
                }}>
                  {item.type.toLowerCase() === 'income' ? '+' : item.type.toLowerCase() === 'expense' ? '-' : ''}{formatVND(item.amount)}
                </div>
                <div style={{ display: 'flex', gap: 2, flexShrink: 0 }}>
                  <button
                    onClick={() => toggleActive(item.id, item.isActive)}
                    className="btn-icon"
                    title={item.isActive ? 'Tạm dừng' : 'Kích hoạt'}
                    style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', color: item.isActive ? 'var(--accent-green)' : 'var(--text-tertiary)' }}
                  >
                    {item.isActive ? <Power size={15} /> : <PowerOff size={15} />}
                  </button>
                  <button
                    onClick={() => { setSelectedItem(item); setShowDrawer(true) }}
                    className="btn-icon"
                    title="Chỉnh sửa"
                    style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                  >
                    <Settings2 size={15} />
                  </button>
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="btn-icon"
                    title="Xóa"
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
    </div>
    </PageTransition>
  )
}
