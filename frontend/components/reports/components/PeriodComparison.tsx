import { motion } from 'framer-motion'
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react'
import { formatVNDCompact } from '@/lib/utils'
import { CategoryComparison } from '@/types'

interface PeriodComparisonProps {
  expenseByCategory: CategoryComparison[]
  incomeByCategory: CategoryComparison[]
  isLoading: boolean
}

function ChangeIndicator({ current, previous }: { current: number; previous: number }) {
  if (previous === 0 && current === 0) {
    return <span style={{ color: 'var(--text-tertiary)' }}><Minus size={12} /></span>
  }
  const pct = previous === 0 ? 100 : ((current - previous) / previous) * 100
  const isUp = pct > 0
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 2,
      color: isUp ? '#ef4444' : '#10b981',
      fontSize: 12, fontWeight: 600,
    }}>
      {isUp ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
      {Math.abs(pct).toFixed(1)}%
    </span>
  )
}

function ComparisonTable({ data, type }: { data: CategoryComparison[]; type: 'expense' | 'income' }) {
  const filtered = data.filter(c => c.current > 0 || c.previous > 0)
  if (filtered.length === 0) return null

  const total = {
    current: filtered.reduce((s, c) => s + c.current, 0),
    previous: filtered.reduce((s, c) => s + c.previous, 0),
  }

  return (
    <div className="card" style={{ padding: 20, overflow: 'hidden' }}>
      <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>
        {type === 'expense' ? 'So sánh chi tiêu' : 'So sánh thu nhập'}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 16 }}>
        Kỳ hiện tại vs kỳ trước theo danh mục
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--surface-border)' }}>
              <th style={{ textAlign: 'left', padding: '8px 0', color: 'var(--text-secondary)', fontWeight: 600, fontSize: 12 }}>
                Danh mục
              </th>
              <th style={{ textAlign: 'right', padding: '8px 0', color: 'var(--text-secondary)', fontWeight: 600, fontSize: 12 }}>
                Kỳ trước
              </th>
              <th style={{ textAlign: 'right', padding: '8px 0', color: 'var(--text-secondary)', fontWeight: 600, fontSize: 12 }}>
                Kỳ này
              </th>
              <th style={{ textAlign: 'right', padding: '8px 0', color: 'var(--text-secondary)', fontWeight: 600, fontSize: 12, width: 80 }}>
                Thay đổi
              </th>
              <th style={{ textAlign: 'right', padding: '8px 0', color: 'var(--text-secondary)', fontWeight: 600, fontSize: 12, width: 50 }}>
                %
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((cat, i) => (
              <motion.tr
                key={cat.categoryId}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: i * 0.03 }}
                style={{ borderBottom: '1px solid var(--surface-border)' }}
              >
                <td style={{ padding: '10px 0' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{
                      width: 26, height: 26, borderRadius: 6,
                      background: `${cat.color}18`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 13, flexShrink: 0,
                    }}>
                      {cat.icon}
                    </div>
                    <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{cat.name}</span>
                  </div>
                </td>
                <td style={{ textAlign: 'right', padding: '10px 0', color: 'var(--text-secondary)' }}>
                  {formatVNDCompact(cat.previous)}
                </td>
                <td style={{ textAlign: 'right', padding: '10px 0', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {formatVNDCompact(cat.current)}
                </td>
                <td style={{ textAlign: 'right', padding: '10px 0' }}>
                  <ChangeIndicator current={cat.current} previous={cat.previous} />
                </td>
                <td style={{ textAlign: 'right', padding: '10px 0', color: 'var(--text-tertiary)', fontSize: 12 }}>
                  {cat.pct.toFixed(1)}%
                </td>
              </motion.tr>
            ))}
          </tbody>
          <tfoot>
            <tr style={{ borderTop: '2px solid var(--surface-border)' }}>
              <td style={{ padding: '10px 0', fontWeight: 700, color: 'var(--text-primary)' }}>Tổng</td>
              <td style={{ textAlign: 'right', padding: '10px 0', color: 'var(--text-secondary)', fontWeight: 600 }}>
                {formatVNDCompact(total.previous)}
              </td>
              <td style={{ textAlign: 'right', padding: '10px 0', fontWeight: 700, color: 'var(--text-primary)' }}>
                {formatVNDCompact(total.current)}
              </td>
              <td style={{ textAlign: 'right', padding: '10px 0' }}>
                <ChangeIndicator current={total.current} previous={total.previous} />
              </td>
              <td style={{ textAlign: 'right', padding: '10px 0', color: 'var(--text-tertiary)', fontSize: 12 }}>
                100%
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}

export function PeriodComparison({ expenseByCategory, incomeByCategory, isLoading }: PeriodComparisonProps) {
  if (isLoading) {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {[0, 1].map(i => (
          <div key={i} className="card" style={{ padding: 20 }}>
            <div className="skeleton" style={{ height: 18, width: 160, marginBottom: 16 }} />
            {[...Array(4)].map((_, j) => <div key={j} className="skeleton" style={{ height: 36, marginBottom: 8 }} />)}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
      <ComparisonTable data={expenseByCategory} type="expense" />
      <ComparisonTable data={incomeByCategory} type="income" />
    </div>
  )
}
