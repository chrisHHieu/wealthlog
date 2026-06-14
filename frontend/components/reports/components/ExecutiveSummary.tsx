import { AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import { formatVNDCompact } from '@/lib/utils'
import { ReportAnalysis } from '../reportAnalysis'
import { ReportMode } from '@/hooks/useReports'

interface ExecutiveSummaryProps {
  analysis: ReportAnalysis
  mode: ReportMode
  periodLabel: string
}

const toneStyles = {
  good: { color: 'var(--accent-green)', icon: CheckCircle2 },
  warning: { color: 'var(--accent-red)', icon: AlertTriangle },
  neutral: { color: 'var(--accent-blue)', icon: Info },
}

function AverageLine({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'baseline',
      justifyContent: 'space-between',
      gap: 10,
      padding: '8px 0',
      borderBottom: '1px solid var(--surface-border)',
      minWidth: 0,
    }}>
      <span style={{ color: 'var(--text-secondary)', fontSize: 12, whiteSpace: 'nowrap' }}>{label}</span>
      <span className="num-meta" style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>{value}</span>
    </div>
  )
}

export function ExecutiveSummary({ analysis, mode, periodLabel }: ExecutiveSummaryProps) {
  const summaryText = analysis.topExpense
    ? `${analysis.topExpense.name} is the largest expense category, while ${analysis.fixedExpensePct.toFixed(1)}% of expenses are estimated fixed costs.`
    : 'No expense activity is available for this period.'

  return (
    <div className="executive-summary-grid">
      <section className="card" style={{ padding: 22 }}>
        <div className="stat-label" style={{ marginBottom: 8 }}>
          {mode === 'month' ? 'Monthly summary' : 'Yearly summary'} · {periodLabel}
        </div>
        <h2 className="font-display" style={{ fontSize: 'clamp(22px, 1vw + 18px, 28px)', fontWeight: 500, letterSpacing: '-0.02em', lineHeight: 1.12, color: 'var(--text-primary)', marginBottom: 10 }}>
          {analysis.insights[0]?.title ?? 'Financial snapshot'}
        </h2>
        <p style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--text-secondary)', maxWidth: 780, marginBottom: 18 }}>
          {analysis.insights[0]?.detail} {summaryText}
        </p>

        <div className="executive-insight-grid">
          {analysis.insights.slice(1, 4).map((insight) => {
            const style = toneStyles[insight.tone]
            const Icon = style.icon
            return (
              <div key={insight.title} style={{
                border: `1px solid color-mix(in srgb, ${style.color} 15%, transparent)`,
                background: `color-mix(in srgb, ${style.color} 6%, transparent)`,
                borderRadius: 8,
                padding: 12,
                minHeight: 92,
              }}>
                <Icon size={16} color={style.color} />
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', marginTop: 8 }}>{insight.title}</div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5, marginTop: 4 }}>{insight.detail}</div>
              </div>
            )
          })}
        </div>
      </section>

      <aside className="card" style={{ padding: 20 }}>
        <div className="card-title" style={{ marginBottom: 10 }}>Period at a glance</div>
        <AverageLine
          label={mode === 'month' ? 'Avg spend / day' : 'Avg spend / month'}
          value={formatVNDCompact(analysis.avgExpensePerPoint)}
        />
        <AverageLine
          label={mode === 'month' ? 'Days with spending' : 'Months with spending'}
          value={`${analysis.activeSpendingPoints} / ${analysis.totalPoints}`}
        />
        {analysis.bestPoint && (
          <AverageLine
            label={mode === 'month' ? 'Best day (net)' : 'Best month (net)'}
            value={`${mode === 'month' ? 'Day ' : ''}${analysis.bestPoint.label} · ${formatVNDCompact(analysis.bestPoint.income - analysis.bestPoint.expense)}`}
          />
        )}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 14 }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 4 }}>Fixed costs</div>
            <div className="num-meta" style={{ fontSize: 15, fontWeight: 800 }}>{formatVNDCompact(analysis.fixedExpense)}</div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 4 }}>Variable costs</div>
            <div className="num-meta" style={{ fontSize: 15, fontWeight: 800 }}>{formatVNDCompact(analysis.variableExpense)}</div>
          </div>
        </div>
      </aside>
      <style jsx>{`
        .executive-summary-grid {
          display: grid;
          grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.9fr);
          gap: var(--space-5);
          min-width: 0;
        }

        .executive-insight-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 12px;
          min-width: 0;
        }

        @media (max-width: 1280px) {
          .executive-summary-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 640px) {
          .executive-insight-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  )
}
