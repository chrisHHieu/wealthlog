import { motion } from 'framer-motion'
import { AnimatedCounter } from '@/components/ui/AnimatedCounter'
import { Sparkline } from '@/components/ui/Sparkline'
import { StatusBadge, TrendBadge } from '@/components/ui/Badge'
import { Stat } from '@/components/ui/Stat'
import { formatVNDCompact } from '@/lib/utils'
import { DashboardData } from '@/types'

interface KPICardsProps {
  data?: DashboardData
  isLoading: boolean
  incomePct: string | null
  expensePct: string | null
}

function monthLabel(data?: DashboardData) {
  if (!data?.selectedMonth) {
    return new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
  }
  const [y, m] = data.selectedMonth.split('-').map(Number)
  return new Date(y, m - 1, 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
}

export function KPICards({ data, isLoading, incomePct, expensePct }: KPICardsProps) {
  if (isLoading) {
    return (
      <div className="kpi-hero">
        <div className="skeleton" style={{ height: 14, width: 120, marginBottom: 12 }} />
        <div className="skeleton" style={{ height: 56, width: 320, maxWidth: '100%', marginBottom: 16 }} />
        <div className="skeleton" style={{ height: 48 }} />
      </div>
    )
  }

  const netWorth = data?.netWorth ?? 0
  const income = data?.currentMonth.income ?? 0
  const expense = data?.currentMonth.expense ?? 0
  const savings = data?.currentMonth.savings ?? 0
  const isPositive = savings >= 0
  const savingsTrend = data?.monthlyChart.map(m => m.income - m.expense) ?? []

  const savingsRate = data && data.currentMonth.income > 0
    ? Math.round(data.currentMonth.savings / data.currentMonth.income * 100)
    : 0
  const prevSavingsRate = data && data.previousMonth.income > 0
    ? Math.round(data.previousMonth.savings / data.previousMonth.income * 100)
    : 0
  const savingsRatePct = prevSavingsRate !== 0
    ? ((savingsRate - prevSavingsRate) / Math.abs(prevSavingsRate) * 100).toFixed(1)
    : null

  return (
    <motion.section
      className="kpi-hero"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <div className="kpi-hero-layout">
        {/* Net worth — the one number that matters */}
        <div className="kpi-hero-networth">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2-5)' }}>
            <span className="stat-label">Net worth</span>
            <StatusBadge label={isPositive ? 'MTD positive' : 'MTD negative'} isGood={isPositive} />
          </div>

          <div className="font-display kpi-hero-amount">
            <AnimatedCounter value={netWorth} format={v => formatVNDCompact(Math.round(v))} />
          </div>

          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
            {monthLabel(data)}
          </div>

          {savingsTrend.length >= 2 && (
            <div style={{ marginTop: 'var(--space-3)', maxWidth: 360 }}>
              <Sparkline
                data={savingsTrend}
                height={32}
                stroke={isPositive ? 'var(--accent-green)' : 'var(--accent-red)'}
              />
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginTop: 'var(--space-1)' }}>
                Monthly savings trend
              </div>
            </div>
          )}
        </div>

        {/* Month-to-date figures */}
        <div className="stat-strip kpi-hero-stats">
          <Stat
            label="Income"
            value={<AnimatedCounter value={income} format={v => formatVNDCompact(Math.round(v))} />}
            color="var(--accent-green)"
            size="lg"
            badge={incomePct !== null ? <TrendBadge pctChange={incomePct} positiveIsGood /> : undefined}
          />
          <Stat
            label="Expense"
            value={<AnimatedCounter value={expense} format={v => formatVNDCompact(Math.round(v))} />}
            color="var(--accent-red)"
            size="lg"
            badge={expensePct !== null ? <TrendBadge pctChange={expensePct} positiveIsGood={false} /> : undefined}
          />
          <Stat
            label="Savings rate"
            value={<AnimatedCounter value={savingsRate} format={v => `${Math.round(v)}%`} />}
            size="lg"
            badge={savingsRatePct !== null ? <TrendBadge pctChange={savingsRatePct} positiveIsGood /> : undefined}
          />
        </div>
      </div>

      <style jsx>{`
        .kpi-hero-layout {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: var(--space-8);
        }
        .kpi-hero-networth {
          display: flex;
          flex-direction: column;
          gap: var(--space-2);
          min-width: 0;
        }
        .kpi-hero-layout :global(.kpi-hero-amount) {
          font-size: var(--text-5xl);
          font-weight: 500;
          color: var(--text-primary);
          line-height: 1.0;
          letter-spacing: var(--tracking-display);
        }
        .kpi-hero-layout :global(.kpi-hero-stats) {
          flex-shrink: 0;
          padding-top: var(--space-1);
        }
        @media (max-width: 1023px) {
          .kpi-hero-layout {
            flex-direction: column;
            gap: var(--space-5);
          }
          .kpi-hero-layout :global(.kpi-hero-amount) {
            font-size: var(--text-4xl);
          }
        }
      `}</style>
    </motion.section>
  )
}
