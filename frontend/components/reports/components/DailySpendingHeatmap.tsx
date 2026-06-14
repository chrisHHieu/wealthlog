import { formatVNDCompact } from '@/lib/utils'
import { TrendPoint } from '@/types'

interface DailySpendingHeatmapProps {
  month: string // yyyy-MM
  trendData: TrendPoint[]
  isLoading: boolean
}

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

/** Intensity step for a day's spending relative to the month's max (0–4). */
function intensity(expense: number, max: number): number {
  if (expense <= 0 || max <= 0) return 0
  const ratio = expense / max
  if (ratio <= 0.25) return 1
  if (ratio <= 0.5) return 2
  if (ratio <= 0.75) return 3
  return 4
}

const CELL_BG = [
  'var(--surface)',
  'color-mix(in srgb, var(--accent-red) 15%, transparent)',
  'color-mix(in srgb, var(--accent-red) 35%, transparent)',
  'color-mix(in srgb, var(--accent-red) 60%, transparent)',
  'var(--accent-red)',
]

export function DailySpendingHeatmap({ month, trendData, isLoading }: DailySpendingHeatmapProps) {
  if (isLoading) {
    return (
      <div className="card" style={{ padding: 20 }}>
        <div className="skeleton" style={{ height: 18, width: 180, marginBottom: 14 }} />
        <div className="skeleton" style={{ height: 200, borderRadius: 8 }} />
      </div>
    )
  }

  const [year, monthNum] = month.split('-').map(Number)
  const expenseByDay = new Map(trendData.map(p => [Number(p.label), p.expense]))
  const daysInMonth = new Date(year, monthNum, 0).getDate()
  // Monday-first column index of day 1
  const firstWeekday = (new Date(year, monthNum - 1, 1).getDay() + 6) % 7
  const maxExpense = Math.max(0, ...trendData.map(p => p.expense))

  const cells: Array<{ day: number; expense: number } | null> = [
    ...Array.from({ length: firstWeekday }, () => null),
    ...Array.from({ length: daysInMonth }, (_, i) => ({
      day: i + 1,
      expense: expenseByDay.get(i + 1) ?? 0,
    })),
  ]

  return (
    <section className="card" style={{ padding: 20, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="card-title">Daily spending</div>
      <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 2, marginBottom: 14 }}>
        Darker days cost more
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4, marginBottom: 4 }}>
        {WEEKDAYS.map(d => (
          <div key={d} style={{ fontSize: 10, color: 'var(--text-tertiary)', textAlign: 'center', fontWeight: 600 }}>
            {d}
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4 }}>
        {cells.map((cell, i) => {
          if (!cell) return <div key={`pad-${i}`} />
          const level = intensity(cell.expense, maxExpense)
          return (
            <div
              key={cell.day}
              title={`Day ${cell.day}: ${cell.expense > 0 ? formatVNDCompact(cell.expense) : 'no spending'}`}
              style={{
                aspectRatio: '1.4',
                borderRadius: 6,
                background: CELL_BG[level],
                border: '1px solid var(--surface-border)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 11,
                fontWeight: 600,
                color: level >= 3 ? '#fff' : 'var(--text-secondary)',
                cursor: 'default',
              }}
            >
              {cell.day}
            </div>
          )
        })}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 'auto', paddingTop: 14, fontSize: 10, color: 'var(--text-tertiary)' }}>
        <span style={{ marginRight: 2 }}>Less</span>
        {CELL_BG.map((bg, i) => (
          <span key={i} style={{ width: 14, height: 10, borderRadius: 3, background: bg, border: '1px solid var(--surface-border)' }} />
        ))}
        <span style={{ marginLeft: 2 }}>More</span>
      </div>
    </section>
  )
}
