import { motion } from 'framer-motion'
import { formatVNDCompact, formatVND } from '@/lib/utils'
import { CashFlowData } from '@/types'

interface CashFlowStatementProps {
  data: CashFlowData
  isLoading: boolean
}

function FlowRow({ icon, name, amount, color, index }: {
  icon: string; name: string; amount: number; color: string; index: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2, delay: index * 0.03 }}
      style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 0',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          width: 28, height: 28, borderRadius: 7,
          background: `color-mix(in srgb, ${color} 8%, transparent)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 14, flexShrink: 0,
        }}>
          {icon}
        </div>
        <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{name}</span>
      </div>
      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>
        {formatVNDCompact(amount)}
      </span>
    </motion.div>
  )
}

export function CashFlowStatement({ data, isLoading }: CashFlowStatementProps) {
  if (isLoading) {
    return (
      <div className="card" style={{ padding: 20 }}>
        <div className="skeleton" style={{ height: 18, width: 180, marginBottom: 16 }} />
        {[...Array(6)].map((_, i) => <div key={i} className="skeleton" style={{ height: 36, marginBottom: 8 }} />)}
      </div>
    )
  }

  const netColor = data.net >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'

  return (
    <div className="card" style={{ padding: 20 }}>
      <div className="card-title" style={{ marginBottom: 4 }}>Cash flow statement</div>
      <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 20 }}>
        Income and expense overview by category
      </div>

      {/* Income section */}
      <div style={{ marginBottom: 16 }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '6px 0', marginBottom: 4,
          borderBottom: '1px solid var(--surface-border)',
        }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--accent-green)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            Income
          </span>
          <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent-green)' }}>
            +{formatVNDCompact(data.totalIncome)}
          </span>
        </div>
        {data.incomeItems.map((item, i) => (
          <FlowRow key={item.categoryId} icon={item.icon} name={item.name} amount={item.current} color={item.color} index={i} />
        ))}
        {data.incomeItems.length === 0 && (
          <div style={{ padding: '12px 0', fontSize: 12, color: 'var(--text-tertiary)', textAlign: 'center' }}>
            No income yet
          </div>
        )}
      </div>

      {/* Expense section */}
      <div style={{ marginBottom: 16 }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '6px 0', marginBottom: 4,
          borderBottom: '1px solid var(--surface-border)',
        }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--accent-red)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            Expense
          </span>
          <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent-red)' }}>
            -{formatVNDCompact(data.totalExpense)}
          </span>
        </div>
        {data.expenseItems.map((item, i) => (
          <FlowRow key={item.categoryId} icon={item.icon} name={item.name} amount={item.current} color={item.color} index={i + data.incomeItems.length} />
        ))}
        {data.expenseItems.length === 0 && (
          <div style={{ padding: '12px 0', fontSize: 12, color: 'var(--text-tertiary)', textAlign: 'center' }}>
            No expenses yet
          </div>
        )}
      </div>

      {/* Net result */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 16px', borderRadius: 10,
        background: `color-mix(in srgb, ${netColor} 6%, transparent)`,
        border: `1px solid color-mix(in srgb, ${netColor} 18%, transparent)`,
      }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
          Net cash flow
        </span>
        <span style={{ fontSize: 18, fontWeight: 800, color: netColor, fontVariantNumeric: 'tabular-nums' }}>
          {data.net >= 0 ? '+' : ''}{formatVND(data.net)}
        </span>
      </div>
    </div>
  )
}
