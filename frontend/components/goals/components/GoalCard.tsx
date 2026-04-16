import { motion } from 'framer-motion'
import { Edit2, Trash2, PiggyBank } from 'lucide-react'
import { CircularProgress } from '@/components/ui/CircularProgress'
import { formatVNDCompact, getDaysRemaining, calcMonthlySavingsNeeded } from '@/lib/utils'
import { Goal } from '@/types'

interface GoalCardProps {
  goal: Goal
  index: number
  onContribute: (g: Goal) => void
  onEdit: (g: Goal) => void
  onDelete: (id: string) => void
}

export function GoalCard({ goal, index, onContribute, onEdit, onDelete }: GoalCardProps) {
  const pct = Math.min(100, (goal.currentAmount / goal.targetAmount) * 100)
  const daysLeft = goal.deadline ? getDaysRemaining(goal.deadline) : null
  const monthlyNeeded = goal.deadline
    ? calcMonthlySavingsNeeded(goal.targetAmount, goal.currentAmount, goal.deadline)
    : null

  return (
    <motion.div
      className="card"
      style={{ padding: '20px', cursor: 'pointer' }}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      whileHover={{ scale: 1.01, boxShadow: `0 4px 32px ${goal.color}25, var(--shadow-card)` }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
        <CircularProgress pct={pct} color={goal.color} icon={goal.icon} size={80} />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {goal.name}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
            {formatVNDCompact(goal.currentAmount)} / {formatVNDCompact(goal.targetAmount)}
          </div>

          {daysLeft !== null && (
            <div style={{ fontSize: 11, color: daysLeft < 30 ? 'var(--accent-red)' : 'var(--text-tertiary)', marginBottom: 4 }}>
              ⏰ Còn {daysLeft} ngày
            </div>
          )}

          {monthlyNeeded && monthlyNeeded > 0 && (
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
              Cần tiết kiệm {formatVNDCompact(monthlyNeeded)}/tháng
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
          <PiggyBank size={13} /> Thêm tiền
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
    </motion.div>
  )
}
