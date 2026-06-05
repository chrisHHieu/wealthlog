import { ChevronLeft, ChevronRight, Download } from 'lucide-react'
import { ReportMode, navigateMonth, getCurrentMonthStr, getCurrentYear } from '@/hooks/useReports'

interface ReportHeaderProps {
  mode: ReportMode
  setMode: (m: ReportMode) => void
  selectedMonth: string
  setSelectedMonth: (m: string) => void
  selectedYear: number
  setSelectedYear: (y: number | ((prev: number) => number)) => void
}

export function ReportHeader({ mode, setMode, selectedMonth, setSelectedMonth, selectedYear, setSelectedYear }: ReportHeaderProps) {
  const currentMonthStr = getCurrentMonthStr()
  const currentYear = getCurrentYear()

  const periodLabel = mode === 'month'
    ? (() => { const [y, m] = selectedMonth.split('-'); return `Month ${Number(m)}, ${y}` })()
    : `Year ${selectedYear}`

  return (
    <div className="report-header">
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Financial reports</h1>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          Detailed analysis and period comparison
        </p>
      </div>

      <div className="report-header-controls">
        {/* Mode toggle */}
        <div style={{
          display: 'flex', background: 'var(--surface)', borderRadius: 10,
          padding: 3, border: '1px solid var(--surface-border)',
        }}>
          {(['month', 'year'] as ReportMode[]).map(m => (
            <button
              key={m}
              onClick={() => setMode(m)}
              style={{
                padding: '5px 14px', borderRadius: 7, border: 'none', cursor: 'pointer',
                fontSize: 12, fontWeight: 500, transition: 'all 0.15s',
                background: mode === m ? 'var(--accent-green)' : 'transparent',
                color: mode === m ? '#0f0f14' : 'var(--text-secondary)',
              }}
            >
              {m === 'month' ? 'Month' : 'Year'}
            </button>
          ))}
        </div>

        {/* Period navigation */}
        {mode === 'month' ? (
          <div className="period-nav">
            <button onClick={() => setSelectedMonth(navigateMonth(selectedMonth, -1))} className="btn btn-ghost btn-sm" style={{ padding: '4px 6px' }}>
              <ChevronLeft size={15} />
            </button>
            <span className="period-label">
              {periodLabel}
            </span>
            <button
              onClick={() => selectedMonth >= currentMonthStr ? null : setSelectedMonth(navigateMonth(selectedMonth, 1))}
              className="btn btn-ghost btn-sm"
              style={{ padding: '4px 6px', opacity: selectedMonth >= currentMonthStr ? 0.3 : 1 }}
              disabled={selectedMonth >= currentMonthStr}
            >
              <ChevronRight size={15} />
            </button>
            {selectedMonth !== currentMonthStr && (
              <button onClick={() => setSelectedMonth(currentMonthStr)} className="btn btn-ghost btn-sm" style={{ fontSize: 11, padding: '3px 8px', color: 'var(--accent-green)' }}>
                Current
              </button>
            )}
          </div>
        ) : (
          <div className="period-nav">
            <button onClick={() => setSelectedYear(y => y - 1)} className="btn btn-ghost btn-sm" style={{ padding: '4px 6px' }} disabled={selectedYear <= 2020}>
              <ChevronLeft size={15} />
            </button>
            <span className="period-label year">
              {selectedYear}
            </span>
            <button
              onClick={() => selectedYear >= currentYear ? null : setSelectedYear(y => y + 1)}
              className="btn btn-ghost btn-sm"
              style={{ padding: '4px 6px', opacity: selectedYear >= currentYear ? 0.3 : 1 }}
              disabled={selectedYear >= currentYear}
            >
              <ChevronRight size={15} />
            </button>
          </div>
        )}

        {/* Export button */}
        <button
          className="btn btn-ghost btn-sm"
          style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, padding: '5px 10px' }}
          title="Export report (coming soon)"
          onClick={() => {/* TODO: implement export */}}
        >
          <Download size={14} />
          <span className="export-label">Export</span>
        </button>
      </div>
      <style jsx>{`
        .report-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 12px;
          min-width: 0;
        }

        .report-header-controls {
          display: flex;
          align-items: center;
          justify-content: flex-end;
          gap: 8px;
          flex-wrap: wrap;
          min-width: 0;
        }

        .period-nav {
          display: flex;
          align-items: center;
          gap: 4px;
          min-width: 0;
        }

        .period-label {
          color: var(--text-primary);
          font-size: 13px;
          font-weight: 650;
          min-width: 110px;
          text-align: center;
          white-space: nowrap;
        }

        .period-label.year {
          min-width: 60px;
        }

        @media (max-width: 640px) {
          .report-header {
            align-items: stretch;
            flex-direction: column;
          }

          .report-header-controls {
            justify-content: flex-start;
          }

          .period-label {
            min-width: 88px;
          }

          .export-label {
            display: none;
          }
        }
      `}</style>
    </div>
  )
}
