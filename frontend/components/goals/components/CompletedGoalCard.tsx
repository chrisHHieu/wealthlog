import { formatVND } from '@/lib/utils'
import { Goal } from '@/types'

export function CompletedGoalCard({ goal }: { goal: Goal }) {
  return (
    <div className="card" style={{ padding: '16px 20px', opacity: 0.7 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ fontSize: 24 }}>{goal.icon}</div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>✅ {goal.name}</div>
          <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{formatVND(goal.targetAmount)}</div>
        </div>
      </div>
    </div>
  )
}
