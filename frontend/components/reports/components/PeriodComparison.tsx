import { motion } from 'framer-motion'
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react'
import { formatVNDCompact } from '@/lib/utils'
import { CategoryComparison } from '@/types'

interface PeriodComparisonProps {
  expenseByCategory: CategoryComparison[]
  incomeByCategory: CategoryComparison[]
  isLoading: boolean
}

function ChangeIndicator({ current, previous }: { current: number; previous: number }) {
  if (previous === 0 && current === 0) {
    return <span className="change-indicator muted"><Minus size={12} /></span>
  }
  const pct = previous === 0 ? 100 : ((current - previous) / previous) * 100
  const isUp = pct > 0
  return (
    <span className={`change-indicator ${isUp ? 'danger' : 'success'}`}>
      {isUp ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
      {Math.abs(pct).toFixed(1)}%
    </span>
  )
}

function ComparisonTable({ data, type }: { data: CategoryComparison[]; type: 'expense' | 'income' }) {
  const filtered = data.filter(c => c.current > 0 || c.previous > 0)
  if (filtered.length === 0) return null

  const total = {
    current: filtered.reduce((s, c) => s + c.current, 0),
    previous: filtered.reduce((s, c) => s + c.previous, 0),
  }

  return (
    <div className="card comparison-card">
      <div className="card-title" style={{ marginBottom: 4 }}>
        {type === 'expense' ? 'Expense comparison' : 'Income comparison'}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 16 }}>
        Current vs previous period by category
      </div>

      <div className="comparison-table-wrap">
        <table className="comparison-table">
          <thead>
            <tr>
              <th>Category</th>
              <th>Previous</th>
              <th>Current</th>
              <th>Delta</th>
              <th>Share</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((cat, i) => (
              <motion.tr
                key={cat.categoryId}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: i * 0.03 }}
              >
                <td>
                  <div className="category-cell">
                    <div
                      className="category-icon"
                      style={{ background: `${cat.color}18` }}
                    >
                      {cat.icon}
                    </div>
                    <span>{cat.name}</span>
                  </div>
                </td>
                <td className="amount muted">
                  {formatVNDCompact(cat.previous)}
                </td>
                <td className="amount strong">
                  {formatVNDCompact(cat.current)}
                </td>
                <td className="delta">
                  <ChangeIndicator current={cat.current} previous={cat.previous} />
                </td>
                <td className="share">
                  {cat.pct.toFixed(1)}%
                </td>
              </motion.tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td>Total</td>
              <td className="amount muted">
                {formatVNDCompact(total.previous)}
              </td>
              <td className="amount strong">
                {formatVNDCompact(total.current)}
              </td>
              <td className="delta">
                <ChangeIndicator current={total.current} previous={total.previous} />
              </td>
              <td className="share">
                100%
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}

function ComparisonStyles() {
  return (
    <style jsx global>{`
      .comparison-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: var(--space-5);
        align-items: start;
      }

      .comparison-card {
        overflow: hidden;
        padding: 20px;
      }

      .comparison-table-wrap {
        overflow-x: auto;
        scrollbar-width: thin;
      }

      .comparison-table {
        width: 100%;
        min-width: 620px;
        border-collapse: collapse;
        table-layout: fixed;
        font-size: 13px;
      }

      .comparison-table th,
      .comparison-table td {
        border-bottom: 1px solid var(--surface-border);
        padding: 11px 10px;
        vertical-align: middle;
      }

      .comparison-table th {
        color: var(--text-secondary);
        font-size: 11px;
        font-weight: 700;
        text-align: right;
      }

      .comparison-table th:first-child,
      .comparison-table td:first-child {
        width: 38%;
        text-align: left;
        padding-left: 0;
      }

      .comparison-table th:nth-child(2),
      .comparison-table th:nth-child(3),
      .comparison-table td:nth-child(2),
      .comparison-table td:nth-child(3) {
        width: 17%;
      }

      .comparison-table th:nth-child(4),
      .comparison-table td:nth-child(4) {
        width: 16%;
      }

      .comparison-table th:last-child,
      .comparison-table td:last-child {
        width: 12%;
        padding-right: 0;
      }

      .comparison-table tbody tr:last-child td {
        border-bottom: 1px solid var(--surface-border);
      }

      .comparison-table tfoot td {
        border-bottom: 0;
        border-top: 2px solid var(--surface-border);
        color: var(--text-primary);
        font-weight: 800;
      }

      .category-cell {
        display: flex;
        align-items: center;
        gap: 9px;
        min-width: 0;
        color: var(--text-primary);
        font-weight: 650;
        line-height: 1.25;
      }

      .category-cell span:last-child {
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .category-icon {
        width: 28px;
        height: 28px;
        border-radius: 7px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex: 0 0 auto;
        font-size: 13px;
      }

      .comparison-table .amount,
      .comparison-table .delta,
      .comparison-table .share {
        text-align: right;
        white-space: nowrap;
        font-variant-numeric: tabular-nums;
      }

      .comparison-table .amount.muted {
        color: var(--text-secondary);
        font-weight: 550;
      }

      .comparison-table .amount.strong {
        color: var(--text-primary);
        font-weight: 800;
      }

      .comparison-table .share {
        color: var(--text-tertiary);
        font-size: 12px;
      }

      .change-indicator {
        display: inline-flex;
        align-items: center;
        justify-content: flex-end;
        gap: 2px;
        min-width: 68px;
        font-size: 12px;
        font-weight: 700;
        white-space: nowrap;
      }

      .change-indicator.success {
        color: var(--accent-green);
      }

      .change-indicator.danger {
        color: var(--accent-red);
      }

      .change-indicator.muted {
        color: var(--text-tertiary);
      }

      @media (max-width: 1400px) {
        .comparison-grid {
          grid-template-columns: 1fr;
        }
      }
    `}</style>
  )
}

export function PeriodComparison({ expenseByCategory, incomeByCategory, isLoading }: PeriodComparisonProps) {
  if (isLoading) {
    return (
      <>
        <div className="comparison-grid">
          {[0, 1].map(i => (
            <div key={i} className="card" style={{ padding: 20 }}>
              <div className="skeleton" style={{ height: 18, width: 160, marginBottom: 16 }} />
              {[...Array(4)].map((_, j) => <div key={j} className="skeleton" style={{ height: 36, marginBottom: 8 }} />)}
            </div>
          ))}
        </div>
        <ComparisonStyles />
      </>
    )
  }

  return (
    <>
      <div className="comparison-grid">
        <ComparisonTable data={expenseByCategory} type="expense" />
        <ComparisonTable data={incomeByCategory} type="income" />
      </div>
      <ComparisonStyles />
    </>
  )
}
