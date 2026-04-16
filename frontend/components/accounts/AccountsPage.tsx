'use client'

import { useState } from 'react'
import { PageTransition } from '@/components/ui/PageTransition'
import { Portal } from '@/components/ui/Portal'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Edit2, Trash2, Archive, History, RefreshCw } from 'lucide-react'
import { useToast } from '@/components/ui/toaster'
import { formatVND, formatVNDCompact, parseShorthandAmount, formatAmountLive } from '@/lib/utils'
import { API_URL } from '@/lib/api'
import { AnimatedCounter } from '@/components/ui/AnimatedCounter'
import { Select } from '@/components/ui/Select'
import { BankLogo } from '@/components/ui/BankLogo'
import { useRouter } from 'next/navigation'

interface Account {
  id: string
  name: string
  type: string
  balance: number
  color: string
  icon: string
  description?: string
  isActive: boolean
}

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  cash: 'Tiền mặt',
  bank: 'Ngân hàng',
  ewallet: 'Ví điện tử',
  investment: 'Đầu tư',
  savings: 'Tiết kiệm',
  debt: 'Nợ/Vay',
}

const ACCOUNT_GROUPS = [
  { key: 'cash', label: 'Tiền mặt' },
  { key: 'bank', label: 'Ngân hàng' },
  { key: 'ewallet', label: 'Ví điện tử' },
  { key: 'investment', label: 'Đầu tư' },
  { key: 'savings', label: 'Tiết kiệm' },
  { key: 'debt', label: 'Nợ/Vay' },
]

const ICON_OPTIONS = ['💵', '💳', '🏦', 'VCB', 'TCB', 'MB', 'VPB', 'MOMO']
const COLOR_OPTIONS = ['#00C896', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#d946ef']

export function AccountsPage() {
  const { toast } = useToast()
  const qc = useQueryClient()
  const router = useRouter()

  const [showForm, setShowForm] = useState(false)
  const [editAccount, setEditAccount] = useState<Account | null>(null)
  const [archiveConfirm, setArchiveConfirm] = useState<Account | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<Account | null>(null)
  const [showArchived, setShowArchived] = useState(false)
  
  const [formName, setFormName] = useState('')
  const [formType, setFormType] = useState('bank')
  const [formBalance, setFormBalance] = useState('0')
  const [formColor, setFormColor] = useState('#00C896')
  const [formIcon, setFormIcon] = useState('💳')
  const [formDesc, setFormDesc] = useState('')
  const [saving, setSaving] = useState(false)

  const { data: accounts = [], isLoading } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: () => fetch(`${API_URL}/api/accounts`).then(r => r.json()),
  })

  const activeAccounts = accounts.filter(a => a.isActive)
  const archivedAccounts = accounts.filter(a => !a.isActive)

  const totalAssets = activeAccounts.filter(a => a.type !== 'debt').reduce((s, a) => s + a.balance, 0)
  const totalDebt = activeAccounts.filter(a => a.type === 'debt').reduce((s, a) => s + Math.abs(a.balance), 0)
  const netWorth = totalAssets - totalDebt

  function openAdd() {
    setEditAccount(null)
    setFormName('')
    setFormType('bank')
    setFormBalance('0')
    setFormColor('#00C896')
    setFormIcon('💳')
    setFormDesc('')
    setShowForm(true)
  }

  function openEdit(e: React.MouseEvent, acc: Account) {
    e.stopPropagation()
    setEditAccount(acc)
    setFormName(acc.name)
    setFormType(acc.type)
    setFormBalance(String(acc.balance))
    setFormColor(acc.color)
    setFormIcon(acc.icon)
    setFormDesc(acc.description || '')
    setShowForm(true)
  }

    // We no longer need renderIcon since BankLogo handles it!

  async function handleSave() {
    if (!formName.trim()) return
    setSaving(true)
    try {
      const body = {
        name: formName.trim(),
        type: formType,
        balance: parseShorthandAmount(formBalance) || 0,
        color: formColor,
        icon: formIcon,
        description: formDesc.trim() || null,
        isActive: editAccount ? editAccount.isActive : true
      }

      if (editAccount) {
        await fetch(`${API_URL}/api/accounts/${editAccount.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        toast('Đã cập nhật tài khoản')
      } else {
        await fetch(`${API_URL}/api/accounts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        toast('Đã tạo tài khoản mới')
      }

      await qc.invalidateQueries({ queryKey: ['accounts'] })
      await qc.invalidateQueries({ queryKey: ['dashboard'] })
      setShowForm(false)
    } finally {
      setSaving(false)
    }
  }

  async function handleArchiveToggle(acc: Account) {
    const isNowActive = !acc.isActive
    await fetch(`${API_URL}/api/accounts/${acc.id}`, { 
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...acc, isActive: isNowActive })
    })
    await qc.invalidateQueries({ queryKey: ['accounts'] })
    await qc.invalidateQueries({ queryKey: ['dashboard'] })
    setArchiveConfirm(null)
    toast(isNowActive ? 'Đã khôi phục tài khoản' : 'Đã lưu trữ tài khoản')
  }

  async function handleDelete() {
    if (!deleteConfirm) return
    await fetch(`${API_URL}/api/accounts/${deleteConfirm.id}`, { method: 'DELETE' })
    await qc.invalidateQueries({ queryKey: ['accounts'] })
    await qc.invalidateQueries({ queryKey: ['dashboard'] })
    toast('Đã xóa tài khoản')
    setDeleteConfirm(null)
  }

  function handleCardClick(accId: string) {
    router.push(`/transactions?accountId=${accId}`)
  }

  function navigateTransfer() {
    // Navigating to transaction page with a "transfer" prepopulate signal
    router.push('/transactions?action=transfer')
  }

  return (
    <PageTransition>
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Tài khoản</h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{activeAccounts.length} tài khoản đang hoạt động</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={navigateTransfer} className="btn btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <RefreshCw size={15} /> Chuyển tiền
          </button>
          <button id="add-account-btn" onClick={openAdd} className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Plus size={15} /> Thêm tài khoản
          </button>
        </div>
      </div>

      {/* Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
        <div className="card" style={{ padding: '20px', background: 'linear-gradient(135deg, rgba(0,200,150,0.08), transparent)', borderColor: 'rgba(0,200,150,0.2)' }}>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>Tổng tài sản</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--accent-green)' }}>
            <AnimatedCounter value={totalAssets} format={v => formatVNDCompact(Math.round(v))} />
          </div>
        </div>
        <div className="card" style={{ padding: '20px', background: 'linear-gradient(135deg, rgba(255,77,109,0.08), transparent)', borderColor: 'rgba(255,77,109,0.2)' }}>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>Tổng nợ</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--accent-red)' }}>
            <AnimatedCounter value={totalDebt} format={v => formatVNDCompact(Math.round(v))} />
          </div>
        </div>
        <div className="card" style={{ padding: '20px', background: 'linear-gradient(135deg, rgba(61,142,248,0.08), transparent)', borderColor: 'rgba(61,142,248,0.2)' }}>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>Tài sản ròng</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--accent-blue)' }}>
            <AnimatedCounter value={netWorth} format={v => formatVNDCompact(Math.round(v))} />
          </div>
        </div>
      </div>

      {/* Account groups */}
      {isLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 120, borderRadius: 16 }} />
          ))}
        </div>
      ) : activeAccounts.length === 0 ? (
        <div className="empty-state card" style={{ padding: '48px 24px' }}>
          <span style={{ fontSize: 48 }}>💳</span>
          <p style={{ fontSize: 15, fontWeight: 600 }}>Chưa có tài khoản nào</p>
          <button className="btn btn-primary" onClick={openAdd} style={{ marginTop: 8 }}>
            <Plus size={15} /> Thêm tài khoản đầu tiên
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {ACCOUNT_GROUPS.map(group => {
            const groupAccounts = activeAccounts.filter(a => a.type === group.key)
            if (groupAccounts.length === 0) return null
            return (
              <div key={group.key}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
                  {group.label}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
                  {groupAccounts.map(acc => (
                    <motion.div
                      key={acc.id}
                      onClick={() => handleCardClick(acc.id)}
                      className="card"
                      style={{ padding: '20px', cursor: 'pointer', borderLeft: `3px solid ${acc.color}` }}
                      whileHover={{ scale: 1.01, boxShadow: `0 4px 24px ${acc.color}20, var(--shadow-card)` }}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                        <BankLogo iconStr={acc.icon} color={acc.color} size={40} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 14, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{acc.name}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                            {ACCOUNT_TYPE_LABELS[acc.type]} {acc.description ? `• ${acc.description}` : ''}
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ fontSize: 20, fontWeight: 700, color: acc.balance >= 0 ? 'var(--text-primary)' : 'var(--accent-red)' }}>
                          {formatVND(acc.balance)}
                        </div>
                        <div style={{ display: 'flex', gap: 2, flexShrink: 0 }}>
                          <button onClick={(e) => openEdit(e, acc)} className="btn btn-ghost btn-sm" style={{ width: 32, height: 32, padding: 0, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }} title="Sửa"><Edit2 size={14} /></button>
                          <button onClick={(e) => { e.stopPropagation(); setArchiveConfirm(acc) }} className="btn btn-ghost btn-sm" style={{ width: 32, height: 32, padding: 0, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)' }} title="Lưu trữ"><Archive size={14} /></button>
                          <button onClick={(e) => { e.stopPropagation(); setDeleteConfirm(acc) }} className="btn btn-ghost btn-sm" style={{ width: 32, height: 32, padding: 0, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-red)' }} title="Xóa"><Trash2 size={14} /></button>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Archived Toggle */}
      {archivedAccounts.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <button onClick={() => setShowArchived(!showArchived)} className="btn btn-ghost btn-sm" style={{ marginBottom: 16 }}>
            {showArchived ? 'Ẩn tài khoản lưu trữ' : `Hiển thị ${archivedAccounts.length} tài khoản đã lưu trữ`}
          </button>
          
          {showArchived && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12, opacity: 0.6 }}>
              {archivedAccounts.map(acc => (
                <div key={acc.id} className="card" style={{ padding: '20px', borderLeft: `3px solid var(--surface-border)` }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, filter: 'grayscale(1)' }}>
                      <BankLogo iconStr={acc.icon} color="var(--text-secondary)" size={40} />
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 600 }}>{acc.name}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Đã lưu trữ</div>
                      </div>
                    </div>
                    <button onClick={() => setArchiveConfirm(acc)} className="btn btn-ghost btn-sm" style={{ padding: '2px 8px' }}>
                      <RefreshCw size={13} style={{ marginRight: 4 }} /> Khôi phục
                    </button>
                  </div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-tertiary)' }}>
                    {formatVND(acc.balance)}
                  </div>
                </div>
              ))}
            </div>
          )}
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
                <h2 style={{ fontSize: 17, fontWeight: 600 }}>{editAccount ? 'Sửa tài khoản' : 'Thêm tài khoản'}</h2>
                <button onClick={() => setShowForm(false)} className="btn btn-ghost" style={{ width: 32, height: 32, padding: 0, borderRadius: '50%' }}>✕</button>
              </div>

              <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16, overflowY: 'auto', flex: 1 }}>
                {/* Icon */}
                <div>
                  <label className="label">Icon / Logo</label>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {ICON_OPTIONS.map((icon, i) => (
                      <button key={i} onClick={() => setFormIcon(icon)} style={{
                        width: 44, height: 44, borderRadius: 10, border: `2px solid ${formIcon === icon ? formColor : 'var(--surface-border)'}`,
                        background: 'transparent', cursor: 'pointer',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0
                      }}>
                        <BankLogo iconStr={icon} color={formIcon === icon ? formColor : 'var(--text-primary)'} size={40} />
                      </button>
                    ))}
                  </div>
                </div>

                {/* Color */}
                <div>
                  <label className="label">Màu sắc</label>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {COLOR_OPTIONS.map(color => (
                      <button key={color} onClick={() => setFormColor(color)} style={{
                        width: 32, height: 32, borderRadius: '50%', background: color, border: `3px solid ${formColor === color ? 'var(--text-primary)' : 'transparent'}`, cursor: 'pointer',
                      }} />
                    ))}
                  </div>
                </div>

                <div>
                  <label className="label" htmlFor="account-name">Tên tài khoản</label>
                  <input id="account-name" type="text" value={formName} onChange={e => setFormName(e.target.value)} placeholder="VD: Tiền mặt, Thẻ tín dụng..." className="input" />
                </div>
                
                <div>
                  <label className="label" htmlFor="account-desc">Số tài khoản / Note (Tùy chọn)</label>
                  <input id="account-desc" type="text" value={formDesc} onChange={e => setFormDesc(e.target.value)} placeholder="VD: 1903001... hoặc TCB Visa" className="input" />
                </div>

                <div style={{ zIndex: 10 }}>
                  <label className="label">Loại tài khoản</label>
                  <Select
                    value={formType}
                    onChange={setFormType}
                    options={ACCOUNT_GROUPS.map(g => ({ value: g.key, label: g.label }))}
                  />
                </div>

                <div>
                  <label className="label" htmlFor="account-balance">Số dư ban đầu (đ)</label>
                  <input id="account-balance" type="text" value={formBalance} onChange={e => setFormBalance(formatAmountLive(e.target.value))} className="input" />
                </div>
              </div>

              <div className="drawer-footer">
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setShowForm(false)}>Hủy</button>
                <button className="btn btn-primary" style={{ flex: 2 }} onClick={handleSave} disabled={saving || !formName.trim()}>
                  {saving ? 'Đang lưu...' : editAccount ? 'Cập nhật' : 'Tạo tài khoản'}
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
      </Portal>

      {/* Archive Confirm */}
      <Portal>
      <AnimatePresence>
        {archiveConfirm && (
          <>
            <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setArchiveConfirm(null)} />
            <motion.div className="modal" style={{ padding: '28px', textAlign: 'center' }} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}>
              <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'var(--surface-border)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                <Archive size={24} style={{ color: 'var(--text-secondary)' }} />
              </div>
              <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 8 }}>
                {archiveConfirm.isActive ? 'Lưu trữ tài khoản?' : 'Khôi phục tài khoản?'}
              </h3>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24, lineHeight: 1.5 }}>
                {archiveConfirm.isActive 
                  ? 'Tài khoản này sẽ bị ẩn đi và không thể tạo thêm giao dịch mới, nhưng toàn bộ lịch sử thu/chi vẫn được giữ nguyên.'
                  : 'Tài khoản sẽ hoạt động trở lại bình thường và cho phép thêm giao dịch mới.'}
              </p>
              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setArchiveConfirm(null)}>Hủy</button>
                <button onClick={() => handleArchiveToggle(archiveConfirm)} className="btn btn-primary" style={{ flex: 1 }}>
                  {archiveConfirm.isActive ? 'Lưu trữ' : 'Khôi phục'}
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
              <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'var(--accent-red-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                <Trash2 size={24} style={{ color: 'var(--accent-red)' }} />
              </div>
              <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 8 }}>
                Xóa tài khoản?
              </h3>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8, lineHeight: 1.5 }}>
                Bạn có chắc muốn xóa <strong>{deleteConfirm.name}</strong>?
              </p>
              <p style={{ fontSize: 12, color: 'var(--accent-red)', marginBottom: 24, lineHeight: 1.5 }}>
                Toàn bộ giao dịch liên quan sẽ bị xóa vĩnh viễn và không thể hoàn tác.
              </p>
              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setDeleteConfirm(null)}>Hủy</button>
                <button onClick={handleDelete} className="btn" style={{ flex: 1, background: 'var(--accent-red)', color: 'white', border: 'none' }}>
                  Xóa vĩnh viễn
                </button>
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
