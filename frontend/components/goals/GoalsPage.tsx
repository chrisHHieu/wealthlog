'use client'

import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useToast } from '@/components/ui/toaster'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { formatVNDCompact } from '@/lib/utils'
import { apiDelete, queryKeys } from '@/lib/api'
import { useGoals } from '@/hooks/useGoals'
import { Goal } from '@/types'
import { PageTransition, StaggerItem } from '@/components/ui/PageTransition'

import { GoalCard } from './components/GoalCard'
import { CompletedGoalCard } from './components/CompletedGoalCard'
import { GoalFormDrawer } from './components/GoalFormDrawer'
import { ContributeModal } from './components/ContributeModal'

export function GoalsPage() {
  const { toast } = useToast()
  const qc = useQueryClient()

  const [showForm, setShowForm] = useState(false)
  const [editGoal, setEditGoal] = useState<Goal | null>(null)
  const [showContribute, setShowContribute] = useState<Goal | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const { data: goals = [] } = useGoals()
  const activeGoals = goals.filter(g => !g.isCompleted)
  const completedGoals = goals.filter(g => g.isCompleted)
  const totalTarget = activeGoals.reduce((s, g) => s + g.targetAmount, 0)
  const totalSaved = activeGoals.reduce((s, g) => s + g.currentAmount, 0)

  function openAdd() {
    setEditGoal(null)
    setShowForm(true)
  }

  function openEdit(g: Goal) {
    setEditGoal(g)
    setShowForm(true)
  }

  async function handleDelete() {
    if (!deleteId) return
    await apiDelete(`/api/goals/${deleteId}`)
    await qc.invalidateQueries({ queryKey: queryKeys.goals })
    toast('Goal deleted')
  }

  return (
    <PageTransition>
      <div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 'var(--space-6)',
        }}>
          <div>
            <h1 style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, marginBottom: 'var(--space-1)' }}>
              Financial goals
            </h1>
            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
              {activeGoals.length} active goals
              {totalTarget > 0 && ` · Total ${formatVNDCompact(totalSaved)} / ${formatVNDCompact(totalTarget)}`}
            </p>
          </div>
          <button id="add-goal-btn" onClick={openAdd} className="btn btn-primary">
            <Plus size={15} /> Create goal
          </button>
        </div>

        {activeGoals.length === 0 ? (
          <div className="empty-state card" style={{ padding: 'var(--space-16) var(--space-6)' }}>
            <span style={{ fontSize: 56 }}>🎯</span>
            <p style={{ fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--text-primary)' }}>No goals yet</p>
            <p style={{ fontSize: 'var(--text-sm)' }}>Create financial goals to save with purpose</p>
            <button className="btn btn-primary" onClick={openAdd} style={{ marginTop: 'var(--space-3)' }}>
              <Plus size={15} /> Create your first goal
            </button>
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
            gap: 'var(--space-4)',
          }}>
            {activeGoals.map((goal, i) => (
              <StaggerItem key={goal.id}>
                <GoalCard
                  goal={goal}
                  index={i}
                  onContribute={setShowContribute}
                  onEdit={openEdit}
                  onDelete={setDeleteId}
                />
              </StaggerItem>
            ))}
          </div>
        )}

        {completedGoals.length > 0 && (
          <div style={{ marginTop: 'var(--space-8)' }}>
            <div style={{
              fontSize: 'var(--text-xs)',
              fontWeight: 700,
              color: 'var(--text-tertiary)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              marginBottom: 'var(--space-3)',
            }}>
              🏆 Completed ({completedGoals.length})
            </div>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
              gap: 'var(--space-3)',
            }}>
              {completedGoals.map(goal => (
                <CompletedGoalCard key={goal.id} goal={goal} />
              ))}
            </div>
          </div>
        )}

        <GoalFormDrawer
          isOpen={showForm}
          onClose={() => setShowForm(false)}
          initialData={editGoal}
        />

        <ContributeModal
          goal={showContribute}
          onClose={() => setShowContribute(null)}
        />

        <ConfirmModal
          isOpen={!!deleteId}
          onClose={() => setDeleteId(null)}
          onConfirm={handleDelete}
          title="Delete goal?"
          description="Are you sure you want to delete this goal?"
        />
      </div>
    </PageTransition>
  )
}
