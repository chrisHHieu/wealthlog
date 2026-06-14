import { Sparkline } from '@/components/ui/Sparkline'
import { formatVNDCompact } from '@/lib/utils'
import { ChartPoint } from '@/types'

interface MonthlyBreakdownTableProps {
  chartData: ChartPoint[]
  isLoading: boolean
}

export function MonthlyBreakdownTable({ chartData, isLoading }: MonthlyBreakdownTableProps) {
  if (isLoading) {
    return (
      <div className="card" style={{ padding: 20 }}>
        <div className="skeleton" style={{ height: 18, width: 200, marginBottom: 14 }} />
        <div className="skeleton" style={{ height: 280, borderRadius: 8 }} />
      </div>
    )
  }

  const rows = chartData.map(p => {
    const savings = p.income - p.expense
    const rate = p.income > 0 ? (savings / p.income) * 100 : null
    return { ...p, savings, rate, hasActivity: p.income > 0 || p.expense > 0 }
  })

  const activeRows = rows.filter(r => r.hasActivity)
  const bestNet = activeRows.length ? Math.max(...activeRows.map(r => r.savings)) : 0
  const worstNet = activeRows.length ? Math.min(...activeRows.map(r => r.savings)) : 0

  const totalIncome = rows.reduce((s, r) => s + r.income, 0)
  const totalExpense = rows.reduce((s, r) => s + r.expense, 0)
  const totalSavings = totalIncome - totalExpense
  const overallRate = totalIncome > 0 ? (totalSavings / totalIncome) * 100 : 0

  const rateSeries = activeRows.map(r => r.rate ?? 0)

  return (
    <section className="card" style={{ padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 14 }}>
        <div>
          <div className="card-title">Month by month</div>
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 2 }}>
            Savings rate trend across active months
          </div>
        </div>
        {rateSeries.length >= 2 && (
          <div style={{ width: 160, flexShrink: 0 }}>
            <Sparkline data={rateSeries} height={32} stroke={overallRate >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'} />
          </div>
        )}
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="table" style={{ minWidth: 520 }}>
          <thead>
            <tr>
              <th>Month</th>
              <th style={{ textAlign: 'right' }}>Income</th>
              <th style={{ textAlign: 'right' }}>Expense</th>
              <th style={{ textAlign: 'right' }}>Net</th>
              <th style={{ textAlign: 'right' }}>Rate</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(row => {
              const isBest = row.hasActivity && row.savings === bestNet && activeRows.length > 1
              const isWorst = row.hasActivity && row.savings === worstNet && activeRows.length > 1 && worstNet !== bestNet
              return (
                <tr key={row.label} style={{ opacity: row.hasActivity ? 1 : 0.45 }}>
                  <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    {row.label}
                    {isBest && <span className="badge badge-green" style={{ marginLeft: 8 }}>Best</span>}
                    {isWorst && <span className="badge badge-red" style={{ marginLeft: 8 }}>Worst</span>}
                  </td>
                  <td style={{ textAlign: 'right', color: 'var(--text-secondary)' }}>{row.income > 0 ? formatVNDCompact(row.income) : '—'}</td>
                  <td style={{ textAlign: 'right', color: 'var(--text-secondary)' }}>{row.expense > 0 ? formatVNDCompact(row.expense) : '—'}</td>
                  <td style={{ textAlign: 'right', fontWeight: 600, color: row.savings >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                    {row.hasActivity ? formatVNDCompact(row.savings) : '—'}
                  </td>
                  <td style={{ textAlign: 'right', color: 'var(--text-secondary)' }}>
                    {row.rate !== null ? `${row.rate.toFixed(0)}%` : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
          <tfoot>
            <tr>
              <td style={{ fontWeight: 700, color: 'var(--text-primary)', borderTop: '2px solid var(--surface-border)' }}>Total</td>
              <td style={{ textAlign: 'right', fontWeight: 700, borderTop: '2px solid var(--surface-border)' }}>{formatVNDCompact(totalIncome)}</td>
              <td style={{ textAlign: 'right', fontWeight: 700, borderTop: '2px solid var(--surface-border)' }}>{formatVNDCompact(totalExpense)}</td>
              <td style={{ textAlign: 'right', fontWeight: 700, borderTop: '2px solid var(--surface-border)', color: totalSavings >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                {formatVNDCompact(totalSavings)}
              </td>
              <td style={{ textAlign: 'right', fontWeight: 700, borderTop: '2px solid var(--surface-border)' }}>{overallRate.toFixed(1)}%</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  )
}
