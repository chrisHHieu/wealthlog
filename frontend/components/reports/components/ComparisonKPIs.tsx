import { TrendingUp, TrendingDown, Wallet, Percent } from 'lucide-react'
import { motion } from 'framer-motion'
import { formatVNDCompact } from '@/lib/utils'
import { PeriodSummary } from '@/types'

interface ComparisonKPIsProps {
  current: PeriodSummary
  previous: PeriodSummary
  isLoading: boolean
}

function calcChange(cur: number, prev: number): { pct: string; direction: 'up' | 'down' | 'flat' } {
  if (prev === 0) return { pct: cur > 0 ? '+100' : '0', direction: cur > 0 ? 'up' : 'flat' }
  const change = ((cur - prev) / prev) * 100
  return {
    pct: (change >= 0 ? '+' : '') + change.toFixed(1),
    direction: change > 0 ? 'up' : change < 0 ? 'down' : 'flat',
  }
}

export function ComparisonKPIs({ current, previous, isLoading }: ComparisonKPIsProps) {
  const incChange = calcChange(current.income, previous.income)
  const expChange = calcChange(current.expense, previous.expense)
  const savChange = calcChange(current.savings, previous.savings)

  const kpis = [
    {
      label: 'Thu nhập',
      value: current.income,
      prevValue: previous.income,
      color: 'var(--accent-green)',
      icon: <TrendingUp size={16} />,
      change: incChange,
      positive: incChange.direction === 'up',
    },
    {
      label: 'Chi tiêu',
      value: current.expense,
      prevValue: previous.expense,
      color: 'var(--accent-red)',
      icon: <TrendingDown size={16} />,
      change: expChange,
      positive: expChange.direction === 'down', // less expense is good
    },
    {
      label: 'Tiết kiệm ròng',
      value: current.savings,
      prevValue: previous.savings,
      color: current.savings >= 0 ? 'var(--accent-blue)' : 'var(--accent-red)',
      icon: <Wallet size={16} />,
      change: savChange,
      positive: savChange.direction === 'up',
    },
    {
      label: 'Tỷ lệ tiết kiệm',
      value: null,
      prevValue: null,
      text: `${current.savingsRate.toFixed(1)}%`,
      prevText: `${previous.savingsRate.toFixed(1)}%`,
      color: 'var(--accent-purple)',
      icon: <Percent size={16} />,
      change: calcChange(current.savingsRate, previous.savingsRate),
      positive: current.savingsRate >= previous.savingsRate,
    },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
      {kpis.map((kpi, i) => (
        <motion.div
          key={i}
          className="card"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: i * 0.06 }}
          style={{ padding: '18px 20px' }}
        >
          {/* Icon + Label */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8,
              background: `${kpi.color}15`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: kpi.color,
            }}>
              {kpi.icon}
            </div>
            <span style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500 }}>{kpi.label}</span>
          </div>

          {/* Value */}
          <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>
            {isLoading
              ? <div className="skeleton" style={{ height: 26, width: 100 }} />
              : (kpi.text ?? formatVNDCompact(kpi.value ?? 0))}
          </div>

          {/* Change badge + previous value */}
          {!isLoading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: 3,
                padding: '2px 7px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                background: kpi.positive ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
                color: kpi.positive ? '#10b981' : '#ef4444',
              }}>
                {kpi.change.direction === 'up' ? '↑' : kpi.change.direction === 'down' ? '↓' : '→'}
                {kpi.change.pct}%
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                vs kỳ trước
              </span>
            </div>
          )}
        </motion.div>
      ))}
    </div>
  )
}
