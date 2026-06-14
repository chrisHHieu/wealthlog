'use client'

import { useState } from 'react'
import { Plus, Target, Trophy } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useToast } from '@/components/ui/toaster'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { formatVNDCompact } from '@/lib/utils'
import { apiDelete, queryKeys } from '@/lib/api'
import { useGoals } from '@/hooks/useGoals'
import { Goal } from '@/types'
import { PageTransition, StaggerItem } from '@/components/ui/PageTransition'
import { PageHeader } from '@/components/ui/PageHeader'

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
        <PageHeader
          eyebrow="Targets"
          title="Goals"
          subtitle={
            <>
              {activeGoals.length} active {activeGoals.length === 1 ? 'goal' : 'goals'}
              {totalTarget > 0 && ` · Total ${formatVNDCompact(totalSaved)} / ${formatVNDCompact(totalTarget)}`}
            </>
          }
          actions={
            <button id="add-goal-btn" onClick={openAdd} className="btn btn-primary">
              <Plus size={15} /> Create goal
            </button>
          }
        />

        {activeGoals.length === 0 ? (
          <div className="empty-state card" style={{ padding: 'var(--space-16) var(--space-6)' }}>
            <div className="icon-tile" style={{ width: 56, height: 56 }}>
              <Target size={26} />
            </div>
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
            {activeGoals.map((goal) => (
              <StaggerItem key={goal.id}>
                <GoalCard
                  goal={goal}
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
            <div className="stat-label" style={{ marginBottom: 'var(--space-3)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Trophy size={12} /> Completed ({completedGoals.length})
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
