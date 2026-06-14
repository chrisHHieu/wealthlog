import { AlertCircle, CheckCircle2, Target, TrendingUp } from 'lucide-react'
import { formatVNDCompact } from '@/lib/utils'
import { PeriodSummary } from '@/types'
import { ReportMode } from '@/hooks/useReports'
import { ReportAnalysis } from '../reportAnalysis'

interface ReportActionItemsProps {
  analysis: ReportAnalysis
  current: PeriodSummary
  mode: ReportMode
}

const SAVINGS_TARGET_PCT = 20

export function ReportActionItems({ analysis, current, mode }: ReportActionItemsProps) {
  const perPeriod = mode === 'month' ? 'month' : 'year'

  const expenseItem = analysis.expenseDeltaPct <= 0
    ? {
        icon: CheckCircle2,
        color: 'var(--accent-green)',
        title: 'Keep expense discipline',
        detail: `Expenses are ${formatVNDCompact(Math.abs(analysis.expenseDeltaAmount))} lower than the previous ${perPeriod}. Keep the same spending controls.`,
      }
    : {
        icon: AlertCircle,
        color: 'var(--accent-red)',
        title: 'Review expense growth',
        detail: `Expenses grew ${formatVNDCompact(analysis.expenseDeltaAmount)} (+${analysis.expenseDeltaPct.toFixed(1)}%) vs the previous ${perPeriod}${analysis.topIncrease ? `, led by ${analysis.topIncrease.name}` : ''}.`,
      }

  const trimItem = analysis.topExpense
    ? {
        icon: Target,
        color: 'var(--accent-blue)',
        title: `Trim ${analysis.topExpense.name}`,
        detail: `Cutting ${analysis.topExpense.name} by 10% frees ≈ ${formatVNDCompact(analysis.topExpense.current * 0.1)} per ${perPeriod}${mode === 'month' ? ` (~${formatVNDCompact(analysis.topExpense.current * 0.1 * 12)}/year)` : ''}.`,
      }
    : {
        icon: Target,
        color: 'var(--accent-blue)',
        title: 'Define category budgets',
        detail: 'No dominant expense category is available for this period.',
      }

  const savingsGap = current.income * (SAVINGS_TARGET_PCT / 100) - current.savings
  const savingsItem = current.savingsRate >= SAVINGS_TARGET_PCT
    ? {
        icon: CheckCircle2,
        color: 'var(--accent-green)',
        title: `Savings rate above ${SAVINGS_TARGET_PCT}%`,
        detail: `You saved ${current.savingsRate.toFixed(1)}% of income this ${perPeriod} — ahead of the ${SAVINGS_TARGET_PCT}% guideline.`,
      }
    : {
        icon: TrendingUp,
        color: 'var(--accent-gold)',
        title: `Reach a ${SAVINGS_TARGET_PCT}% savings rate`,
        detail: current.income > 0
          ? `Saving ${formatVNDCompact(Math.max(0, savingsGap))} more this ${perPeriod} would lift your rate from ${current.savingsRate.toFixed(1)}% to ${SAVINGS_TARGET_PCT}%.`
          : 'Record income for this period to track your savings rate.',
      }

  const items = [expenseItem, trimItem, savingsItem]

  return (
    <section className="card" style={{ padding: 20 }}>
      <div className="card-title" style={{ marginBottom: 14 }}>Action items</div>
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
