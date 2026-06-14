import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Wallet } from 'lucide-react'
import { apiGet, queryKeys } from '@/lib/api'
import { formatVNDCompact } from '@/lib/utils'
import { CategoryComparison } from '@/types'

interface BudgetItem {
  id: string
  categoryId: string
  categoryName: string
  categoryIcon: string
  categoryColor: string
  amount: number
  month: string
}

interface BudgetVsActualProps {
  month: string
  expenseByCategory: CategoryComparison[]
}

export function BudgetVsActual({ month, expenseByCategory }: BudgetVsActualProps) {
  const { data: budgets = [], isLoading } = useQuery<BudgetItem[]>({
    queryKey: queryKeys.budget(month),
    queryFn: () => apiGet<BudgetItem[]>('/api/budgets', { month }),
  })

  if (isLoading) {
    return (
      <div className="card" style={{ padding: 20 }}>
        <div className="skeleton" style={{ height: 18, width: 180, marginBottom: 14 }} />
        <div className="skeleton" style={{ height: 140, borderRadius: 8 }} />
      </div>
    )
  }

  if (budgets.length === 0) {
    return (
      <section className="card" style={{ padding: 20 }}>
        <div className="card-title" style={{ marginBottom: 4 }}>Budget vs actual</div>
        <div className="empty-state" style={{ padding: 'var(--space-8) var(--space-4)' }}>
          <Wallet size={28} />
          <span style={{ fontSize: 'var(--text-sm)' }}>No budgets set for this month</span>
          <Link href="/budget" className="btn btn-secondary btn-sm">
            Set up budgets <ArrowRight size={13} />
          </Link>
        </div>
      </section>
    )
  }

  const actualByCategory = new Map(expenseByCategory.map(c => [c.categoryId, c.current]))
  const rows = budgets
    .map(b => {
      const actual = actualByCategory.get(b.categoryId) ?? 0
      return { ...b, actual, diff: actual - b.amount, usagePct: b.amount > 0 ? (actual / b.amount) * 100 : 0 }
    })
    .sort((a, b) => b.usagePct - a.usagePct)

  const totalPlanned = rows.reduce((s, r) => s + r.amount, 0)
  const totalActual = rows.reduce((s, r) => s + r.actual, 0)
  const overCount = rows.filter(r => r.diff > 0).length

  return (
    <section className="card" style={{ padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, marginBottom: 14 }}>
        <div>
          <div className="card-title">Budget vs actual</div>
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 2 }}>
            {overCount > 0 ? `${overCount} of ${rows.length} budgets exceeded` : `All ${rows.length} budgets on track`}
          </div>
        </div>
        <div style={{ fontSize: 12, color: totalActual > totalPlanned ? 'var(--accent-red)' : 'var(--accent-green)', fontWeight: 700, whiteSpace: 'nowrap' }}>
          {formatVNDCompact(totalActual)} / {formatVNDCompact(totalPlanned)}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {rows.map(row => {
          const over = row.diff > 0
          const barPct = Math.min(100, row.usagePct)
          return (
            <div key={row.id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 10, marginBottom: 5 }}>
                <span style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 600, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {row.categoryIcon} {row.categoryName}
                </span>
                <span style={{ fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                  {formatVNDCompact(row.actual)} / {formatVNDCompact(row.amount)}
                  <span style={{ marginLeft: 6, fontWeight: 700, color: over ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                    {over ? `+${formatVNDCompact(row.diff)}` : `−${formatVNDCompact(Math.abs(row.diff))}`}
                  </span>
                </span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-bar-fill"
                  style={{
                    width: `${barPct}%`,
                    background: over
                      ? 'var(--accent-red)'
                      : row.usagePct >= 80
                        ? 'var(--accent-gold)'
                        : 'var(--accent-green)',
                  }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
