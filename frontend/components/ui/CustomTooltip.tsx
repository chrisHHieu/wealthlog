import { formatVNDCompact } from '@/lib/utils'

export function CustomTooltip({ active, payload, label }: any) {
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
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ color: p.color, marginBottom: 4 }}>
          {p.name}: <strong>{formatVNDCompact(p.value || 0)}</strong>
        </div>
      ))}
    </div>
  )
}
