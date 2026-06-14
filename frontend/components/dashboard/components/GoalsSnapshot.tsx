import { motion } from 'framer-motion'
import { Plus, Target } from 'lucide-react'
import Link from 'next/link'
import { formatVNDCompact } from '@/lib/utils'
import { Goal } from '@/types'

interface GoalsSnapshotProps {
  goals: Goal[]
  isLoading?: boolean
}

export function GoalsSnapshot({ goals, isLoading }: GoalsSnapshotProps) {
  return (
    <div className="card" style={{ padding: 'var(--space-5)', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
        <div className="card-title">Financial goals</div>
        <Link href="/goals" className="btn btn-ghost btn-sm" style={{ padding: 'var(--space-1)' }}>
          <Plus size={16} />
        </Link>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: 52, borderRadius: 'var(--radius-sm)' }} />)}
        </div>
      ) : goals.length === 0 ? (
        <div className="empty-state" style={{ flex: 1, padding: 'var(--space-6) var(--space-3)' }}>
          <div className="icon-tile" style={{ width: 48, height: 48 }}>
            <Target size={22} />
          </div>
          <span style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-1)', color: 'var(--text-tertiary)' }}>No goals yet</span>
          <Link href="/goals" className="btn btn-primary btn-sm" style={{ marginTop: 'var(--space-2)' }}>
            Create your first goal
          </Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', flex: 1 }}>
          {goals.slice(0, 3).map((goal, i) => {
            const pct = Math.min(100, (goal.currentAmount / goal.targetAmount) * 100)
            return (
              <div key={goal.id}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-1-5)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flex: 1, minWidth: 0 }}>
                    <span style={{ fontSize: 14 }}>{goal.icon}</span>
                    <span style={{
                      fontSize: 'var(--text-sm)',
                      fontWeight: 600,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {goal.name}
                    </span>
                  </div>
                  <span className="num-meta" style={{
                    fontSize: 'var(--text-sm)',
                    fontWeight: 700,
                    color: goal.color,
                    flexShrink: 0,
                    marginLeft: 'var(--space-2)',
                  }}>
                    {pct.toFixed(0)}%
                  </span>
                </div>
                <div className="num-meta" style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginBottom: 'var(--space-1-5)' }}>
                  {formatVNDCompact(goal.currentAmount)} / {formatVNDCompact(goal.targetAmount)}
                </div>
                <div className="progress-bar">
                  <motion.div
                    className="progress-bar-fill"
                    style={{ background: goal.color }}
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.8, delay: i * 0.1, ease: [0.25, 0.46, 0.45, 0.94] }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
