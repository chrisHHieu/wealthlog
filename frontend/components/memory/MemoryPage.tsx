'use client'

import { useState } from 'react'
import { Brain, Trash2, CheckCircle, Tag, Shield, Filter } from 'lucide-react'
import { useToast } from '@/components/ui/toaster'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { PageTransition, StaggerItem } from '@/components/ui/PageTransition'
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
  commitment:  'var(--accent-red, #ef4444)',
  emotion:     'var(--accent-pink, #d946ef)',
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
            background: i < value ? 'var(--accent-green)' : 'var(--border)',
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
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-6)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <Brain size={24} color="var(--accent-purple)" />
            <div>
              <h1 style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, margin: 0 }}>
                AI Memory
              </h1>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', margin: 0 }}>
                What the assistant remembers about you
              </p>
            </div>
          </div>

          {/* Stats */}
          <div style={{ display: 'flex', gap: 'var(--space-4)', textAlign: 'right' }}>
            <div>
              <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, color: 'var(--accent-green)' }}>
                {totalCount}
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>Total facts</div>
            </div>
            <div>
              <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, color: 'var(--accent-blue)' }}>
                {verifiedCount}
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>Confirmed</div>
            </div>
          </div>
        </div>

        {/* Category filter */}
        <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', marginBottom: 'var(--space-5)' }}>
          <Filter size={14} color="var(--text-secondary)" style={{ marginTop: 6 }} />
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setFilterCat(cat)}
              style={{
                padding: '4px 12px',
                borderRadius: 20,
                border: `1px solid ${filterCat === cat ? CATEGORY_COLORS[cat] ?? 'var(--accent-blue)' : 'var(--border)'}`,
                background: filterCat === cat ? `${CATEGORY_COLORS[cat] ?? 'var(--accent-blue)'}18` : 'transparent',
                color: filterCat === cat ? CATEGORY_COLORS[cat] ?? 'var(--accent-blue)' : 'var(--text-secondary)',
                fontSize: 'var(--text-sm)',
                cursor: 'pointer',
                fontWeight: filterCat === cat ? 600 : 400,
                transition: 'all 0.15s',
              }}
            >
              {cat === ALL ? 'All' : CATEGORY_LABELS[cat] ?? cat}
            </button>
          ))}
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
            border: '1px dashed var(--border)',
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
                    border: `1px solid ${fact.verifiedByUser ? 'var(--accent-green)33' : 'var(--border)'}`,
                    borderLeft: `3px solid ${CATEGORY_COLORS[fact.category] ?? 'var(--border)'}`,
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
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted, var(--text-secondary))', marginTop: 2 }}>
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
                              background: 'var(--surface-2, var(--bg-card))',
                              border: '1px solid var(--border)',
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
                          border: '1px solid var(--border)',
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
                        border: '1px solid var(--border)',
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
