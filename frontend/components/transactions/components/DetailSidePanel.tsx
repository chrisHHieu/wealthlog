import { motion, AnimatePresence } from 'framer-motion'
import { Edit2, Trash2, X } from 'lucide-react'
import { formatVND, formatDateVI } from '@/lib/utils'
import { Transaction } from '@/types'

interface DetailSidePanelProps {
  transaction: Transaction | null
  onClose: () => void
  onEdit: (id: string) => void
  onDelete: (id: string) => void
}

export function DetailSidePanel({ transaction, onClose, onEdit, onDelete }: DetailSidePanelProps) {
  return (
    <AnimatePresence>
      {transaction && (
        <motion.div
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 40 }}
          className="transaction-detail-panel"
        >
          <div className="card" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <span style={{ fontWeight: 600, fontSize: 15 }}>Details</span>
              <button onClick={onClose} className="btn btn-ghost btn-sm" style={{ padding: '4px 8px' }} aria-label="Close">
                <X size={14} />
              </button>
            </div>

            <div style={{ textAlign: 'center', marginBottom: 20 }}>
              <div style={{ fontSize: 40, marginBottom: 8 }}>{transaction.categoryIcon ?? '📦'}</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: transaction.type === 'income' ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                {transaction.type === 'income' ? '+' : '-'}{formatVND(transaction.amount)}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>{transaction.description}</div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[
                { label: 'Type', value: transaction.type === 'income' ? 'Income' : transaction.type === 'expense' ? 'Expense' : 'Transfer' },
                { label: 'Date', value: formatDateVI(transaction.date) },
                { label: 'Category', value: transaction.categoryName ?? 'Uncategorized' },
                { label: 'Accounts', value: `${transaction.accountIcon ?? ''} ${transaction.accountName ?? 'N/A'}` },
                ...(transaction.note ? [{ label: 'Note', value: transaction.note }] : []),
              ].map(row => (
                <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                  <span style={{ color: 'var(--text-tertiary)' }}>{row.label}</span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 500, textAlign: 'right', maxWidth: '65%' }}>{row.value}</span>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 8, marginTop: 20 }}>
              <button
                className="btn btn-secondary" style={{ flex: 1 }}
                onClick={() => { onEdit(transaction.id); onClose() }}
              >
                <Edit2 size={14} /> Edit
              </button>
              <button
                className="btn btn-danger" style={{ flex: 1 }}
                onClick={() => onDelete(transaction.id)}
              >
                <Trash2 size={14} /> Delete
              </button>
            </div>
          </div>
          <style jsx>{`
            .transaction-detail-panel {
              width: 300px;
              flex-shrink: 0;
              position: sticky;
              top: 88px;
              align-self: flex-start;
            }

            @media (max-width: 1180px) {
              .transaction-detail-panel {
                width: 100%;
                position: static;
              }
            }
          `}</style>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
