'use client'

import { useState } from 'react'
import { Stat } from '@/components/ui/Stat'
import { Brain, Trash2, CheckCircle, Tag, Shield, Filter } from 'lucide-react'
import { useToast } from '@/components/ui/toaster'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { PageTransition, StaggerItem } from '@/components/ui/PageTransition'
import { PageHeader } from '@/components/ui/PageHeader'
import { useMemoryFacts, useDeleteFact, useVerifyFact, UserFact } from '@/hooks/useMemoryFacts'

const CATEGORY_LABELS: Record<string, string> = {
  preference:  'Preferences',
  habit:       'Habits',
  goal:        'Goals',
  context:     'Context',
  pattern:     'Patterns',
  commitment:  'Commitments',
  emotion:     'Emotions',
  general:     'General',
}

const CATEGORY_COLORS: Record<string, string> = {
  preference:  'var(--accent-blue)',
  habit:       'var(--accent-purple)',
  goal:        'var(--accent-green)',
  context:     'var(--accent-gold)',
  pattern:     'var(--accent-amber)',
  commitment:  'var(--accent-red)',
  emotion:     'var(--accent-purple-light)',
  general:     'var(--text-secondary)',
}

const ALL = 'all'

function ImportanceDots({ value }: { value: number }) {
  return (
    <span style={{ display: 'flex', gap: 2, alignItems: 'center' }}>
      {Array.from({ length: 10 }).map((_, i) => (
        <span
          key={i}
          style={{
            width: 5,
            height: 5,
            borderRadius: '50%',
            background: i < value ? 'var(--accent-green)' : 'var(--surface-border)',
          }}
        />
      ))}
    </span>
  )
}

export function MemoryPage() {
  const { toast } = useToast()
  const { data: facts = [], isLoading } = useMemoryFacts()
  const deleteMutation = useDeleteFact()
  const verifyMutation = useVerifyFact()

  const [filterCat, setFilterCat] = useState(ALL)
  const [deleteTarget, setDeleteTarget] = useState<UserFact | null>(null)

  const categories = [ALL, ...Array.from(new Set(facts.map(f => f.category)))]
  const filtered = filterCat === ALL ? facts : facts.filter(f => f.category === filterCat)

  const verifiedCount = facts.filter(f => f.verifiedByUser).length
  const totalCount = facts.length

  async function handleDelete() {
    if (!deleteTarget) return
    await deleteMutation.mutateAsync(deleteTarget.id)
    toast('Fact deleted')
    setDeleteTarget(null)
  }

  async function handleVerify(fact: UserFact) {
    await verifyMutation.mutateAsync(fact)
    toast('Fact confirmed')
  }

  return (
    <PageTransition>
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        {/* Header */}
        <PageHeader
          eyebrow="Assistant"
          title="AI Memory"
          subtitle="What the assistant remembers about you"
          actions={
            <div className="stat-strip" style={{ gap: 'var(--space-4)' }}>
              <Stat label="Total facts" value={totalCount} />
              <Stat label="Confirmed" value={verifiedCount} color="var(--accent-green)" />
            </div>
          }
        />

        {/* Category filter */}
        <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', marginBottom: 'var(--space-5)' }}>
          <Filter size={14} color="var(--text-secondary)" style={{ marginTop: 6 }} />
          {categories.map(cat => {
            const active = filterCat === cat
            const color = CATEGORY_COLORS[cat] ?? 'var(--accent-blue)'
            return (
              <button
                key={cat}
                onClick={() => setFilterCat(cat)}
                className={`chip-toggle${active ? ' active' : ''}`}
                style={active ? {
                  borderColor: color,
                  background: `color-mix(in srgb, ${color} 10%, transparent)`,
                  color,
                } : undefined}
              >
                {cat === ALL ? 'All' : CATEGORY_LABELS[cat] ?? cat}
              </button>
            )
          })}
        </div>

        {/* Facts list */}
        {isLoading ? (
          <div style={{ color: 'var(--text-secondary)', padding: 'var(--space-8)', textAlign: 'center' }}>
            Loading...
          </div>
        ) : filtered.length === 0 ? (
          <div style={{
            color: 'var(--text-secondary)',
            padding: 'var(--space-12)',
            textAlign: 'center',
            border: '1px dashed var(--surface-border)',
            borderRadius: 'var(--radius-lg)',
          }}>
            <Brain size={32} style={{ opacity: 0.3, marginBottom: 8 }} />
            <div>No facts yet. Chat with AI to get started.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {filtered.map((fact) => (
              <StaggerItem key={fact.id}>
                <div
                  style={{
                    background: 'var(--surface)',
                    border: `1px solid ${fact.verifiedByUser ? 'color-mix(in srgb, var(--accent-green) 20%, transparent)' : 'var(--surface-border)'}`,
                    borderLeft: `3px solid ${CATEGORY_COLORS[fact.category] ?? 'var(--surface-border)'}`,
                    borderRadius: 'var(--radius-md)',
                    padding: 'var(--space-4)',
                    display: 'flex',
                    gap: 'var(--space-3)',
                    alignItems: 'flex-start',
                  }}
                >
                  {/* Left: importance + category */}
                  <div style={{ minWidth: 90, flexShrink: 0 }}>
                    <div style={{
                      fontSize: 'var(--text-xs)',
                      fontWeight: 600,
                      color: CATEGORY_COLORS[fact.category] ?? 'var(--text-secondary)',
                      marginBottom: 4,
                    }}>
                      {CATEGORY_LABELS[fact.category] ?? fact.category}
                    </div>
                    <ImportanceDots value={fact.importance} />
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginTop: 2 }}>
                      {fact.importance}/10
                    </div>
                  </div>

                  {/* Middle: fact text + topics */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 'var(--text-sm)',
                      lineHeight: 1.5,
                      color: 'var(--text-primary)',
                      marginBottom: fact.topics.length ? 6 : 0,
                    }}>
                      {fact.verifiedByUser && (
                        <Shield
                          size={12}
                          color="var(--accent-green)"
                          style={{ marginRight: 4, display: 'inline', verticalAlign: 'middle' }}
                        />
                      )}
                      {fact.fact}
                    </div>

                    {fact.topics.length > 0 && (
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
                        <Tag size={10} color="var(--text-secondary)" />
                        {fact.topics.map(t => (
                          <span
                            key={t}
                            style={{
                              fontSize: 11,
                              padding: '1px 7px',
                              borderRadius: 10,
                              background: 'var(--surface)',
                              border: '1px solid var(--surface-border)',
                              color: 'var(--text-secondary)',
                            }}
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Right: actions */}
                  <div style={{ display: 'flex', gap: 'var(--space-2)', flexShrink: 0 }}>
                    {!fact.verifiedByUser && (
                      <button
                        onClick={() => handleVerify(fact)}
                        title="Confirm this fact"
                        style={{
                          padding: 6,
                          background: 'transparent',
                          border: '1px solid var(--surface-border)',
                          borderRadius: 'var(--radius-sm)',
                          cursor: 'pointer',
                          color: 'var(--accent-green)',
                          display: 'flex',
                          alignItems: 'center',
                        }}
                      >
                        <CheckCircle size={14} />
                      </button>
                    )}
                    <button
                      onClick={() => setDeleteTarget(fact)}
                      title="Delete this fact"
                      style={{
                        padding: 6,
                        background: 'transparent',
                        border: '1px solid var(--surface-border)',
                        borderRadius: 'var(--radius-sm)',
                        cursor: 'pointer',
                        color: 'var(--text-secondary)',
                        display: 'flex',
                        alignItems: 'center',
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </StaggerItem>
            ))}
          </div>
        )}
      </div>

      <ConfirmModal
        isOpen={!!deleteTarget}
        title="Delete this fact?"
        description={deleteTarget?.fact ?? ''}
        onConfirm={handleDelete}
        onClose={() => setDeleteTarget(null)}
      />
    </PageTransition>
  )
}
