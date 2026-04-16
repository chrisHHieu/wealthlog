'use client'

import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useToast } from '@/components/ui/toaster'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { formatVNDCompact } from '@/lib/utils'
import { API_URL } from '@/lib/api'
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
    await fetch(`${API_URL}/api/goals/${deleteId}`, { method: 'DELETE' })
    await qc.invalidateQueries({ queryKey: ['goals'] })
    toast('Đã xóa mục tiêu')
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
              Mục tiêu tài chính
            </h1>
            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
              {activeGoals.length} mục tiêu đang theo đuổi
              {totalTarget > 0 && ` · Tổng ${formatVNDCompact(totalSaved)} / ${formatVNDCompact(totalTarget)}`}
            </p>
          </div>
          <button id="add-goal-btn" onClick={openAdd} className="btn btn-primary">
            <Plus size={15} /> Tạo mục tiêu
          </button>
        </div>

        {activeGoals.length === 0 ? (
          <div className="empty-state card" style={{ padding: 'var(--space-16) var(--space-6)' }}>
            <span style={{ fontSize: 56 }}>🎯</span>
            <p style={{ fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--text-primary)' }}>Chưa có mục tiêu nào</p>
            <p style={{ fontSize: 'var(--text-sm)' }}>Đặt ra mục tiêu tài chính để tiết kiệm có mục đích hơn</p>
            <button className="btn btn-primary" onClick={openAdd} style={{ marginTop: 'var(--space-3)' }}>
              <Plus size={15} /> Tạo mục tiêu đầu tiên
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
              🏆 Đã hoàn thành ({completedGoals.length})
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
          title="Xóa mục tiêu?"
          description="Bạn có chắc muốn xóa mục tiêu này không?"
        />
      </div>
    </PageTransition>
  )
}
