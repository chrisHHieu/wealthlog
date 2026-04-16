import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { formatVNDCompact } from '@/lib/utils'
import { ChartPoint } from '@/types'
import { ReportMode } from '@/hooks/useReports'

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-tertiary)', border: '1px solid var(--surface-border)',
      borderRadius: 10, padding: '12px 16px', fontSize: 12,
    }}>
      <div style={{ color: 'var(--text-secondary)', marginBottom: 8, fontWeight: 600 }}>{label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <div style={{ width: 8, height: 8, borderRadius: 2, background: p.color, flexShrink: 0 }} />
          <span style={{ color: 'var(--text-secondary)' }}>{p.name}:</span>
          <strong style={{ color: 'var(--text-primary)' }}>{formatVNDCompact(p.value)}</strong>
        </div>
      ))}
    </div>
  )
}

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
      <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>
        Thu nhập vs Chi tiêu
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 20 }}>
        {mode === 'month' ? 'Biến động theo ngày trong tháng' : 'So sánh theo từng tháng'}
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} barGap={2} barCategoryGap="20%">
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
          <Tooltip cursor={{ fill: 'transparent' }} content={<ChartTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
            iconType="square"
            iconSize={10}
          />
          <Bar name="Thu nhập" dataKey="income" fill="var(--accent-green)" radius={[4, 4, 0, 0]} opacity={0.85} />
          <Bar name="Chi tiêu" dataKey="expense" fill="var(--accent-red)" radius={[4, 4, 0, 0]} opacity={0.85} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
