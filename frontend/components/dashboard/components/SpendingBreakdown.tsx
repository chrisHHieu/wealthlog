import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { motion } from 'framer-motion'
import { ChartPie, Plus } from 'lucide-react'
import { formatVND, formatVNDCompact } from '@/lib/utils'
import { useAppStore } from '@/store/useAppStore'
import { DashboardData } from '@/types'
import { AnimatedCounter } from '@/components/ui/AnimatedCounter'
import { ChartTooltipProps } from '@/types/chart'

function EmptyBreakdown() {
  const openAddTransaction = useAppStore(s => s.openAddTransaction)
  return (
    <div className="empty-state" style={{ flex: 1 }}>
      <div className="icon-tile" style={{ width: 48, height: 48 }}>
        <ChartPie size={22} />
      </div>
      <span style={{ fontSize: 'var(--text-sm)' }}>No spending data yet</span>
      <button className="btn btn-secondary btn-sm" onClick={() => openAddTransaction('expense')}>
        <Plus size={13} /> Add expense
      </button>
    </div>
  )
}

interface SpendingBreakdownProps {
  data?: DashboardData
  isLoading: boolean
}

interface SpendingSlice {
  icon: string
}

function DonutTooltip({ active, payload }: ChartTooltipProps<SpendingSlice>) {
  if (!active || !payload?.length) return null
  const d = payload[0]
  return (
    <div className="chart-tooltip">
      <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 'var(--text-sm)' }}>
        {d.payload?.icon} {d.name}
      </div>
      <div style={{ marginTop: 'var(--space-1)', color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
        {formatVND(Number(d.value ?? 0))}
      </div>
    </div>
  )
}

const GROUP_CONFIG = {
  needs:   { label: 'Needs', target: 50, color: 'var(--accent-blue)' },
  wants:   { label: 'Wants', target: 30, color: 'var(--accent-green)' },
  savings: { label: 'Savings', target: 20, color: 'var(--accent-gold)' },
} as const

export function SpendingBreakdown({ data, isLoading }: SpendingBreakdownProps) {
  const pieData = data?.categoryBreakdown.map(c => ({
    name: c.categoryName,
    value: c.total,
    color: c.categoryColor,
    icon: c.categoryIcon,
  })) ?? []

  const totalExpense = pieData.reduce((s, c) => s + c.value, 0)
  const totalIncome = data?.currentMonth.income ?? 0
  const spending = data?.spendingByGroup ?? { needs: 0, wants: 0, savings: 0, unassigned: 0 }

  const groups = (['needs', 'wants', 'savings'] as const).map(key => {
    const cfg = GROUP_CONFIG[key]
    const actual = key === 'savings' ? (totalIncome - totalExpense) : spending[key]
    const actualPct = totalIncome > 0 ? (actual / totalIncome) * 100 : 0
    const targetPct = cfg.target
    const targetAmount = totalIncome * (targetPct / 100)
    const diff = actual - targetAmount
    return { key, label: cfg.label, color: cfg.color, actual, actualPct, targetPct, targetAmount, diff }
  })

  return (
    <div className="card" style={{ padding: 'var(--space-6)', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: 'var(--space-4)' }}>
        <div className="card-title-lg">
          Expense breakdown
        </div>
        <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)', marginTop: 2 }}>
          50/30/20 rule
        </div>
      </div>

      {isLoading ? (
        <div className="skeleton" style={{ flex: 1, borderRadius: 'var(--radius-md)' }} />
      ) : pieData.length === 0 ? (
        <EmptyBreakdown />
      ) : (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          {/* Donut chart */}
          <div style={{ position: 'relative', width: '100%', maxWidth: 220 }}>
            <ResponsiveContainer width="100%" height={200} minWidth={0} minHeight={0}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%" cy="50%"
                  innerRadius={65} outerRadius={95}
                  paddingAngle={2}
                  dataKey="value"
                  startAngle={90} endAngle={-270}
                  animationDuration={800}
                  animationEasing="ease-out"
                >
                  {pieData.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={entry.color}
                      stroke="var(--bg-secondary)"
                      strokeWidth={2}
                    />
                  ))}
                </Pie>
                <Tooltip content={<DonutTooltip />} wrapperStyle={{ zIndex: 10 }} />
              </PieChart>
            </ResponsiveContainer>
            {/* Center content */}
            <div style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              pointerEvents: 'none',
            }}>
              <div className="num-meta" style={{
                fontSize: 'var(--text-xl)',
                fontWeight: 700,
                color: 'var(--text-primary)',
              }}>
                <AnimatedCounter
                  value={totalExpense}
                  format={v => formatVNDCompact(Math.round(v))}
                />
              </div>
              <div style={{
                fontSize: 10,
                color: 'var(--accent-red)',
                fontWeight: 700,
                marginTop: 2,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
              }}>
                Total expense
              </div>
            </div>
          </div>

          {/* 50/30/20 breakdown */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', width: '100%', marginTop: 'var(--space-4)' }}>
            {groups.map((g, i) => {
              const isSavings = g.key === 'savings'
              const barPct = g.targetPct > 0 ? Math.min(100, Math.max(0, (g.actualPct / g.targetPct) * 100)) : 0

              const barColor = isSavings
                ? (g.actualPct >= g.targetPct ? 'var(--accent-green)' : g.actualPct > 0 ? g.color : 'var(--accent-red)')
                : (g.actualPct > g.targetPct ? 'var(--accent-red)' : g.color)

              const pctColor = isSavings
                ? (g.actualPct >= g.targetPct ? 'var(--accent-green)' : g.actualPct > 0 ? 'var(--text-primary)' : 'var(--accent-red)')
                : (g.actualPct > g.targetPct ? 'var(--accent-red)' : 'var(--text-primary)')

              const diffColor = isSavings
                ? (g.diff >= 0 ? 'var(--accent-green)' : 'var(--accent-red)')
                : (g.diff > 0 ? 'var(--accent-red)' : 'var(--accent-green)')

              return (
                <div key={g.key}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 5 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                      <div style={{ width: 10, height: 10, borderRadius: 'var(--radius-full)', background: g.color, flexShrink: 0 }} />
                      <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', fontWeight: 500 }}>
                        {g.label}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1-5)' }}>
                      <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: pctColor }}>
                        {Math.max(0, g.actualPct).toFixed(0)}%
                      </span>
                      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)' }}>
                        / {g.targetPct}%
                      </span>
                    </div>
                  </div>

                  <div style={{
                    height: 6,
                    borderRadius: 'var(--radius-full)',
                    background: 'var(--surface-hover)',
                    overflow: 'hidden',
                  }}>
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${barPct}%` }}
                      transition={{ duration: 0.7, delay: i * 0.12, ease: [0.25, 0.46, 0.45, 0.94] }}
                      style={{
                        height: '100%',
                        borderRadius: 'var(--radius-full)',
                        background: barColor,
                      }}
                    />
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 3 }}>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)' }}>
                      {formatVNDCompact(g.actual)}
                    </span>
                    <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: diffColor }}>
                      {g.diff > 0 ? '+' : ''}{formatVNDCompact(g.diff)}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
