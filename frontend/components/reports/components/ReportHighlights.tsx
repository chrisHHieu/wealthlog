import { ArrowDownRight, ArrowUpRight, CalendarDays } from 'lucide-react'
import { formatVNDCompact } from '@/lib/utils'
import { ReportAnalysis } from '../reportAnalysis'

interface ReportHighlightsProps {
  analysis: ReportAnalysis
  mode: 'month' | 'year'
}

function HighlightCard({ title, label, value, color }: { title: string; label: string; value: string; color: string }) {
  return (
    <div className="card report-highlight-card">
      <div className="highlight-title">{title}</div>
      <div className="highlight-label">{label}</div>
      <div className="highlight-value" style={{ color }}>{value}</div>
    </div>
  )
}

export function ReportHighlights({ analysis, mode }: ReportHighlightsProps) {
  return (
    <div className="report-highlight-grid">
      <HighlightCard
        title={mode === 'month' ? 'Best day' : 'Best month'}
        label={analysis.bestPoint ? `${mode === 'month' ? 'Day' : 'Month'} ${analysis.bestPoint.label}` : 'No activity'}
        value={analysis.bestPoint ? formatVNDCompact(analysis.bestPoint.income - analysis.bestPoint.expense) : '0 VND'}
        color="var(--accent-green)"
      />
      <HighlightCard
        title={mode === 'month' ? 'Weakest day' : 'Weakest month'}
        label={analysis.worstPoint ? `${mode === 'month' ? 'Day' : 'Month'} ${analysis.worstPoint.label}` : 'No activity'}
        value={analysis.worstPoint ? formatVNDCompact(analysis.worstPoint.income - analysis.worstPoint.expense) : '0 VND'}
        color="var(--accent-red)"
      />
      <div className="card report-highlight-card icon-card">
        <ArrowUpRight size={17} color="var(--accent-red)" />
        <div className="highlight-title">Largest category increase</div>
        <div className="highlight-label">{analysis.topIncrease?.name ?? 'No increase'}</div>
        <div className="highlight-value" style={{ color: 'var(--accent-red)' }}>
          {analysis.topIncrease ? `+${formatVNDCompact(analysis.topIncrease.current - analysis.topIncrease.previous)}` : '0 VND'}
        </div>
      </div>
      <div className="card report-highlight-card icon-card">
        <ArrowDownRight size={17} color="var(--accent-green)" />
        <div className="highlight-title">Largest category decrease</div>
        <div className="highlight-label">{analysis.topDecrease?.name ?? 'No decrease'}</div>
        <div className="highlight-value" style={{ color: 'var(--accent-green)' }}>
          {analysis.topDecrease ? formatVNDCompact(analysis.topDecrease.current - analysis.topDecrease.previous) : '0 VND'}
        </div>
      </div>
      <style jsx global>{`
        .report-highlight-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: var(--space-4);
        }

        .report-highlight-card {
          min-height: 118px;
          padding: 18px;
        }

        .icon-card svg {
          margin-bottom: 8px;
        }

        .highlight-title {
          color: var(--text-tertiary);
          font-size: 12px;
          line-height: 1.35;
          margin-bottom: 8px;
        }

        .highlight-label {
          color: var(--text-primary);
          font-size: 15px;
          font-weight: 750;
          line-height: 1.3;
          margin-bottom: 6px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .highlight-value {
          font-size: 13px;
          font-weight: 800;
          line-height: 1.25;
          white-space: nowrap;
        }
      `}</style>
    </div>
  )
}

export function YearlyHealthStrip({ analysis }: { analysis: ReportAnalysis }) {
  const items = [
    { label: 'Estimated fixed costs', value: formatVNDCompact(analysis.fixedExpense), color: 'var(--accent-blue)' },
    { label: 'Estimated variable costs', value: formatVNDCompact(analysis.variableExpense), color: 'var(--accent-purple)' },
    { label: 'Fixed cost ratio', value: `${analysis.fixedExpensePct.toFixed(1)}%`, color: 'var(--accent-gold)' },
  ]

  return (
    <section className="card" style={{ padding: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <CalendarDays size={17} color="var(--accent-green)" />
        <div className="card-title">Yearly financial health</div>
      </div>
      <div className="yearly-health-grid">
        {items.map(item => (
          <div key={item.label} style={{ borderLeft: `3px solid ${item.color}`, paddingLeft: 12 }}>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 4 }}>{item.label}</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)' }}>{item.value}</div>
          </div>
        ))}
      </div>
      <style jsx global>{`
        .yearly-health-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 14px;
        }
      `}</style>
    </section>
  )
}
