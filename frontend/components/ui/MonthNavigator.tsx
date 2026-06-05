import { ChevronLeft, ChevronRight } from 'lucide-react'

function getCurrentMonthStr() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function navigateMonth(yyyymm: string, delta: number): string {
  const [y, m] = yyyymm.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

export function MonthNavigator({ value, onChange }: { value: string; onChange: (m: string) => void }) {
  const [year, month] = value.split('-').map(Number)
  const isCurrentMonth = value === getCurrentMonthStr()

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <button
        onClick={() => onChange(navigateMonth(value, -1))}
        className="btn btn-ghost btn-sm"
        style={{ padding: '4px 6px', borderRadius: 8 }}
      >
        <ChevronLeft size={15} />
      </button>
      <span style={{
        fontSize: 13, fontWeight: 600,
        minWidth: 110, textAlign: 'center',
        color: 'var(--text-primary)',
      }}>
        Month {month}, {year}
      </span>
      <button
        onClick={() => value >= getCurrentMonthStr() ? null : onChange(navigateMonth(value, 1))}
        className="btn btn-ghost btn-sm"
        style={{ padding: '4px 6px', borderRadius: 8, opacity: value >= getCurrentMonthStr() ? 0.3 : 1 }}
        disabled={value >= getCurrentMonthStr()}
      >
        <ChevronRight size={15} />
      </button>
      {!isCurrentMonth && (
        <button
          onClick={() => onChange(getCurrentMonthStr())}
          className="btn btn-ghost btn-sm"
          style={{ fontSize: 11, padding: '3px 8px', marginLeft: 4, color: 'var(--accent-green)', borderColor: 'var(--accent-green)' }}
        >
          Current
        </button>
      )}
    </div>
  )
}
