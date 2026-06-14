'use client'

import { useState } from 'react'
import { PageTransition } from '@/components/ui/PageTransition'
import { PageHeader } from '@/components/ui/PageHeader'
import { Portal } from '@/components/ui/Portal'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Edit2, Trash2, Archive, RefreshCw, Wallet, X } from 'lucide-react'
import { useToast } from '@/components/ui/toaster'
import { formatVND, formatVNDCompact, parseShorthandAmount, formatAmountLive } from '@/lib/utils'
import { apiDelete, apiGet, apiJson, queryKeys } from '@/lib/api'
import { AnimatedCounter } from '@/components/ui/AnimatedCounter'
import { Select } from '@/components/ui/Select'
import { Stat } from '@/components/ui/Stat'
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
  cash: 'Cash',
  bank: 'Bank',
  ewallet: 'E-wallet',
  investment: 'Investment',
  savings: 'Savings',
  debt: 'Debt/Loan',
}

const ACCOUNT_GROUPS = [
  { key: 'cash', label: 'Cash' },
  { key: 'bank', label: 'Bank' },
  { key: 'ewallet', label: 'E-wallet' },
  { key: 'investment', label: 'Investment' },
  { key: 'savings', label: 'Savings' },
  { key: 'debt', label: 'Debt/Loan' },
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
    queryKey: queryKeys.accounts,
    queryFn: () => apiGet<Account[]>('/api/accounts'),
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
        await apiJson(`/api/accounts/${editAccount.id}`, {
          method: 'PUT',
          body,
        })
        toast('Account updated')
      } else {
        await apiJson('/api/accounts', {
          method: 'POST',
          body,
        })
        toast('Account created')
      }

      await qc.invalidateQueries({ queryKey: queryKeys.accounts })
      await qc.invalidateQueries({ queryKey: ['dashboard'] })
      setShowForm(false)
    } finally {
      setSaving(false)
    }
  }

  async function handleArchiveToggle(acc: Account) {
    const isNowActive = !acc.isActive
    await apiJson(`/api/accounts/${acc.id}`, {
      method: 'PUT',
      body: { ...acc, isActive: isNowActive }
    })
    await qc.invalidateQueries({ queryKey: queryKeys.accounts })
    await qc.invalidateQueries({ queryKey: ['dashboard'] })
    setArchiveConfirm(null)
    toast(isNowActive ? 'Account restored' : 'Account archived')
  }

  async function handleDelete() {
    if (!deleteConfirm) return
    await apiDelete(`/api/accounts/${deleteConfirm.id}`)
    await qc.invalidateQueries({ queryKey: queryKeys.accounts })
    await qc.invalidateQueries({ queryKey: ['dashboard'] })
    toast('Account deleted')
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
      <PageHeader
        eyebrow="Balances"
        title="Accounts"
        subtitle={`${activeAccounts.length} active ${activeAccounts.length === 1 ? 'account' : 'accounts'}`}
        actions={
          <>
            <button onClick={navigateTransfer} className="btn btn-secondary">
              <RefreshCw size={15} /> Transfer money
            </button>
            <button id="add-account-btn" onClick={openAdd} className="btn btn-primary">
              <Plus size={15} /> Add account
            </button>
          </>
        }
      />

      {/* Summary */}
      <div className="card" style={{ padding: 20, marginBottom: 24 }}>
        <div className="stat-strip">
          <Stat
            label="Total assets"
            value={<AnimatedCounter value={totalAssets} format={v => formatVNDCompact(Math.round(v))} />}
            color="var(--accent-green)"
            size="lg"
          />
          <Stat
            label="Total debt"
            value={<AnimatedCounter value={totalDebt} format={v => formatVNDCompact(Math.round(v))} />}
            color="var(--accent-red)"
            size="lg"
          />
          <Stat
            label="Net worth"
            value={<AnimatedCounter value={netWorth} format={v => formatVNDCompact(Math.round(v))} />}
            size="lg"
          />
        </div>
      </div>

      {/* Account groups */}
      {isLoading ? (
        <div className="accounts-card-grid">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 120, borderRadius: 16 }} />
          ))}
        </div>
      ) : activeAccounts.length === 0 ? (
        <div className="empty-state card" style={{ padding: '48px 24px' }}>
          <div className="icon-tile" style={{ width: 56, height: 56 }}>
            <Wallet size={26} />
          </div>
          <p style={{ fontSize: 15, fontWeight: 600 }}>No accounts yet</p>
          <button className="btn btn-primary" onClick={openAdd} style={{ marginTop: 8 }}>
            <Plus size={15} /> Add your first account
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {ACCOUNT_GROUPS.map(group => {
            const groupAccounts = activeAccounts.filter(a => a.type === group.key)
            if (groupAccounts.length === 0) return null
            return (
              <div key={group.key}>
                <div className="stat-label" style={{ marginBottom: 10 }}>
                  {group.label}
                </div>
                <div className="accounts-card-grid compact">
                  {groupAccounts.map(acc => (
                    <motion.div
                      key={acc.id}
                      onClick={() => handleCardClick(acc.id)}
                      className="card card-interactive"
                      style={{ padding: '20px', cursor: 'pointer', borderLeft: `3px solid ${acc.color}` }}
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
                        <div className="num-meta" style={{ fontSize: 20, fontWeight: 700, color: acc.balance >= 0 ? 'var(--text-primary)' : 'var(--accent-red)' }}>
                          {formatVND(acc.balance)}
                        </div>
                        <div style={{ display: 'flex', gap: 2, flexShrink: 0 }}>
                          <button onClick={(e) => openEdit(e, acc)} className="btn btn-ghost btn-sm" style={{ width: 32, height: 32, padding: 0, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }} title="Edit"><Edit2 size={14} /></button>
                          <button onClick={(e) => { e.stopPropagation(); setArchiveConfirm(acc) }} className="btn btn-ghost btn-sm" style={{ width: 32, height: 32, padding: 0, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)' }} title="Archive"><Archive size={14} /></button>
                          <button onClick={(e) => { e.stopPropagation(); setDeleteConfirm(acc) }} className="btn btn-ghost btn-sm" style={{ width: 32, height: 32, padding: 0, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-red)' }} title="Delete"><Trash2 size={14} /></button>
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
            {showArchived ? 'Hide archived accounts' : `Show ${archivedAccounts.length} archived accounts`}
          </button>
          
          {showArchived && (
            <div className="accounts-card-grid compact" style={{ opacity: 0.6 }}>
              {archivedAccounts.map(acc => (
                <div key={acc.id} className="card" style={{ padding: '20px', borderLeft: `3px solid var(--surface-border)` }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, filter: 'grayscale(1)' }}>
                      <BankLogo iconStr={acc.icon} color="var(--text-secondary)" size={40} />
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 600 }}>{acc.name}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Archived</div>
                      </div>
                    </div>
                    <button onClick={() => setArchiveConfirm(acc)} className="btn btn-ghost btn-sm" style={{ padding: '2px 8px' }}>
                      <RefreshCw size={13} style={{ marginRight: 4 }} /> Restore
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
                <h2 style={{ fontSize: 17, fontWeight: 600 }}>{editAccount ? 'Edit account' : 'Add account'}</h2>
                <button onClick={() => setShowForm(false)} className="btn btn-ghost" style={{ width: 32, height: 32, padding: 0, borderRadius: '50%' }} aria-label="Close">
                  <X size={16} />
                </button>
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
                  <label className="label">Color</label>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {COLOR_OPTIONS.map(color => (
                      <button key={color} onClick={() => setFormColor(color)} style={{
                        width: 32, height: 32, borderRadius: '50%', background: color, border: `3px solid ${formColor === color ? 'var(--text-primary)' : 'transparent'}`, cursor: 'pointer',
                      }} />
                    ))}
                  </div>
                </div>

                <div>
                  <label className="label" htmlFor="account-name">Account name</label>
                  <input id="account-name" type="text" value={formName} onChange={e => setFormName(e.target.value)} placeholder="Example: Cash, Credit card..." className="input" />
                </div>
                
                <div>
                  <label className="label" htmlFor="account-desc">Account number / Note (optional)</label>
                  <input id="account-desc" type="text" value={formDesc} onChange={e => setFormDesc(e.target.value)} placeholder="Example: 1903001... or TCB Visa" className="input" />
                </div>

                <div style={{ zIndex: 10 }}>
                  <label className="label">Account type</label>
                  <Select
                    value={formType}
                    onChange={setFormType}
                    options={ACCOUNT_GROUPS.map(g => ({ value: g.key, label: g.label }))}
                  />
                </div>

                <div>
                  <label className="label" htmlFor="account-balance">Initial balance (VND)</label>
                  <input id="account-balance" type="text" value={formBalance} onChange={e => setFormBalance(formatAmountLive(e.target.value))} className="input" />
                </div>
              </div>

              <div className="drawer-footer">
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setShowForm(false)}>Cancel</button>
                <button className="btn btn-primary" style={{ flex: 2 }} onClick={handleSave} disabled={saving || !formName.trim()}>
                  {saving ? 'Saving...' : editAccount ? 'Update' : 'Create account'}
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
                {archiveConfirm.isActive ? 'Archive account?' : 'Restore account?'}
              </h3>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24, lineHeight: 1.5 }}>
                {archiveConfirm.isActive 
                  ? 'This account will be hidden and cannot be used for new transactions, but all income and expense history will be preserved.'
                  : 'This account will become active again and can be used for new transactions.'}
              </p>
              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setArchiveConfirm(null)}>Cancel</button>
                <button onClick={() => handleArchiveToggle(archiveConfirm)} className="btn btn-primary" style={{ flex: 1 }}>
                  {archiveConfirm.isActive ? 'Archive' : 'Restore'}
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
                Delete account?
              </h3>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8, lineHeight: 1.5 }}>
                Are you sure you want to delete <strong>{deleteConfirm.name}</strong>?
              </p>
              <p style={{ fontSize: 12, color: 'var(--accent-red)', marginBottom: 24, lineHeight: 1.5 }}>
                All related transactions will be permanently deleted and cannot be undone.
              </p>
              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setDeleteConfirm(null)}>Cancel</button>
                <button onClick={handleDelete} className="btn" style={{ flex: 1, background: 'var(--accent-red)', color: 'white', border: 'none' }}>
                  Delete permanently
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
      </Portal>
      <style jsx>{`
        .accounts-card-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(min(280px, 100%), 1fr));
          gap: 16px;
        }

        .accounts-card-grid.compact {
          gap: 12px;
        }
      `}</style>
    </div>
    </PageTransition>
  )
}
