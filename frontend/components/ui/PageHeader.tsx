import { ReactNode } from 'react'

interface PageHeaderProps {
  /** Small mono-caps kicker above the title */
  eyebrow: string
  /** Editorial serif page title */
  title: string
  /** Optional supporting line under the title (count, summary, controls) */
  subtitle?: ReactNode
  /** Optional right-aligned controls (buttons, navigators, stats) */
  actions?: ReactNode
  className?: string
}

/**
 * Editorial page header used across every module: a mono-caps eyebrow over a
 * large serif title, with an optional subtitle and a right-aligned actions slot.
 */
export function PageHeader({ eyebrow, title, subtitle, actions, className }: PageHeaderProps) {
  return (
    <header className={`page-header${className ? ` ${className}` : ''}`}>
      <div className="page-header-lead">
        <div className="page-eyebrow">{eyebrow}</div>
        <h1 className="page-title">{title}</h1>
        {subtitle != null && <div className="page-subtitle">{subtitle}</div>}
      </div>
      {actions != null && <div className="page-header-actions">{actions}</div>}
    </header>
  )
}
