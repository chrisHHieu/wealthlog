import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { formatVNDCompact, formatVND } from '@/lib/utils'
import { DashboardData } from '@/types'
import { Select } from '@/components/ui/Select'
import { CHART_COLORS, AXIS_STYLE, GRID_STYLE } from '@/lib/chartTheme'
import { ChartTooltipProps } from '@/types/chart'

type Period = '6months' | '12months'

const PERIOD_OPTIONS = [
  { value: '6months', label: 'Last 6 months' },
  { value: '12months', label: 'Last 12 months' },
]

function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip">
      <div style={{ color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 'var(--space-2)', fontSize: 'var(--text-sm)' }}>
        {label}
      </div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 3 }}>
          <div style={{
            width: 8,
            height: 8,
            borderRadius: 'var(--radius-xs)',
            background: p.color,
            flexShrink: 0,
          }} />
          <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>{p.name}:</span>
          <strong style={{ color: 'var(--text-primary)', fontSize: 'var(--text-sm)' }}>{formatVND(Number(p.value ?? 0))}</strong>
        </div>
      ))}
    </div>
  )
}

interface CashFlowChartProps {
  data?: DashboardData
  isLoading: boolean
}

export function CashFlowChart({ data, isLoading }: CashFlowChartProps) {
  const [period, setPeriod] = useState<Period>('6months')

  const allData = data?.monthlyChart.map(m => {
    const [, month] = m.month.split('-')
    return { name: `${Number(month)}`, 'Income': m.income, 'Expense': m.expense }
  }) ?? []

  const chartData = period === '6months' ? allData.slice(-6) : allData

  return (
    <div className="card" style={{ padding: 'var(--space-6)', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 'var(--text-lg)', color: 'var(--text-primary)' }}>
            Income - Expense trend
          </div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)', marginTop: 2 }}>
            Your monthly cash flow
          </div>
        </div>

        <Select
          value={period}
          onChange={(val) => setPeriod(val as Period)}
          options={PERIOD_OPTIONS}
          minWidth={140}
        />
      </div>

      {isLoading ? (
        <div className="skeleton" style={{ flex: 1, borderRadius: 'var(--radius-md)', minHeight: 280 }} />
      ) : chartData.length === 0 ? (
        <div className="empty-state" style={{ flex: 1 }}>
          <span style={{ fontSize: 32 }}>📊</span>
          <span style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-2)' }}>Not enough data yet</span>
        </div>
      ) : (
        <div style={{ flex: 1, minHeight: 0 }}>
          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={200}>
            <BarChart data={chartData} barGap={4} barCategoryGap="20%" margin={{ top: 10, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="barGradientGreen" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={CHART_COLORS.green} stopOpacity={1} />
                  <stop offset="100%" stopColor={CHART_COLORS.green} stopOpacity={0.6} />
                </linearGradient>
                <linearGradient id="barGradientRed" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={CHART_COLORS.red} stopOpacity={0.9} />
                  <stop offset="100%" stopColor={CHART_COLORS.red} stopOpacity={0.4} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} {...GRID_STYLE} />
              <XAxis
                dataKey="name"
                tick={{ ...AXIS_STYLE, fontWeight: 500 }}
                axisLine={{ stroke: 'var(--surface-border)' }}
                tickLine={false}
                dy={8}
              />
              <YAxis
                width={56}
                tick={AXIS_STYLE}
                tickFormatter={formatVNDCompact}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip cursor={{ fill: 'var(--surface)', radius: 8 }} content={<ChartTooltip />} />
              <Bar
                dataKey="Income"
                fill="url(#barGradientGreen)"
                radius={[6, 6, 0, 0]}
                maxBarSize={32}
                animationDuration={800}
                animationEasing="ease-out"
              />
              <Bar
                dataKey="Expense"
                fill="url(#barGradientRed)"
                radius={[6, 6, 0, 0]}
                maxBarSize={32}
                animationDuration={800}
                animationEasing="ease-out"
                animationBegin={200}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
