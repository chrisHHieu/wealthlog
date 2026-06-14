import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { formatVNDCompact } from '@/lib/utils'
import { ChartPoint } from '@/types'
import { ReportMode } from '@/hooks/useReports'
import { AXIS_STYLE, GRID_STYLE, ChartTooltip, GradientDefs } from '@/lib/chartTheme'

interface IncomeExpenseChartProps {
  data: ChartPoint[]
  mode: ReportMode
  isLoading: boolean
}

export function IncomeExpenseChart({ data, mode, isLoading }: IncomeExpenseChartProps) {
  if (isLoading) {
    return (
      <div className="card" style={{ padding: 20 }}>
        <div className="skeleton" style={{ height: 18, width: 180, marginBottom: 8 }} />
        <div className="skeleton" style={{ height: 12, width: 120, marginBottom: 20 }} />
        <div className="skeleton" style={{ height: 260, borderRadius: 8 }} />
      </div>
    )
  }

  return (
    <div className="card" style={{ padding: 20 }}>
      <div className="card-title" style={{ marginBottom: 4 }}>
        Income vs Expense
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 20 }}>
        {mode === 'month' ? 'Daily movement within the month' : 'Monthly comparison'}
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} barGap={2} barCategoryGap="20%" margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs><GradientDefs /></defs>
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
          <Tooltip cursor={{ fill: 'var(--surface)', radius: 8 }} content={<ChartTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 12, paddingTop: 12, color: 'var(--text-secondary)' }}
            iconType="circle"
            iconSize={8}
          />
          <Bar name="Income" dataKey="income" fill="url(#gradientGreen)" radius={[6, 6, 0, 0]} maxBarSize={36} animationDuration={800} animationEasing="ease-out" />
          <Bar name="Expense" dataKey="expense" fill="url(#gradientRed)" radius={[6, 6, 0, 0]} maxBarSize={36} animationDuration={800} animationEasing="ease-out" animationBegin={150} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
