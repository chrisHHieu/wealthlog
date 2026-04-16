import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Wallet, CreditCard, Percent } from 'lucide-react'
import { AnimatedCounter } from '@/components/ui/AnimatedCounter'
import { formatVNDCompact } from '@/lib/utils'
import { SkeletonKPI } from '@/components/ui/SkeletonKPI'
import { DashboardData } from '@/types'

interface KPICardsProps {
  data?: DashboardData
  isLoading: boolean
  incomePct: string | null
  expensePct: string | null
}

interface KPIItem {
  label: string
  value: number
  color: string
  glowClass: string
  icon: React.ReactNode
  pctChange: string | null
  pctPositiveIsGood: boolean
  format?: (v: number) => string
}

function PctBadge({ pctChange, isGood }: { pctChange: string; isGood: boolean }) {
  const pctNum = parseFloat(pctChange)
  const isPositive = pctNum >= 0

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 3,
      padding: '2px 8px',
      borderRadius: 'var(--radius-full)',
      background: isGood ? 'var(--accent-green-subtle)' : 'var(--accent-red-subtle)',
      color: isGood ? 'var(--accent-green)' : 'var(--accent-red)',
      fontSize: 'var(--text-xs)',
      fontWeight: 700,
    }}>
      {isPositive ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
      {isPositive ? '+' : ''}{pctChange}%
    </div>
  )
}

function KPICard({ item, index }: { item: KPIItem; index: number }) {
  const { label, value, color, glowClass, icon, pctChange, pctPositiveIsGood, format } = item
  const pctNum = pctChange ? parseFloat(pctChange) : 0
  const isPositive = pctNum >= 0
  const isGood = pctPositiveIsGood ? isPositive : !isPositive

  return (
    <motion.div
      className={`kpi-card card ${glowClass}`}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
        <div style={{
          width: 40,
          height: 40,
          borderRadius: 'var(--radius-md)',
          background: `color-mix(in srgb, ${color} 12%, transparent)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color,
        }}>
          {icon}
        </div>
        {pctChange !== null && <PctBadge pctChange={pctChange} isGood={isGood} />}
      </div>

      <div style={{
        fontSize: 'var(--text-xs)',
        color: 'var(--text-tertiary)',
        marginBottom: 'var(--space-1-5)',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
      }}>
        {label}
      </div>

      <div style={{
        fontSize: 'var(--text-2xl)',
        fontWeight: 700,
        color: 'var(--text-primary)',
        lineHeight: 'var(--leading-tight)',
      }}>
        <AnimatedCounter
          value={value}
          format={format ?? (v => formatVNDCompact(Math.round(v)))}
        />
      </div>
    </motion.div>
  )
}

function NetWorthHero({ data, incomePct }: { data?: DashboardData; incomePct: string | null }) {
  const netWorth = data?.netWorth ?? 0
  const pctNum = incomePct ? parseFloat(incomePct) : 0
  const isPositive = pctNum >= 0

  return (
    <motion.div
      className="kpi-hero"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <div style={{ position: 'relative', zIndex: 1 }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-3)',
          marginBottom: 'var(--space-4)',
        }}>
          <div style={{
            width: 44,
            height: 44,
            borderRadius: 'var(--radius-md)',
            background: 'linear-gradient(135deg, var(--accent-green), var(--accent-gold))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--text-inverse)',
          }}>
            <Wallet size={22} />
          </div>
          <div>
            <div style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--text-tertiary)',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}>
              Tài sản ròng
            </div>
            {incomePct !== null && (
              <PctBadge pctChange={incomePct} isGood={isPositive} />
            )}
          </div>
        </div>

        <div className="font-display" style={{
          fontSize: 'var(--text-4xl)',
          fontWeight: 400,
          color: 'var(--text-primary)',
          lineHeight: 1.1,
          letterSpacing: '-0.02em',
        }}>
          <AnimatedCounter
            value={netWorth}
            format={v => formatVNDCompact(Math.round(v))}
          />
        </div>

        <div style={{
          fontSize: 'var(--text-sm)',
          color: 'var(--text-secondary)',
          marginTop: 'var(--space-2)',
        }}>
          {new Date().toLocaleDateString('vi-VN', { month: 'long', year: 'numeric' })}
        </div>
      </div>
    </motion.div>
  )
}

export function KPICards({ data, isLoading, incomePct, expensePct }: KPICardsProps) {
  if (isLoading) {
    return (
      <div className="kpi-grid">
        <div className="kpi-hero-slot"><SkeletonKPI /></div>
        <SkeletonKPI /><SkeletonKPI /><SkeletonKPI />
        <style jsx>{`
          .kpi-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: var(--space-4);
          }
          .kpi-hero-slot {
            grid-row: span 1;
          }
          @media (max-width: 1023px) {
            .kpi-grid { grid-template-columns: 1fr 1fr; }
          }
          @media (max-width: 639px) {
            .kpi-grid { grid-template-columns: 1fr; }
          }
        `}</style>
      </div>
    )
  }

  const savingsRate = data && data.currentMonth.income > 0
    ? Math.round(data.currentMonth.savings / data.currentMonth.income * 100)
    : 0

  const prevSavingsRate = data && data.previousMonth.income > 0
    ? Math.round(data.previousMonth.savings / data.previousMonth.income * 100)
    : 0

  const savingsRatePct = prevSavingsRate !== 0
    ? ((savingsRate - prevSavingsRate) / Math.abs(prevSavingsRate) * 100).toFixed(1)
    : null

  const kpis: KPIItem[] = [
    {
      label: 'Tổng thu nhập',
      value: data?.currentMonth.income ?? 0,
      color: 'var(--accent-green)',
      glowClass: 'card-glow-green',
      icon: <TrendingUp size={20} />,
      pctChange: incomePct,
      pctPositiveIsGood: true,
    },
    {
      label: 'Tổng chi tiêu',
      value: data?.currentMonth.expense ?? 0,
      color: 'var(--accent-red)',
      glowClass: 'card-glow-red',
      icon: <CreditCard size={20} />,
      pctChange: expensePct,
      pctPositiveIsGood: false,
    },
    {
      label: 'Tỷ lệ tiết kiệm',
      value: savingsRate,
      color: 'var(--accent-purple)',
      glowClass: 'card-glow-purple',
      icon: <Percent size={20} />,
      pctChange: savingsRatePct,
      pctPositiveIsGood: true,
      format: v => `${Math.round(v)}%`,
    },
  ]

  return (
    <div className="kpi-grid">
      <div className="kpi-hero-slot">
        <NetWorthHero data={data} incomePct={incomePct} />
      </div>
      {kpis.map((kpi, i) => <KPICard key={i} item={kpi} index={i + 1} />)}

      <style jsx>{`
        .kpi-grid {
          display: grid;
          grid-template-columns: 1.4fr 1fr 1fr 1fr;
          gap: var(--space-4);
          align-items: stretch;
        }
        .kpi-hero-slot {
          grid-row: span 1;
        }
        @media (max-width: 1279px) {
          .kpi-grid {
            grid-template-columns: 1fr 1fr;
          }
          .kpi-hero-slot {
            grid-column: span 2;
          }
        }
        @media (max-width: 639px) {
          .kpi-grid {
            grid-template-columns: 1fr;
          }
          .kpi-hero-slot {
            grid-column: span 1;
          }
        }
      `}</style>
    </div>
  )
}
