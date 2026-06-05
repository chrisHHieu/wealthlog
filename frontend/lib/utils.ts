import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function formatVND(amount: number): string {
  return `${amount.toLocaleString('en-US')} VND`
}

export function formatVNDCompact(amount: number): string {
  if (Math.abs(amount) >= 1_000_000_000) {
    return `${(amount / 1_000_000_000).toFixed(1)}B VND`
  }
  if (Math.abs(amount) >= 1_000_000) {
    return `${(amount / 1_000_000).toFixed(1)}M VND`
  }
  if (Math.abs(amount) >= 1_000) {
    return `${(amount / 1_000).toFixed(0)}K VND`
  }
  return formatVND(amount)
}

export function parseShorthandAmount(input: string): number | null {
  const cleaned = input.trim()
  if (!cleaned) return null

  const numStr = cleaned.replace(/[.,]/g, '')
  const num = parseFloat(numStr)
  return Number.isNaN(num) ? null : num
}

export function formatAmountLive(val: string): string {
  const digits = val.replace(/[^\d]/g, '')
  if (!digits) return ''
  return new Intl.NumberFormat('en-US').format(Number(digits))
}

export function formatDateVI(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('en-US', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 5) return 'Good night'
  if (hour < 11) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

export function formatRelativeDate(date: string): string {
  const d = new Date(date)
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  return formatDateVI(date)
}

export function getMonthNameVI(month: number): string {
  return new Date(2000, month - 1, 1).toLocaleString('en-US', { month: 'long' })
}

export function formatMonthVI(yyyymm: string): string {
  const [year, month] = yyyymm.split('-')
  return `${new Date(Number(year), parseInt(month) - 1, 1).toLocaleString('en-US', { month: 'long' })} ${year}`
}

export function getCurrentMonth(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

export function getToday(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

export function getDaysRemaining(dateStr: string): number {
  const target = new Date(dateStr)
  const now = new Date()
  return Math.max(0, Math.floor((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)))
}

export function calcMonthlySavingsNeeded(
  targetAmount: number,
  currentAmount: number,
  deadlineStr: string
): number {
  const remaining = targetAmount - currentAmount
  if (remaining <= 0) return 0

  const deadline = new Date(deadlineStr)
  const now = new Date()
  const monthsLeft = Math.max(
    1,
    (deadline.getFullYear() - now.getFullYear()) * 12 +
      (deadline.getMonth() - now.getMonth())
  )

  return Math.ceil(remaining / monthsLeft)
}

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
