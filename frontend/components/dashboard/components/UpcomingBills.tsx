import { CalendarClock } from 'lucide-react'
import { formatVNDCompact } from '@/lib/utils'
import { DashboardData } from '@/types'

interface UpcomingBillsProps {
  data?: DashboardData
  isLoading: boolean
}

function formatBillDate(dateStr: string): string {
  const d = new Date(dateStr)
  return `Hạn: ${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`
}

function getDaysUntil(dateStr: string): number {
  const target = new Date(dateStr)
  const now = new Date()
  return Math.max(0, Math.ceil((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)))
}

export function UpcomingBills({ data, isLoading }: UpcomingBillsProps) {
  const bills = data?.upcomingBills ?? []

  return (
    <div className="card" style={{ padding: 'var(--space-5)', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
        <div style={{ fontWeight: 700, fontSize: 'var(--text-base)' }}>Hóa đơn sắp tới</div>
        <CalendarClock size={16} style={{ color: 'var(--text-tertiary)' }} />
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: 56, borderRadius: 'var(--radius-md)' }} />)}
        </div>
      ) : bills.length === 0 ? (
        <div className="empty-state" style={{ flex: 1, padding: 'var(--space-6) var(--space-3)' }}>
          <span style={{ fontSize: 32 }}>🎉</span>
          <span style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-1)', color: 'var(--text-tertiary)' }}>Không có hóa đơn sắp tới</span>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2-5)', flex: 1 }}>
          {bills.map(bill => {
            const daysLeft = getDaysUntil(bill.nextRunDate)
            const isUrgent = daysLeft <= 3

            return (
              <div key={bill.id} className={isUrgent ? 'pulse-alert' : ''} style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-3)',
                padding: 'var(--space-2-5) var(--space-3)',
                background: 'var(--surface)',
                borderRadius: 'var(--radius-md)',
                border: `1px solid ${isUrgent ? 'var(--accent-red-muted)' : 'var(--surface-border)'}`,
                transition: 'all var(--duration-fast) ease',
              }}>
                <div style={{
                  width: 40,
                  height: 40,
                  borderRadius: 'var(--radius-md)',
                  background: `${bill.categoryColor}18`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 18,
                  flexShrink: 0,
                }}>
                  {bill.categoryIcon}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: 'var(--text-sm)',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}>
                    {bill.description}
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginTop: 1 }}>
                    {formatBillDate(bill.nextRunDate)}
                  </div>
                </div>

                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <div style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {formatVNDCompact(bill.amount)}
                  </div>
                  <div style={{
                    fontSize: 10,
                    fontWeight: 700,
                    marginTop: 2,
                    color: isUrgent ? 'var(--accent-red)' : 'var(--accent-gold)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                  }}>
                    {daysLeft === 0 ? 'HÔM NAY' : `còn ${daysLeft} ngày`}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
