import { ArrowRight, ReceiptText } from 'lucide-react'
import Link from 'next/link'
import { formatVND } from '@/lib/utils'
import { DashboardData } from '@/types'

interface RecentTransactionsProps {
  data?: DashboardData
  isLoading: boolean
}

function formatShortDate(dateStr: string): string {
  const d = new Date(dateStr)
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`
}

export function RecentTransactions({ data, isLoading }: RecentTransactionsProps) {
  const txs = data?.recentTransactions ?? []

  return (
    <div className="card" style={{ padding: 'var(--space-6)', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
        <div className="card-title-lg">Recent transactions</div>
        <Link href="/transactions" className="btn btn-ghost btn-sm" style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--accent-blue)' }}>
          View all <ArrowRight size={14} />
        </Link>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {[...Array(5)].map((_, i) => <div key={i} className="skeleton" style={{ height: 48, borderRadius: 'var(--radius-sm)' }} />)}
        </div>
      ) : txs.length === 0 ? (
        <div className="empty-state" style={{ flex: 1 }}>
          <div className="icon-tile" style={{ width: 48, height: 48 }}>
            <ReceiptText size={22} />
          </div>
          <span style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-2)' }}>No transactions yet</span>
        </div>
      ) : (
        <div style={{ flex: 1, overflowX: 'auto' }}>
          <table className="table" style={{ minWidth: 480 }}>
            <thead>
              <tr>
                <th>Date</th>
                <th>Transaction</th>
                <th>Type</th>
                <th style={{ textAlign: 'right' }}>Amount</th>
              </tr>
            </thead>
            <tbody>
              {txs.map(tx => {
                const typeClass = tx.type === 'income' ? 'table-row-income'
                  : tx.type === 'expense' ? 'table-row-expense'
                  : 'table-row-transfer'

                return (
                  <tr key={tx.id} className={typeClass}>
                    <td style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)', whiteSpace: 'nowrap' }}>
                      {formatShortDate(tx.date)}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2-5)' }}>
                        <div style={{
                          width: 34,
                          height: 34,
                          borderRadius: 'var(--radius-sm)',
                          background: tx.type === 'transfer' ? 'var(--accent-blue-subtle)' : `${tx.categoryColor}18`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: 16,
                          flexShrink: 0,
                        }}>
                          {tx.type === 'transfer' ? '↔️' : tx.categoryIcon}
                        </div>
                        <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>
                          {tx.description}
                        </span>
                      </div>
                    </td>
                    <td>
                      <span className={
                        tx.type === 'transfer' ? 'badge badge-blue'
                        : tx.type === 'income' ? 'badge badge-green'
                        : 'badge'
                      } style={
                        tx.type !== 'transfer' && tx.type !== 'income'
                          ? { background: `${tx.categoryColor}12`, color: tx.categoryColor }
                          : undefined
                      }>
                        {tx.type === 'transfer' ? 'Transfer' : tx.categoryName}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                      <span style={{
                        fontSize: 'var(--text-sm)',
                        fontWeight: 700,
                        color: tx.type === 'income' ? 'var(--accent-green)'
                             : tx.type === 'expense' ? 'var(--text-primary)'
                             : 'var(--accent-blue)',
                      }}>
                        {tx.type === 'income' ? '+' : tx.type === 'expense' ? '-' : ''}
                        {formatVND(tx.amount)}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
