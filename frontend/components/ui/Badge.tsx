import { cva, type VariantProps } from 'class-variance-authority'
import { TrendingDown, TrendingUp } from 'lucide-react'
import { cn } from '@/lib/utils'

const badgeVariants = cva('badge', {
  variants: {
    tone: {
      success: 'badge-green',
      danger: 'badge-red',
      info: 'badge-blue',
      warning: 'badge-yellow',
      ai: 'badge-purple',
      neutral: 'badge-neutral',
    },
  },
  defaultVariants: {
    tone: 'neutral',
  },
})

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ tone, className, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />
}

interface TrendBadgeProps {
  /** Percent change as string, e.g. "12.5" or "-3.1" */
  pctChange: string
  /** Whether a positive change is good (income) or bad (expense) */
  positiveIsGood?: boolean
}

export function TrendBadge({ pctChange, positiveIsGood = true }: TrendBadgeProps) {
  const isPositive = parseFloat(pctChange) >= 0
  const isGood = positiveIsGood ? isPositive : !isPositive

  return (
    <Badge tone={isGood ? 'success' : 'danger'}>
      {isPositive ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
      {isPositive ? '+' : ''}{pctChange}%
    </Badge>
  )
}

export function StatusBadge({ label, isGood }: { label: string; isGood: boolean }) {
  return (
    <Badge tone={isGood ? 'success' : 'danger'}>
      {isGood ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
      {label}
    </Badge>
  )
}
