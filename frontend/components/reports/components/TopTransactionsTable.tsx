import { formatDateVI, formatVNDCompact } from '@/lib/utils'
import { TopTransaction } from '@/types'

interface TopTransactionsTableProps {
  transactions: TopTransaction[]
}

export function TopTransactionsTable({ transactions }: TopTransactionsTableProps) {
  return (
    <section className="card top-transactions-card">
      <div style={{ fontSize: 15, fontWeight: 750, marginBottom: 4 }}>Largest transactions</div>
      <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 16 }}>Highest-value rows in the selected period</div>

      {transactions.length === 0 ? (
        <div style={{ color: 'var(--text-tertiary)', fontSize: 13, padding: '20px 0', textAlign: 'center' }}>No transactions in this period</div>
      ) : (
        <div className="top-transactions-scroll">
          <div className="top-transactions-grid header-row">
            <div>Description</div>
            <div>Category</div>
            <div>Date</div>
            <div>Amount</div>
          </div>
          {transactions.map((tx, index) => (
            <div key={`${tx.date}-${tx.amount}-${index}`} className="top-transactions-grid transaction-row">
              <div className="transaction-description" title={tx.description}>
                {tx.description}
              </div>
              <div className="transaction-category" title={tx.categoryName}>
                <span aria-hidden="true">{tx.categoryIcon}</span>
                <span>{tx.categoryName}</span>
              </div>
              <div className="transaction-date">{formatDateVI(tx.date)}</div>
              <div className={`transaction-amount ${tx.type === 'income' ? 'income' : 'expense'}`}>
                {tx.type === 'income' ? '+' : '-'}{formatVNDCompact(tx.amount)}
              </div>
            </div>
          ))}
        </div>
      )}

      <style jsx>{`
        .top-transactions-card {
          overflow: hidden;
          padding: 20px;
        }

        .top-transactions-scroll {
          overflow-x: auto;
          scrollbar-width: thin;
        }

        .top-transactions-grid {
          display: grid;
          grid-template-columns: minmax(260px, 1fr) 150px 98px 132px;
          column-gap: 18px;
          min-width: 700px;
          align-items: center;
        }

        .header-row {
          border-bottom: 1px solid var(--surface-border);
          color: var(--text-secondary);
          font-size: 11px;
          font-weight: 700;
          padding: 8px 0;
        }

        .header-row > div:last-child {
          text-align: right;
        }

        .transaction-row {
          border-bottom: 1px solid var(--surface-border);
          padding: 12px 0;
          font-size: 13px;
        }

        .transaction-description {
          color: var(--text-primary);
          font-weight: 700;
          line-height: 1.35;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .transaction-category {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          min-width: 0;
          color: var(--text-secondary);
          white-space: nowrap;
        }

        .transaction-category span:last-child {
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .transaction-date {
          color: var(--text-secondary);
          font-variant-numeric: tabular-nums;
          white-space: nowrap;
        }

        .transaction-amount {
          text-align: right;
          font-weight: 850;
          font-variant-numeric: tabular-nums;
          white-space: nowrap;
        }

        .transaction-amount.income {
          color: var(--accent-green);
        }

        .transaction-amount.expense {
          color: var(--accent-red);
        }
      `}</style>
    </section>
  )
}
