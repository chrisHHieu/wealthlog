import { formatVNDCompact } from '@/lib/utils'
import { ChartTooltipProps } from '@/types/chart'

export function CustomTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-tertiary)',
      border: '1px solid var(--surface-border)',
      borderRadius: 10,
      padding: '12px 16px',
      fontSize: 12,
    }}>
      <div style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ color: p.color, marginBottom: 4 }}>
          {p.name}: <strong>{formatVNDCompact(Number(p.value ?? 0))}</strong>
        </div>
      ))}
    </div>
  )
}
