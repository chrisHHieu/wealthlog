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
    ? (() => { const [y, m] = selectedMonth.split('-'); return `Tháng ${Number(m)}, ${y}` })()
    : `Năm ${selectedYear}`

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Báo cáo tài chính</h1>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          Phân tích chi tiết & so sánh theo kỳ
        </p>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
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
              {m === 'month' ? 'Tháng' : 'Năm'}
            </button>
          ))}
        </div>

        {/* Period navigation */}
        {mode === 'month' ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <button onClick={() => setSelectedMonth(navigateMonth(selectedMonth, -1))} className="btn btn-ghost btn-sm" style={{ padding: '4px 6px' }}>
              <ChevronLeft size={15} />
            </button>
            <span style={{ fontSize: 13, fontWeight: 600, minWidth: 110, textAlign: 'center', color: 'var(--text-primary)' }}>
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
                Hiện tại
              </button>
            )}
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <button onClick={() => setSelectedYear(y => y - 1)} className="btn btn-ghost btn-sm" style={{ padding: '4px 6px' }} disabled={selectedYear <= 2020}>
              <ChevronLeft size={15} />
            </button>
            <span style={{ fontSize: 13, fontWeight: 600, minWidth: 60, textAlign: 'center', color: 'var(--text-primary)' }}>
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
          title="Xuất báo cáo (Sắp ra mắt)"
          onClick={() => {/* TODO: implement export */}}
        >
          <Download size={14} />
          Xuất
        </button>
      </div>
    </div>
  )
}
