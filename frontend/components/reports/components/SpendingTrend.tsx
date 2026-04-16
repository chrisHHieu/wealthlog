import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { formatVNDCompact } from '@/lib/utils'
import { TrendPoint } from '@/types'
import { ReportMode } from '@/hooks/useReports'

function TrendTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-tertiary)', border: '1px solid var(--surface-border)',
      borderRadius: 10, padding: '12px 16px', fontSize: 12,
    }}>
      <div style={{ color: 'var(--text-secondary)', marginBottom: 8, fontWeight: 600 }}>{label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: p.color, flexShrink: 0 }} />
          <span style={{ color: 'var(--text-secondary)' }}>{p.name}:</span>
          <strong style={{ color: 'var(--text-primary)' }}>{formatVNDCompact(p.value)}</strong>
        </div>
      ))}
    </div>
  )
}

interface SpendingTrendProps {
  data: TrendPoint[]
  mode: ReportMode
  isLoading: boolean
}

export function SpendingTrend({ data, mode, isLoading }: SpendingTrendProps) {
  if (isLoading) {
    return (
      <div className="card" style={{ padding: 20 }}>
        <div className="skeleton" style={{ height: 18, width: 160, marginBottom: 8 }} />
        <div className="skeleton" style={{ height: 12, width: 120, marginBottom: 20 }} />
        <div className="skeleton" style={{ height: 260, borderRadius: 8 }} />
      </div>
    )
  }

  // Calculate moving average (5-point for month, 3-point for year)
  const windowSize = mode === 'month' ? 5 : 3
  const withMA = data.map((d, i) => {
    const start = Math.max(0, i - windowSize + 1)
    const window = data.slice(start, i + 1)
    const avg = window.reduce((s, p) => s + p.expense, 0) / window.length
    return { ...d, movingAvg: Math.round(avg) }
  })

  return (
    <div className="card" style={{ padding: 20 }}>
      <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>
        Xu hướng chi tiêu
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 20 }}>
        Chi tiêu lũy kế & trung bình trượt ({windowSize} {mode === 'month' ? 'ngày' : 'tháng'})
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={withMA}>
          <defs>
            <linearGradient id="gradCum" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--accent-red)" stopOpacity={0.15} />
              <stop offset="95%" stopColor="var(--accent-red)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--surface-border)" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
            axisLine={false}
            tickLine={false}
            interval={mode === 'month' ? 4 : 0}
          />
          <YAxis
            tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={v => formatVNDCompact(v)}
            width={65}
          />
          <Tooltip cursor={{ fill: 'transparent' }} content={<TrendTooltip />} />
          <Area
            name="Chi tiêu lũy kế"
            type="monotone"
            dataKey="cumExpense"
            stroke="var(--accent-red)"
            strokeWidth={2}
            fill="url(#gradCum)"
          />
          <Area
            name="Trung bình trượt"
            type="monotone"
            dataKey="movingAvg"
            stroke="var(--accent-purple)"
            strokeWidth={2}
            strokeDasharray="6 3"
            fill="none"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
