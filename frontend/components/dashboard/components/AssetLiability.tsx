import { formatVNDCompact } from '@/lib/utils'
import { AnimatedCounter } from '@/components/ui/AnimatedCounter'
import { DashboardData } from '@/types'

interface AssetLiabilityProps {
  data?: DashboardData
  isLoading: boolean
}

const TYPE_ICONS: Record<string, string> = {
  cash: '💵', bank: '🏦', ewallet: '📱',
  investment: '📈', savings: '🏧', debt: '💳',
}

function SectionRow({ label, total, icon }: { label: string; total: number; icon: string }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: 'var(--space-1-5) 0',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
        <span style={{ fontSize: 14 }}>{icon}</span>
        <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>{label}</span>
      </div>
      <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text-primary)' }}>
        {formatVNDCompact(total)}
      </span>
    </div>
  )
}

export function AssetLiability({ data, isLoading }: AssetLiabilityProps) {
  const al = data?.assetLiability

  return (
    <div className="card" style={{ padding: 'var(--space-6)', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ fontWeight: 700, fontSize: 'var(--text-lg)', marginBottom: 'var(--space-5)' }}>
        Cấu trúc Tài sản & Nợ
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {[...Array(5)].map((_, i) => <div key={i} className="skeleton" style={{ height: 28, borderRadius: 'var(--radius-sm)' }} />)}
        </div>
      ) : !al ? (
        <div className="empty-state" style={{ flex: 1 }}>
          <span style={{ fontSize: 32 }}>🏦</span>
          <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)' }}>Chưa có dữ liệu</span>
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {/* Assets */}
          <div style={{
            fontSize: 'var(--text-xs)',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: 'var(--accent-green)',
            marginBottom: 'var(--space-2)',
          }}>
            Tài sản
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {al.assets.map(a => (
              <SectionRow key={a.type} label={a.label} total={a.total} icon={TYPE_ICONS[a.type] ?? '💰'} />
            ))}
          </div>

          {al.assets.length > 0 && al.liabilities.length > 0 && (
            <div className="divider" style={{ margin: 'var(--space-3) 0' }} />
          )}

          {/* Liabilities */}
          {al.liabilities.length > 0 && (
            <>
              <div style={{
                fontSize: 'var(--text-xs)',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                color: 'var(--accent-red)',
                marginBottom: 'var(--space-2)',
              }}>
                Nợ
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {al.liabilities.map(l => (
                  <SectionRow key={l.type} label={l.label} total={l.total} icon={TYPE_ICONS[l.type] ?? '💳'} />
                ))}
              </div>
            </>
          )}

          {/* Net worth */}
          <div style={{ marginTop: 'auto', paddingTop: 'var(--space-4)' }}>
            <div className="divider" style={{ marginBottom: 'var(--space-3)' }} />
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-secondary)' }}>Tổng ròng</span>
              <span className="font-display" style={{
                fontSize: 'var(--text-xl)',
                fontWeight: 400,
                color: data!.netWorth >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
              }}>
                <AnimatedCounter
                  value={data!.netWorth}
                  format={v => formatVNDCompact(Math.round(v))}
                />
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
