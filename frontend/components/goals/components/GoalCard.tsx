import { Edit2, Trash2, PiggyBank, Clock, TrendingUp } from 'lucide-react'
import { CircularProgress } from '@/components/ui/CircularProgress'
import { formatVNDCompact, getDaysRemaining, calcMonthlySavingsNeeded } from '@/lib/utils'
import { Goal } from '@/types'

interface GoalCardProps {
  goal: Goal
  onContribute: (g: Goal) => void
  onEdit: (g: Goal) => void
  onDelete: (id: string) => void
}

export function GoalCard({ goal, onContribute, onEdit, onDelete }: GoalCardProps) {
  const pct = Math.min(100, (goal.currentAmount / goal.targetAmount) * 100)
  const daysLeft = goal.deadline ? getDaysRemaining(goal.deadline) : null
  const monthlyNeeded = goal.deadline
    ? calcMonthlySavingsNeeded(goal.targetAmount, goal.currentAmount, goal.deadline)
    : null

  return (
    <div
      className="card card-interactive"
      style={{ padding: '20px', cursor: 'pointer' }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
        <CircularProgress pct={pct} color={goal.color} icon={goal.icon} size={80} />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="card-title" style={{ marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {goal.name}
          </div>
          <div className="num-meta" style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
            {formatVNDCompact(goal.currentAmount)} / {formatVNDCompact(goal.targetAmount)}
          </div>

          {daysLeft !== null && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: daysLeft < 30 ? 'var(--accent-red)' : 'var(--text-tertiary)', marginBottom: 4 }}>
              <Clock size={12} /> {daysLeft} days left
            </div>
          )}

          {monthlyNeeded && monthlyNeeded > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--text-tertiary)' }}>
              <TrendingUp size={12} /> Save {formatVNDCompact(monthlyNeeded)}/month
            </div>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button
          className="btn btn-primary btn-sm"
          style={{ flex: 2, fontSize: 12 }}
          onClick={() => onContribute(goal)}
        >
          <PiggyBank size={13} /> Add money
        </button>
        <button
          className="btn btn-secondary btn-sm"
          style={{ flex: 'none', width: 32, height: 32, padding: 0 }}
          onClick={() => onEdit(goal)}
        >
          <Edit2 size={13} />
        </button>
        <button
          className="btn btn-ghost btn-sm"
          style={{ flex: 'none', width: 32, height: 32, padding: 0, color: 'var(--accent-red)' }}
          onClick={() => onDelete(goal.id)}
        >
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  )
}
