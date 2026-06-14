import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { formatVNDCompact } from '@/lib/utils'
import { TrendPoint } from '@/types'
import { ReportMode } from '@/hooks/useReports'
import { AXIS_STYLE, GRID_STYLE, CHART_COLORS, ChartTooltip } from '@/lib/chartTheme'

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
      <div className="card-title" style={{ marginBottom: 4 }}>
        Spending trend
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 20 }}>
        Cumulative expense &amp; moving average ({windowSize} {mode === 'month' ? 'days' : 'months'})
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={withMA} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="gradCum" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS.red} stopOpacity={0.22} />
              <stop offset="95%" stopColor={CHART_COLORS.red} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid {...GRID_STYLE} vertical={false} />
          <XAxis
            dataKey="label"
            tick={AXIS_STYLE}
            axisLine={false}
            tickLine={false}
            dy={6}
            interval={mode === 'month' ? 4 : 0}
          />
          <YAxis
            tick={AXIS_STYLE}
            axisLine={false}
            tickLine={false}
            tickFormatter={v => formatVNDCompact(v)}
            width={65}
          />
          <Tooltip cursor={{ stroke: 'var(--text-tertiary)', strokeWidth: 1, strokeDasharray: '4 4' }} content={<ChartTooltip />} />
          <Area
            name="Cumulative expense"
            type="monotone"
            dataKey="cumExpense"
            stroke={CHART_COLORS.red}
            strokeWidth={2.5}
            fill="url(#gradCum)"
            animationDuration={900}
            animationEasing="ease-out"
          />
          <Area
            name="Moving average"
            type="monotone"
            dataKey="movingAvg"
            stroke={CHART_COLORS.purple}
            strokeWidth={2}
            strokeDasharray="6 3"
            fill="none"
            dot={false}
            animationDuration={900}
            animationEasing="ease-out"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
