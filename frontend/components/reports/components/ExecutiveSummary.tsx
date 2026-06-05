import { AlertTriangle, CheckCircle2, Info, TrendingDown, TrendingUp } from 'lucide-react'
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

function DeltaLine({ label, value, positiveWhenUp = true }: { label: string; value: number; positiveWhenUp?: boolean }) {
  const isPositive = positiveWhenUp ? value >= 0 : value <= 0
  const Icon = value >= 0 ? TrendingUp : TrendingDown
  return (
    <div className="delta-line">
      <span>{label}</span>
      <span style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'flex-end',
        gap: 4,
        fontSize: 12,
        fontWeight: 700,
        color: isPositive ? 'var(--accent-green)' : 'var(--accent-red)',
        minWidth: 0,
      }}>
        <Icon size={13} />
        {value >= 0 ? '+' : ''}{value.toFixed(1)}%
      </span>
      <style jsx>{`
        .delta-line {
          display: grid;
          grid-template-columns: minmax(0, 1fr) max-content;
          align-items: center;
          gap: 10px;
          padding: 8px 0;
          border-bottom: 1px solid var(--surface-border);
          min-width: 0;
        }

        .delta-line span:first-child {
          color: var(--text-secondary);
          font-size: 12px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        @media (max-width: 640px) {
          .delta-line {
            grid-template-columns: 1fr;
            gap: 3px;
          }

          .delta-line span:last-child {
            justify-content: flex-start !important;
          }
        }
      `}</style>
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
        <div style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 8 }}>
          {mode === 'month' ? 'Monthly summary' : 'Yearly summary'} - {periodLabel}
        </div>
        <h2 style={{ fontSize: 20, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 8 }}>
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
                border: `1px solid ${style.color}30`,
                background: `${style.color}10`,
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
        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>Period movement</div>
        <DeltaLine label="Income" value={analysis.incomeDeltaPct} />
        <DeltaLine label="Expenses" value={analysis.expenseDeltaPct} positiveWhenUp={false} />
        <DeltaLine label="Net savings" value={analysis.savingsDeltaPct} />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 14 }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 4 }}>Fixed costs</div>
            <div style={{ fontSize: 15, fontWeight: 800 }}>{formatVNDCompact(analysis.fixedExpense)}</div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 4 }}>Variable costs</div>
            <div style={{ fontSize: 15, fontWeight: 800 }}>{formatVNDCompact(analysis.variableExpense)}</div>
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
