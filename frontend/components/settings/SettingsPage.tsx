'use client'

import { useState, useEffect } from 'react'
import { PageTransition } from '@/components/ui/PageTransition'
import { Portal } from '@/components/ui/Portal'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Save, Trash2, Plus, Edit2, Moon, Sun, Globe } from 'lucide-react'
import { useToast } from '@/components/ui/toaster'
import { useAppStore } from '@/store/useAppStore'
import { formatVND } from '@/lib/utils'
import { API_URL } from '@/lib/api'
import { Select } from '@/components/ui/Select'

interface Category {
  id: string
  name: string
  icon: string
  color: string
  type: string
  budgetGroup?: string | null
  isDefault: boolean
}

const CAT_COLORS = ['#00C896', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#d946ef', '#06b6d4', '#84cc16', '#f97316', '#ec4899']
const CAT_ICONS = [
  '📦', '🍜', '🍔', '☕', '🍺', // Ăn uống
  '🚗', '🚌', '🚕', '🏍️', '🚄', '⛽', // Di chuyển
  '🛍️', '👗', '👟', '📱', '🎮', '💻', // Mua sắm
  '🎬', '🎵', '📸', '🎨', '🏖️', // Giải trí
  '🏥', '💊', '🏃', '🏋️‍♀️', '🧘‍♀️', // Sức khỏe
  '📚', '🎓', '✏️', '💡', '🧠', // Giáo dục
  '🏠', '🛋️', '🧹', '🔧', '🪴', // Nhà cửa
  '⚡', '💧', '🗑️', '🌐', '📞', // Hóa đơn & Tiện ích
  '💄', '💈', '💅', '💆‍♀️', '🎀', // Làm đẹp
  '✈️', '🚂', '🛳️', '🗺️', '🏕️', // Du lịch
  '👨‍👩‍👧', '👶', '🐶', '🐱', '💝', // Gia đình & Thú cưng
  '💰', '🎁', '📈', '💵', '🏦', '💳', '🧾', // Tài chính
  '💼', '🛠️', '🤖', '⚙️', '🔒', '🛡️', // Công việc & Công nghệ
  '🤝', '🎉', '🔥', '✨', '⭐' // Khác
]

export function SettingsPage() {
  const { toast } = useToast()
  const qc = useQueryClient()
  const { theme, toggleTheme } = useAppStore()

  const [userName, setUserName] = useState('')
  const [saving, setSaving] = useState(false)
  const [showCatForm, setShowCatForm] = useState(false)
  const [catName, setCatName] = useState('')
  const [catType, setCatType] = useState<'income' | 'expense' | 'both'>('expense')
  const [catBudgetGroup, setCatBudgetGroup] = useState('')
  const [catIcon, setCatIcon] = useState('📦')
  const [catColor, setCatColor] = useState('#6366f1')
  const [editCat, setEditCat] = useState<Category | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const { data: settings } = useQuery<Record<string, string>>({
    queryKey: ['settings'],
    queryFn: () => fetch(`${API_URL}/api/settings`).then(r => r.json()).then(r => r.data ?? r),
  })

  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: () => fetch(`${API_URL}/api/categories`).then(r => r.json()),
  })

  useEffect(() => {
    if (settings?.userName) setUserName(settings.userName)
  }, [settings])

  async function saveProfile() {
    setSaving(true)
    try {
      await fetch(`${API_URL}/api/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: { userName } }),
      })
      await qc.invalidateQueries({ queryKey: ['settings'] })
      toast('Đã lưu thông tin cá nhân')
    } finally {
      setSaving(false)
    }
  }

  async function saveCat() {
    if (!catName.trim()) return

    if (editCat) {
      await fetch(`${API_URL}/api/categories`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: editCat.id, name: catName, type: catType, budgetGroup: catBudgetGroup || null, icon: catIcon, color: catColor }),
      })
      toast('Đã cập nhật danh mục')
    } else {
      await fetch(`${API_URL}/api/categories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: catName, type: catType, budgetGroup: catBudgetGroup || null, icon: catIcon, color: catColor }),
      })
      toast('Đã thêm danh mục')
    }

    await qc.invalidateQueries({ queryKey: ['categories'] })
    setShowCatForm(false)
    setCatName(''); setCatBudgetGroup(''); setCatIcon('📦'); setCatColor('#6366f1'); setEditCat(null)
  }

  async function deleteCat(id: string) {
    await fetch(`${API_URL}/api/categories?id=${id}`, { method: 'DELETE' })
    await qc.invalidateQueries({ queryKey: ['categories'] })
    setDeleteConfirm(null)
    toast('Đã xóa danh mục')
  }

  function openEditCat(cat: Category) {
    setEditCat(cat)
    setCatName(cat.name)
    setCatType(cat.type as 'income' | 'expense' | 'both')
    setCatBudgetGroup(cat.budgetGroup ?? '')
    setCatIcon(cat.icon)
    setCatColor(cat.color)
    setShowCatForm(true)
  }

  const incomeCategories = categories.filter(c => c.type === 'income' || c.type === 'both')
  const expenseCategories = categories.filter(c => c.type === 'expense' || c.type === 'both')

  return (
    <PageTransition>
    <div style={{ maxWidth: 720 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Cài đặt</h1>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Tùy chỉnh ứng dụng theo sở thích của bạn</p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Profile */}
        <div className="card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>👤 Thông tin cá nhân</h3>

          <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 20 }}>
            <div style={{
              width: 72, height: 72, borderRadius: '50%',
              background: 'linear-gradient(135deg, var(--accent-green), var(--accent-blue))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 28, fontWeight: 700, color: '#fff', flexShrink: 0,
            }}>
              {userName.charAt(0)?.toUpperCase() ?? '?'}
            </div>
            <div style={{ flex: 1 }}>
              <label className="label" htmlFor="settings-name">Tên hiển thị</label>
              <input
                id="settings-name"
                type="text"
                value={userName}
                onChange={e => setUserName(e.target.value)}
                placeholder="Nhập tên của bạn"
                className="input"
              />
            </div>
          </div>

          <button className="btn btn-primary btn-sm" onClick={saveProfile} disabled={saving} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Save size={14} />
            {saving ? 'Đang lưu...' : 'Lưu thay đổi'}
          </button>
        </div>

        {/* Appearance */}
        <div className="card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>🎨 Giao diện</h3>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--surface)', borderRadius: 10, border: '1px solid var(--surface-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {theme === 'dark' ? <Moon size={18} style={{ color: 'var(--accent-blue)' }} /> : <Sun size={18} style={{ color: 'var(--accent-yellow)' }} />}
              <div>
                <div style={{ fontSize: 14, fontWeight: 500 }}>{theme === 'dark' ? 'Chế độ tối' : 'Chế độ sáng'}</div>
                <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                  {theme === 'dark' ? 'Phù hợp với môi trường tối' : 'Phù hợp với ánh sáng ban ngày'}
                </div>
              </div>
            </div>
            <button
              id="theme-toggle"
              onClick={toggleTheme}
              style={{
                width: 48, height: 26, borderRadius: 13, border: 'none', cursor: 'pointer',
                background: theme === 'dark' ? 'var(--accent-blue)' : 'var(--accent-yellow)',
                position: 'relative', transition: 'background 0.2s',
              }}
            >
              <motion.div
                style={{
                  position: 'absolute', top: 3, width: 20, height: 20, borderRadius: '50%',
                  background: '#fff', boxShadow: '0 1px 4px rgba(0,0,0,0.3)',
                }}
                animate={{ left: theme === 'dark' ? '100%' : '3px', x: theme === 'dark' ? 'calc(-100% - 3px)' : 0 }}
                transition={{ type: 'spring', stiffness: 500, damping: 30 }}
              />
            </button>
          </div>
        </div>

        {/* Categories */}
        <div className="card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <h3 style={{ fontSize: 15, fontWeight: 600 }}>📂 Quản lý danh mục</h3>
            <button
              id="add-category-btn"
              onClick={() => { setEditCat(null); setCatName(''); setCatBudgetGroup(''); setCatIcon('📦'); setCatColor('#6366f1'); setCatType('expense'); setShowCatForm(true) }}
              className="btn btn-primary btn-sm"
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <Plus size={13} /> Thêm danh mục
            </button>
          </div>

          {showCatForm && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--surface-border)', borderRadius: 12, padding: 16, marginBottom: 16 }}
            >
              <div style={{ marginBottom: 12, fontSize: 14, fontWeight: 600 }}>{editCat ? 'Sửa danh mục' : 'Danh mục mới'}</div>

              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12, maxHeight: 160, overflowY: 'auto', paddingRight: 4 }}>
                {CAT_ICONS.map(i => (
                  <button key={i} onClick={() => setCatIcon(i)} style={{
                    fontSize: 20, width: 40, height: 40, borderRadius: 8,
                    border: `2px solid ${catIcon === i ? catColor : 'var(--surface-border)'}`,
                    background: catIcon === i ? `${catColor}20` : 'var(--surface)', cursor: 'pointer',
                  }}>{i}</button>
                ))}
              </div>

              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
                {CAT_COLORS.map(c => (
                  <button key={c} onClick={() => setCatColor(c)} style={{
                    width: 28, height: 28, borderRadius: '50%', background: c,
                    border: `3px solid ${catColor === c ? 'var(--text-primary)' : 'transparent'}`, cursor: 'pointer',
                  }} />
                ))}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 10, alignItems: 'end' }}>
                <div>
                  <label className="label">Tên danh mục</label>
                  <input type="text" value={catName} onChange={e => setCatName(e.target.value)} placeholder="VD: Cà phê" className="input" />
                </div>
                <div>
                  <label className="label">Loại</label>
                  <Select
                    value={catType}
                    onChange={(v) => setCatType(v as 'income' | 'expense' | 'both')}
                    options={[
                      { value: 'income', label: 'Thu' },
                      { value: 'expense', label: 'Chi' },
                      { value: 'both', label: 'Cả hai' }
                    ]}
                  />
                </div>
              </div>

              {/* Budget group selector (50/30/20 rule) */}
              {(catType === 'expense' || catType === 'both') && (
                <div style={{ marginTop: 12 }}>
                  <label className="label" style={{ marginBottom: 6, display: 'block' }}>Nhóm quy tắc 50/30/20</label>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {[
                      { value: '', label: 'Chưa phân loại', color: '#6b7280' },
                      { value: 'needs', label: '🏠 Thiết yếu (50%)', color: '#3b82f6' },
                      { value: 'wants', label: '🎬 Mong muốn (30%)', color: '#10b981' },
                    ].map(opt => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setCatBudgetGroup(opt.value)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: 8,
                          border: `2px solid ${catBudgetGroup === opt.value ? opt.color : 'var(--surface-border)'}`,
                          background: catBudgetGroup === opt.value ? `${opt.color}20` : 'var(--surface)',
                          color: catBudgetGroup === opt.value ? opt.color : 'var(--text-secondary)',
                          fontSize: 12,
                          fontWeight: 600,
                          cursor: 'pointer',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end', marginTop: 12 }}>
                <button className="btn btn-secondary btn-sm" onClick={() => setShowCatForm(false)}>Hủy</button>
                <button className="btn btn-primary btn-sm" onClick={saveCat} disabled={!catName.trim()}>Lưu</button>
              </div>
            </motion.div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            {/* Income categories */}
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-tertiary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
                Thu nhập ({incomeCategories.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {incomeCategories.map(cat => (
                  <div key={cat.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', borderRadius: 8, background: 'var(--surface)', border: '1px solid var(--surface-border)' }}>
                    <span style={{ fontSize: 16 }}>{cat.icon}</span>
                    <span style={{ flex: 1, fontSize: 13, fontWeight: 500 }}>{cat.name}</span>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: cat.color }} />
                    {!cat.isDefault && (
                      <>
                        <button onClick={() => openEditCat(cat)} className="btn btn-ghost btn-sm" style={{ width: 24, height: 24, padding: 0, borderRadius: '50%' }}><Edit2 size={11} /></button>
                        <button onClick={() => setDeleteConfirm(cat.id)} className="btn btn-ghost btn-sm" style={{ width: 24, height: 24, padding: 0, borderRadius: '50%', color: 'var(--accent-red)' }}><Trash2 size={11} /></button>
                      </>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Expense categories */}
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-tertiary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
                Chi tiêu ({expenseCategories.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {expenseCategories.map(cat => (
                  <div key={cat.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', borderRadius: 8, background: 'var(--surface)', border: '1px solid var(--surface-border)' }}>
                    <span style={{ fontSize: 16 }}>{cat.icon}</span>
                    <span style={{ flex: 1, fontSize: 13, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                      {cat.name}
                      {cat.budgetGroup && (
                        <span style={{
                          fontSize: 9,
                          padding: '1px 5px',
                          borderRadius: 4,
                          background: cat.budgetGroup === 'needs' ? '#3b82f615' : '#10b98115',
                          color: cat.budgetGroup === 'needs' ? '#3b82f6' : '#10b981',
                          fontWeight: 600,
                          lineHeight: '14px',
                        }}>
                          {cat.budgetGroup === 'needs' ? 'Thiết yếu' : 'Mong muốn'}
                        </span>
                      )}
                    </span>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: cat.color, flexShrink: 0 }} />
                    {!cat.isDefault && (
                      <>
                        <button onClick={() => openEditCat(cat)} className="btn btn-ghost btn-sm" style={{ width: 24, height: 24, padding: 0, borderRadius: '50%' }}><Edit2 size={11} /></button>
                        <button onClick={() => setDeleteConfirm(cat.id)} className="btn btn-ghost btn-sm" style={{ width: 24, height: 24, padding: 0, borderRadius: '50%', color: 'var(--accent-red)' }}><Trash2 size={11} /></button>
                      </>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* App Info */}
        <div className="card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>ℹ️ Về ứng dụng</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13, color: 'var(--text-secondary)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Phiên bản</span><span style={{ color: 'var(--accent-green)', fontWeight: 600 }}>1.0.0</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Tech Stack</span><span style={{ color: 'var(--text-primary)' }}>Next.js 16 + Drizzle + SQLite</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Được tạo bởi</span><span style={{ color: 'var(--text-primary)' }}>WealthLog Team</span>
            </div>
          </div>
        </div>
      </div>

      {/* Delete Category Confirm */}
      <Portal>
        {deleteConfirm && (
          <>
            <div className="overlay" onClick={() => setDeleteConfirm(null)} />
            <div className="modal" style={{ padding: '28px', textAlign: 'center' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>⚠️</div>
              <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 8 }}>Xóa danh mục?</h3>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24 }}>Các giao dịch liên quan sẽ không bị xóa nhưng sẽ mất phân loại.</p>
              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setDeleteConfirm(null)}>Hủy</button>
                <button className="btn btn-danger" style={{ flex: 1 }} onClick={() => deleteCat(deleteConfirm)}>Xóa</button>
              </div>
            </div>
          </>
        )}
      </Portal>
    </div>
    </PageTransition>
  )
}
