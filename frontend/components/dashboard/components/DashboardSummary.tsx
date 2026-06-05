import { AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import { formatVNDCompact } from '@/lib/utils'
import { DashboardData } from '@/types'
import { DashboardInsights } from '../dashboardInsights'

interface DashboardSummaryProps {
  data?: DashboardData
  insights: DashboardInsights
  isLoading: boolean
}

const toneConfig = {
  good: { color: 'var(--accent-green)', icon: CheckCircle2 },
  warning: { color: 'var(--accent-red)', icon: AlertTriangle },
  neutral: { color: 'var(--accent-blue)', icon: Info },
}

export function DashboardSummary({ data, insights, isLoading }: DashboardSummaryProps) {
  if (isLoading) {
    return (
      <div className="card" style={{ padding: 20 }}>
        <div className="skeleton" style={{ height: 20, width: 220, marginBottom: 12 }} />
        <div className="skeleton" style={{ height: 50, borderRadius: 8 }} />
      </div>
    )
  }

  const primary = insights.insights[0]
  const monthLabel = data?.selectedMonth
    ? (() => {
      const [year, month] = data.selectedMonth.split('-')
      return `${new Date(Number(year), Number(month) - 1, 1).toLocaleString('en-US', { month: 'long' })} ${year}`
    })()
    : 'Current month'

  return (
    <section className="card" style={{ padding: 22 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 20 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 8 }}>
            Month-to-date summary - {monthLabel}
          </div>
          <h2 style={{ fontSize: 19, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 6 }}>
            {primary?.title ?? 'Financial snapshot'}
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.65, maxWidth: 760 }}>
            {primary?.detail ?? 'No activity is available yet.'}
            {data && ` Net savings are ${formatVNDCompact(data.currentMonth.savings)} after ${formatVNDCompact(data.currentMonth.expense)} in expenses.`}
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 120px)', gap: 10, flexShrink: 0 }}>
          <Metric label="Savings rate" value={`${insights.savingsRate.toFixed(1)}%`} color="var(--accent-green)" />
          <Metric label="Expense change" value={`${insights.expenseDeltaPct >= 0 ? '+' : ''}${insights.expenseDeltaPct.toFixed(1)}%`} color={insights.expenseDeltaPct <= 0 ? 'var(--accent-green)' : 'var(--accent-red)'} />
          <Metric label="Income change" value={`${insights.incomeDeltaPct >= 0 ? '+' : ''}${insights.incomeDeltaPct.toFixed(1)}%`} color={insights.incomeDeltaPct >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'} />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12, marginTop: 18 }}>
        {insights.insights.slice(1, 4).map((item) => {
          const cfg = toneConfig[item.tone]
          const Icon = cfg.icon
          return (
            <div key={item.title} style={{ border: `1px solid ${cfg.color}25`, background: `${cfg.color}10`, borderRadius: 8, padding: 12 }}>
              <Icon size={16} color={cfg.color} />
              <div style={{ fontSize: 12, fontWeight: 700, marginTop: 7, color: 'var(--text-primary)' }}>{item.title}</div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5, marginTop: 4 }}>{item.detail}</div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function Metric({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ border: '1px solid var(--surface-border)', borderRadius: 8, padding: 12, background: 'var(--surface)' }}>
      <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginBottom: 5 }}>{label}</div>
      <div style={{ fontSize: 17, fontWeight: 800, color }}>{value}</div>
    </div>
  )
}
