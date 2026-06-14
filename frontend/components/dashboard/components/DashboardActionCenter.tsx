import Link from 'next/link'
import { ArrowRight, AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import { DashboardInsights } from '../dashboardInsights'

interface DashboardActionCenterProps {
  insights: DashboardInsights
  isLoading: boolean
}

const toneConfig = {
  good: { color: 'var(--accent-green)', icon: CheckCircle2 },
  warning: { color: 'var(--accent-red)', icon: AlertTriangle },
  neutral: { color: 'var(--accent-blue)', icon: Info },
}

export function DashboardActionCenter({ insights, isLoading }: DashboardActionCenterProps) {
  if (isLoading) {
    return (
      <div className="card" style={{ padding: 20 }}>
        <div className="skeleton" style={{ height: 18, width: 160, marginBottom: 14 }} />
        <div className="skeleton" style={{ height: 80, borderRadius: 8 }} />
      </div>
    )
  }

  return (
    <section className="card" style={{ padding: 20, height: '100%' }}>
      <div className="card-title" style={{ marginBottom: 14 }}>Priority actions</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {insights.actions.slice(0, 3).map(action => {
          const cfg = toneConfig[action.tone]
          const Icon = cfg.icon
          return (
            <Link
              href={action.href}
              key={action.title}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                border: '1px solid var(--surface-border)',
                borderRadius: 8,
                padding: 12,
                background: 'var(--surface)',
                textDecoration: 'none',
              }}
            >
              <Icon size={17} color={cfg.color} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>{action.title}</div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 3, lineHeight: 1.45 }}>{action.detail}</div>
              </div>
              <ArrowRight size={14} color="var(--text-tertiary)" />
            </Link>
          )
        })}
      </div>
    </section>
  )
}
