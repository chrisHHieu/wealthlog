'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { X, ArrowDownCircle, ArrowUpCircle, ArrowLeftRight } from 'lucide-react'
import { formatAmountLive } from '@/lib/utils'
import { Select } from '@/components/ui/Select'
import { DatePicker } from '@/components/ui/DatePicker'
import { AmountInput } from '@/components/ui/AmountInput'
import { BankLogo } from '@/components/ui/BankLogo'
import { TAB_COLORS, TxType } from './types'
import { useTransactionDrawerForm } from './useTransactionDrawerForm'

export function TransactionDrawer() {
  const {
    accounts,
    addTransactionOpen,
    amountRaw,
    categoryId,
    closeAddTransaction,
    date,
    description,
    editTransactionId,
    filteredCategories,
    handleSubmit,
    isValid,
    accountId,
    saveAndAdd,
    saving,
    setAccountId,
    setAmountRaw,
    setCategoryId,
    setDate,
    setDescription,
    setToAccountId,
    setTxType,
    toAccountId,
    txType,
  } = useTransactionDrawerForm()

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
                {editTransactionId ? 'Edit transaction' : 'Add transaction'}
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

            {/* Form */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
              {/* Amount */}
              <div style={{ textAlign: 'center', marginBottom: 28 }}>
                <div className="stat-label" style={{ marginBottom: 8 }}>
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
                  <label className="label" htmlFor="tx-description">Description</label>
                  <input
                    id="tx-description"
                    type="text"
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    placeholder="Example: Lunch with colleagues"
                    className="input"
                  />
                </div>

                {/* Account */}
                <div>
                  <label className="label" htmlFor="tx-account">Accounts</label>
                  <Select
                    value={accountId}
                    onChange={setAccountId}
                    options={accounts.map(a => ({ value: a.id, label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><BankLogo iconStr={a.icon} color="var(--text-primary)" size={20} /> {a.name}</span> }))}
                  />
                </div>

                {/* To Account (for transfer) */}
                {txType === 'transfer' && (
                  <div>
                    <label className="label" htmlFor="tx-to-account">Destination account</label>
                    <Select
                      value={toAccountId}
                      onChange={setToAccountId}
                      placeholder="Select account..."
                      options={[
                        { value: '', label: 'Select account...' },
                        ...accounts.filter(a => a.id !== accountId).map(a => ({ value: a.id, label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><BankLogo iconStr={a.icon} color="var(--text-primary)" size={20} /> {a.name}</span> }))
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
                  <label className="label" htmlFor="tx-date">Date</label>
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
                Save & add another
              </button>
              <button
                id="tx-save-btn"
                className="btn btn-primary"
                onClick={() => handleSubmit(false)}
                disabled={!isValid || saving}
                style={{ flex: 1 }}
              >
                {saving && !saveAndAdd ? 'Saving...' : 'Save transactions'}
              </button>
            </div>
            <style jsx>{`
              .drawer-option-grid {
                display: grid;
                gap: 8px;
              }

              .drawer-option-grid.four {
                grid-template-columns: repeat(4, minmax(0, 1fr));
              }

              @media (max-width: 480px) {
                .drawer-option-grid.four {
                  grid-template-columns: repeat(2, minmax(0, 1fr));
                }

                :global(.drawer-footer) {
                  flex-direction: column-reverse;
                }

                :global(.drawer-footer .btn) {
                  width: 100%;
                }
              }
            `}</style>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
