import { CheckCircle2 } from 'lucide-react'
import { formatVND } from '@/lib/utils'
import { Goal } from '@/types'

export function CompletedGoalCard({ goal }: { goal: Goal }) {
  return (
    <div className="card" style={{ padding: '16px 20px', opacity: 0.75 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ fontSize: 24 }}>{goal.icon}</div>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600 }}>
            <CheckCircle2 size={14} color="var(--accent-green)" />
            {goal.name}
          </div>
          <div className="num-meta" style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{formatVND(goal.targetAmount)}</div>
        </div>
      </div>
    </div>
  )
}
