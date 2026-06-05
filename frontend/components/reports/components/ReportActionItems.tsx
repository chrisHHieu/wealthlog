import { AlertCircle, CheckCircle2, Target } from 'lucide-react'
import { formatVNDCompact } from '@/lib/utils'
import { ReportAnalysis } from '../reportAnalysis'

interface ReportActionItemsProps {
  analysis: ReportAnalysis
}

export function ReportActionItems({ analysis }: ReportActionItemsProps) {
  const items = [
    {
      icon: analysis.expenseDeltaPct <= 0 ? CheckCircle2 : AlertCircle,
      color: analysis.expenseDeltaPct <= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
      title: analysis.expenseDeltaPct <= 0 ? 'Keep expense discipline' : 'Review expense growth',
      detail: analysis.expenseDeltaPct <= 0
        ? 'Expenses are lower than the previous period. Keep the same spending controls.'
        : `Expenses increased by ${analysis.expenseDeltaPct.toFixed(1)}%. Review categories with the largest increases.`,
    },
    {
      icon: Target,
      color: 'var(--accent-blue)',
      title: analysis.topExpense ? `Watch ${analysis.topExpense.name}` : 'Define category budgets',
      detail: analysis.topExpense
        ? `${analysis.topExpense.name} is currently ${analysis.topExpense.pct.toFixed(1)}% of total expenses.`
        : 'No dominant expense category is available for this period.',
    },
    {
      icon: CheckCircle2,
      color: 'var(--accent-purple)',
      title: 'Fixed cost ratio',
      detail: `Estimated fixed costs are ${formatVNDCompact(analysis.fixedExpense)} (${analysis.fixedExpensePct.toFixed(1)}% of expenses).`,
    },
  ]

  return (
    <section className="card" style={{ padding: 20 }}>
      <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>Action items</div>
      <div className="report-action-grid">
        {items.map((item) => {
          const Icon = item.icon
          return (
            <div key={item.title} style={{
              border: '1px solid var(--surface-border)',
              borderRadius: 8,
              padding: 14,
              background: 'var(--surface)',
            }}>
              <Icon size={17} color={item.color} />
              <div style={{ fontSize: 13, fontWeight: 700, marginTop: 8, color: 'var(--text-primary)' }}>{item.title}</div>
              <div style={{ fontSize: 12, lineHeight: 1.55, color: 'var(--text-secondary)', marginTop: 5 }}>{item.detail}</div>
            </div>
          )
        })}
      </div>
      <style jsx>{`
        .report-action-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 14px;
        }
      `}</style>
    </section>
  )
}
