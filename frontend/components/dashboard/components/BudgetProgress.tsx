import { motion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import Link from 'next/link'
import { formatVNDCompact } from '@/lib/utils'
import { DashboardData } from '@/types'

interface BudgetProgressProps {
  data?: DashboardData
  isLoading: boolean
}

export function BudgetProgress({ data, isLoading }: BudgetProgressProps) {
  const budgets = data?.budgetProgress ?? []

  return (
    <div className="card" style={{ padding: 'var(--space-5)', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
        <div style={{ fontWeight: 700, fontSize: 'var(--text-base)' }}>Budget progress</div>
        <Link href="/budget" className="btn btn-ghost btn-sm" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          View all <ArrowRight size={14} />
        </Link>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 44, borderRadius: 'var(--radius-sm)' }} />)}
        </div>
      ) : budgets.length === 0 ? (
        <div className="empty-state" style={{ flex: 1, padding: 'var(--space-6) var(--space-3)' }}>
          <span style={{ fontSize: 32 }}>📋</span>
          <span style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-1)', color: 'var(--text-tertiary)' }}>No budgets set</span>
          <Link href="/budget" className="btn btn-primary btn-sm" style={{ marginTop: 'var(--space-2)' }}>
            Create budget
          </Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', flex: 1 }}>
          {budgets.slice(0, 4).map((b, i) => {
            const pct = Math.min(100, b.budgetAmount > 0 ? (b.spentAmount / b.budgetAmount) * 100 : 0)
            const isOver = pct >= 90
            const barColor = isOver ? 'var(--accent-red)' : b.categoryColor

            return (
              <div key={b.categoryId} className={isOver ? 'pulse-alert' : ''} style={{ borderRadius: 'var(--radius-sm)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-1-5)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <span style={{ fontSize: 14 }}>{b.categoryIcon}</span>
                    <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {b.categoryName}
                    </span>
                  </div>
                  <span style={{ fontSize: 'var(--text-xs)', color: isOver ? 'var(--accent-red)' : 'var(--text-tertiary)', fontWeight: 600 }}>
                    {formatVNDCompact(b.spentAmount)} / {formatVNDCompact(b.budgetAmount)}
                  </span>
                </div>
                <div className="progress-bar">
                  <motion.div
                    className="progress-bar-fill"
                    style={{ background: barColor }}
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.8, delay: i * 0.08, ease: [0.25, 0.46, 0.45, 0.94] }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
