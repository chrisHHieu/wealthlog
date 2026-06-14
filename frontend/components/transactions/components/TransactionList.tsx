import { motion } from 'framer-motion'
import { Edit2, Trash2, Plus, ReceiptText } from 'lucide-react'
import { formatVND, formatDateVI } from '@/lib/utils'
import { Transaction } from '@/types'

interface TransactionListProps {
  transactions: Transaction[]
  isLoading: boolean
  onAdd: () => void
  onSelect: (tx: Transaction) => void
  onEdit: (id: string) => void
  onDelete: (id: string) => void
}

function groupByDate(transactions: Transaction[]) {
  const groups: Record<string, Transaction[]> = {}
  transactions.forEach(tx => {
    if (!groups[tx.date]) groups[tx.date] = []
    groups[tx.date].push(tx)
  })
  return Object.entries(groups).sort(([a], [b]) => b.localeCompare(a))
}

const TYPE_COLORS: Record<string, string> = {
  income: 'var(--accent-green)',
  expense: 'var(--accent-red)',
  transfer: 'var(--accent-blue)',
}

export function TransactionList({ transactions, isLoading, onAdd, onSelect, onEdit, onDelete }: TransactionListProps) {
  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        {[...Array(5)].map((_, i) => (
          <div key={i} className="skeleton" style={{ height: 64, borderRadius: 'var(--radius-md)' }} />
        ))}
      </div>
    )
  }

  if (transactions.length === 0) {
    return (
      <div className="empty-state card" style={{ padding: 'var(--space-12) var(--space-6)' }}>
        <div className="icon-tile" style={{ width: 56, height: 56 }}>
          <ReceiptText size={26} />
        </div>
        <p style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--text-primary)' }}>No transactions yet</p>
        <p style={{ fontSize: 'var(--text-sm)' }}>Add your first transaction</p>
        <button className="btn btn-primary" onClick={onAdd} style={{ marginTop: 'var(--space-2)' }}>
          <Plus size={15} /> Add transaction
        </button>
      </div>
    )
  }

  const grouped = groupByDate(transactions)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
      {grouped.map(([date, txs]) => {
        const dayIncome = txs.filter(t => t.type === 'income').reduce((s, t) => s + t.amount, 0)
        const dayExpense = txs.filter(t => t.type === 'expense').reduce((s, t) => s + t.amount, 0)

        return (
          <div key={date}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 'var(--space-2)',
              padding: '0 var(--space-1)',
            }}>
              <span className="mono-meta" style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>
                {formatDateVI(date)}
              </span>
              <div className="num-meta" style={{ display: 'flex', gap: 'var(--space-2-5)', fontSize: 'var(--text-sm)' }}>
                {dayIncome > 0 && <span style={{ color: 'var(--accent-green)', fontWeight: 600 }}>+{formatVND(dayIncome)}</span>}
                {dayExpense > 0 && <span style={{ color: 'var(--accent-red)', fontWeight: 600 }}>-{formatVND(dayExpense)}</span>}
              </div>
            </div>

            <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
              {txs.map((tx, i) => (
                <motion.div
                  key={tx.id}
                  className="row-hover"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03, duration: 0.25 }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-3)',
                    padding: 'var(--space-3) var(--space-4)',
                    borderBottom: i < txs.length - 1 ? '1px solid var(--surface-border)' : 'none',
                    cursor: 'pointer',
                    position: 'relative',
                    borderLeft: `3px solid ${TYPE_COLORS[tx.type] ?? 'transparent'}`,
                  }}
                  onClick={() => onSelect(tx)}
                >
                  <div className="category-icon" style={{
                    background: `${tx.categoryColor ?? '#6366f1'}15`,
                    fontSize: 18,
                  }}>
                    {tx.categoryIcon ?? '📦'}
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 'var(--text-base)',
                      fontWeight: 600,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {tx.description}
                    </div>
                    <div style={{
                      fontSize: 'var(--text-xs)',
                      color: 'var(--text-tertiary)',
                      marginTop: 2,
                    }}>
                      {tx.categoryName ?? 'Uncategorized'}
                      {tx.accountName && ` · ${tx.accountIcon ?? ''} ${tx.accountName}`}
                    </div>
                  </div>

                  <div className="num-meta" style={{
                    fontSize: 'var(--text-base)',
                    fontWeight: 700,
                    marginRight: 'var(--space-2)',
                    flexShrink: 0,
                    color: TYPE_COLORS[tx.type] ?? 'var(--text-secondary)',
                  }}>
                    {tx.type === 'income' ? '+' : tx.type === 'expense' ? '-' : ''}
                    {formatVND(tx.amount)}
                  </div>

                  <div style={{ display: 'flex', gap: 'var(--space-1)' }} onClick={e => e.stopPropagation()}>
                    <button
                      onClick={() => onEdit(tx.id)}
                      className="btn-icon"
                      style={{ width: 28, height: 28, borderRadius: 'var(--radius-full)', border: 'none', background: 'transparent' }}
                      title="Edit"
                    >
                      <Edit2 size={13} />
                    </button>
                    <button
                      onClick={() => onDelete(tx.id)}
                      className="btn-icon"
                      style={{ width: 28, height: 28, borderRadius: 'var(--radius-full)', border: 'none', background: 'transparent', color: 'var(--accent-red)' }}
                      title="Delete"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
