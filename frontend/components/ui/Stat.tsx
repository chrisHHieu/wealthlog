import { cn } from '@/lib/utils'

interface StatProps {
  label: string
  value: React.ReactNode
  /** Value text color, defaults to text-primary */
  color?: string
  size?: 'md' | 'lg'
  /** Optional trailing element next to the value, e.g. a TrendBadge */
  badge?: React.ReactNode
  className?: string
}

export function Stat({ label, value, color, size = 'md', badge, className }: StatProps) {
  return (
    <div className={cn('stat', className)}>
      <span className="stat-label">{label}</span>
      <span
        className={cn('stat-value', size === 'lg' && 'stat-value-lg')}
        style={color ? { color } : undefined}
      >
        {value}
        {badge && <span style={{ marginLeft: 'var(--space-2)', verticalAlign: 'middle' }}>{badge}</span>}
      </span>
    </div>
  )
}
