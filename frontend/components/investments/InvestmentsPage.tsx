'use client'

import { useState } from 'react'
import { PageTransition } from '@/components/ui/PageTransition'
import { Portal } from '@/components/ui/Portal'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, TrendingUp, TrendingDown, Edit2, Trash2 } from 'lucide-react'
import { useToast } from '@/components/ui/toaster'
import { formatVND, formatVNDCompact, formatDateVI, parseShorthandAmount, formatAmountLive, getToday } from '@/lib/utils'
import { API_URL } from '@/lib/api'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { Select } from '@/components/ui/Select'
import { DatePicker } from '@/components/ui/DatePicker'

interface Investment {
  id: string
  name: string
  type: string
  symbol?: string
  quantity: number
  buyPrice: number
  currentPrice: number
  buyDate: string
  note?: string
}

const INVESTMENT_TYPE_LABELS: Record<string, string> = {
  stock: '📊 Cổ phiếu',
  etf: '📈 ETF/Quỹ',
  gold: '🥇 Vàng',
  realestate: '🏠 Bất động sản',
  savings: '🏦 Tiết kiệm',
  crypto: '₿ Crypto',
  other: '💼 Khác',
}

const INVESTMENT_TYPES = Object.entries(INVESTMENT_TYPE_LABELS)
const INV_COLORS = ['#00C896', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899']

export function InvestmentsPage() {
  const { toast } = useToast()
  const qc = useQueryClient()

  const [showForm, setShowForm] = useState(false)
  const [editInv, setEditInv] = useState<Investment | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const [formName, setFormName] = useState('')
  const [formType, setFormType] = useState('stock')
  const [formSymbol, setFormSymbol] = useState('')
  const [formQty, setFormQty] = useState('1')
  const [formBuyPrice, setFormBuyPrice] = useState('')
  const [formCurrentPrice, setFormCurrentPrice] = useState('')
  const [formBuyDate, setFormBuyDate] = useState(getToday())
  const [formNote, setFormNote] = useState('')
  const [saving, setSaving] = useState(false)

  const { data: investments = [] } = useQuery<Investment[]>({
    queryKey: ['investments'],
    queryFn: () => fetch(`${API_URL}/api/investments`).then(r => r.json()),
  })

  const totalValue = investments.reduce((s, inv) => s + inv.currentPrice * inv.quantity, 0)
  const totalCost = investments.reduce((s, inv) => s + inv.buyPrice * inv.quantity, 0)
  const totalProfit = totalValue - totalCost
  const totalROI = totalCost > 0 ? ((totalProfit / totalCost) * 100).toFixed(2) : '0.00'

  // Group for pie chart
  const byType: Record<string, number> = {}
  investments.forEach(inv => {
    const v = inv.currentPrice * inv.quantity
    byType[inv.type] = (byType[inv.type] ?? 0) + v
  })
  const pieData = Object.entries(byType).map(([type, value], i) => ({
    name: INVESTMENT_TYPE_LABELS[type] ?? type,
    value,
    color: INV_COLORS[i % INV_COLORS.length],
  }))

  function openAdd() {
    setEditInv(null)
    setFormName(''); setFormType('stock'); setFormSymbol('')
    setFormQty('1'); setFormBuyPrice(''); setFormCurrentPrice('')
    setFormBuyDate(getToday()); setFormNote('')
    setShowForm(true)
  }

  function openEdit(inv: Investment) {
    setEditInv(inv)
    setFormName(inv.name); setFormType(inv.type); setFormSymbol(inv.symbol ?? '')
    setFormQty(String(inv.quantity)); setFormBuyPrice(String(inv.buyPrice))
    setFormCurrentPrice(String(inv.currentPrice)); setFormBuyDate(inv.buyDate); setFormNote(inv.note ?? '')
    setShowForm(true)
  }

  async function handleSave() {
    if (!formName.trim() || !formBuyPrice || !formCurrentPrice) return
    setSaving(true)
    try {
      const body = {
        name: formName.trim(),
        type: formType,
        symbol: formSymbol.trim() || undefined,
        quantity: parseFloat(formQty) || 1,
        buyPrice: parseShorthandAmount(formBuyPrice) || 0,
        currentPrice: parseShorthandAmount(formCurrentPrice) || 0,
        buyDate: formBuyDate,
        note: formNote.trim() || undefined,
      }

      if (editInv) {
        await fetch(`${API_URL}/api/investments/${editInv.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        toast('Đã cập nhật tài sản')
      } else {
        await fetch(`${API_URL}/api/investments`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        toast('Đã thêm tài sản đầu tư')
      }

      await qc.invalidateQueries({ queryKey: ['investments'] })
      setShowForm(false)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    await fetch(`${API_URL}/api/investments/${id}`, { method: 'DELETE' })
    await qc.invalidateQueries({ queryKey: ['investments'] })
    setDeleteConfirm(null)
    toast('Đã xóa tài sản')
  }

  return (
    <PageTransition>
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Đầu tư</h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{investments.length} tài sản đầu tư</p>
        </div>
        <button id="add-investment-btn" onClick={openAdd} className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Plus size={15} /> Thêm tài sản
        </button>
      </div>

      {/* Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 24 }}>
        <div className="kpi-card" style={{ background: 'linear-gradient(135deg, rgba(0,200,150,0.08), transparent)', borderColor: 'rgba(0,200,150,0.2)' }}>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>Tổng giá trị hiện tại</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--accent-green)' }}>{formatVNDCompact(totalValue)}</div>
        </div>
        <div className="kpi-card" style={{
          background: `linear-gradient(135deg, ${totalProfit >= 0 ? 'rgba(0,200,150,0.08)' : 'rgba(255,77,109,0.08)'}, transparent)`,
          borderColor: totalProfit >= 0 ? 'rgba(0,200,150,0.2)' : 'rgba(255,77,109,0.2)',
        }}>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>Lãi/Lỗ tổng</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {totalProfit >= 0 ? <TrendingUp size={18} style={{ color: 'var(--accent-green)' }} /> : <TrendingDown size={18} style={{ color: 'var(--accent-red)' }} />}
            <div style={{ fontSize: 22, fontWeight: 700, color: totalProfit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
              {totalProfit >= 0 ? '+' : ''}{formatVNDCompact(totalProfit)}
            </div>
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 4 }}>
            ROI: {parseFloat(totalROI) >= 0 ? '+' : ''}{totalROI}%
          </div>
        </div>
        <div className="kpi-card">
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>Vốn đầu tư</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>{formatVNDCompact(totalCost)}</div>
        </div>
      </div>

      {investments.length === 0 ? (
        <div className="empty-state card" style={{ padding: '60px 24px' }}>
          <span style={{ fontSize: 56 }}>📈</span>
          <p style={{ fontSize: 16, fontWeight: 600 }}>Chưa có tài sản đầu tư nào</p>
          <p style={{ fontSize: 13 }}>Thêm cổ phiếu, vàng, ETF... để theo dõi danh mục đầu tư</p>
          <button className="btn btn-primary" onClick={openAdd} style={{ marginTop: 12 }}><Plus size={15} /> Thêm tài sản đầu tư</button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20 }}>
          {/* Table */}
          <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Tài sản</th>
                  <th>Số lượng</th>
                  <th>Giá mua → Hiện tại</th>
                  <th>Tổng hiện tại</th>
                  <th>Lãi/Lỗ</th>
                  <th>ROI</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {investments.map(inv => {
                  const cost = inv.buyPrice * inv.quantity
                  const value = inv.currentPrice * inv.quantity
                  const profit = value - cost
                  const roi = cost > 0 ? ((profit / cost) * 100).toFixed(1) : '0.0'

                  return (
                    <tr key={inv.id}>
                      <td>
                        <div style={{ fontWeight: 600, fontSize: 13 }}>
                          {inv.symbol && <span style={{ fontSize: 11, color: 'var(--accent-green)', marginRight: 4 }}>{inv.symbol}</span>}
                          {inv.name}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                          {INVESTMENT_TYPE_LABELS[inv.type]} · Mua {formatDateVI(inv.buyDate)}
                        </div>
                      </td>
                      <td style={{ fontSize: 13 }}>{inv.quantity.toLocaleString()}</td>
                      <td style={{ fontSize: 12 }}>
                        <div style={{ color: 'var(--text-secondary)' }}>{formatVNDCompact(inv.buyPrice)}</div>
                        <div style={{ color: 'var(--text-primary)', fontWeight: 500 }}>→ {formatVNDCompact(inv.currentPrice)}</div>
                      </td>
                      <td style={{ fontSize: 13, fontWeight: 600 }}>{formatVNDCompact(value)}</td>
                      <td style={{ fontSize: 13, fontWeight: 600, color: profit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                        {profit >= 0 ? '+' : ''}{formatVNDCompact(profit)}
                      </td>
                      <td>
                        <span className={`badge ${parseFloat(roi) >= 0 ? 'badge-green' : 'badge-red'}`}>
                          {parseFloat(roi) >= 0 ? '+' : ''}{roi}%
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: 4 }}>
                          <button onClick={() => openEdit(inv)} className="btn btn-ghost btn-sm" style={{ width: 28, height: 28, padding: 0, borderRadius: '50%' }}><Edit2 size={13} /></button>
                          <button onClick={() => setDeleteConfirm(inv.id)} className="btn btn-ghost btn-sm" style={{ width: 28, height: 28, padding: 0, borderRadius: '50%', color: 'var(--accent-red)' }}><Trash2 size={13} /></button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Allocation Pie */}
          <div className="card" style={{ padding: '20px' }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 16 }}>Phân bổ danh mục</div>
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={2} dataKey="value">
                  {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip cursor={{ fill: 'transparent' }} formatter={(v) => [formatVND(Number(v)), '']} contentStyle={{ background: 'var(--bg-tertiary)', border: '1px solid var(--surface-border)', borderRadius: 8, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
              {pieData.map((p, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: p.color, flexShrink: 0 }} />
                  <span style={{ flex: 1, color: 'var(--text-secondary)' }}>{p.name}</span>
                  <span style={{ fontWeight: 600 }}>{totalValue > 0 ? ((p.value / totalValue) * 100).toFixed(1) : 0}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Form Drawer */}
      <Portal>
      <AnimatePresence>
        {showForm && (
          <>
            <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowForm(false)} />
            <motion.div className="drawer" style={{ height: '100dvh', display: 'flex', flexDirection: 'column' }} initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', stiffness: 300, damping: 30 }}>
              <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--surface-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <h2 style={{ fontSize: 17, fontWeight: 600 }}>{editInv ? 'Sửa tài sản' : 'Thêm tài sản đầu tư'}</h2>
                <button onClick={() => setShowForm(false)} className="btn btn-ghost" style={{ width: 32, height: 32, padding: 0, borderRadius: '50%' }}>✕</button>
              </div>

              <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div style={{ zIndex: 10 }}>
                  <label className="label">Loại tài sản</label>
                  <Select
                    value={formType}
                    onChange={setFormType}
                    options={INVESTMENT_TYPES.map(([key, label]) => ({ value: key, label }))}
                  />
                </div>
                <div>
                  <label className="label">Tên tài sản</label>
                  <input type="text" value={formName} onChange={e => setFormName(e.target.value)} placeholder="VD: FPT Corporation" className="input" />
                </div>
                <div>
                  <label className="label">Mã chứng khoán (tuỳ chọn)</label>
                  <input type="text" value={formSymbol} onChange={e => setFormSymbol(e.target.value)} placeholder="VD: FPT" className="input" />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div>
                    <label className="label">Số lượng</label>
                    <input type="number" value={formQty} onChange={e => setFormQty(e.target.value)} className="input" />
                  </div>
                  <div style={{ zIndex: 9 }}>
                    <label className="label">Ngày mua</label>
                    <DatePicker value={formBuyDate} onChange={setFormBuyDate} disableFuture={true} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div>
                    <label className="label">Giá mua (đ)</label>
                    <input type="text" value={formBuyPrice} onChange={e => setFormBuyPrice(formatAmountLive(e.target.value))} placeholder="0" className="input" />
                  </div>
                  <div>
                    <label className="label">Giá hiện tại (đ)</label>
                    <input type="text" value={formCurrentPrice} onChange={e => setFormCurrentPrice(formatAmountLive(e.target.value))} placeholder="0" className="input" />
                  </div>
                </div>
                <div>
                  <label className="label">Ghi chú</label>
                  <textarea value={formNote} onChange={e => setFormNote(e.target.value)} className="input" rows={2} style={{ resize: 'vertical' }} />
                </div>
              </div>

              <div className="drawer-footer">
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setShowForm(false)}>Hủy</button>
                <button className="btn btn-primary" style={{ flex: 2 }} onClick={handleSave} disabled={saving || !formName.trim() || !formBuyPrice || !formCurrentPrice}>
                  {saving ? 'Đang lưu...' : editInv ? 'Cập nhật' : 'Thêm tài sản'}
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
      </Portal>

      {/* Delete Confirm */}
      <Portal>
      <AnimatePresence>
        {deleteConfirm && (
          <>
            <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setDeleteConfirm(null)} />
            <motion.div className="modal" style={{ padding: '28px', textAlign: 'center' }} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>⚠️</div>
              <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 8 }}>Xóa tài sản đầu tư?</h3>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24 }}>Hành động này không thể hoàn tác.</p>
              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setDeleteConfirm(null)}>Hủy</button>
                <button className="btn btn-danger" style={{ flex: 1 }} onClick={() => handleDelete(deleteConfirm)}>Xóa</button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
      </Portal>
    </div>
    </PageTransition>
  )
}
