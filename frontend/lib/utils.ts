/**
 * Format a number as Vietnamese Dong currency
 * Example: 1500000 → "1.500.000 đ"
 */
export function formatVND(amount: number): string {
  return amount.toLocaleString('vi-VN') + ' đ'
}

/**
 * Format a number as compact VND (e.g. 1.5 triệu)
 */
export function formatVNDCompact(amount: number): string {
  if (Math.abs(amount) >= 1_000_000_000) {
    return (amount / 1_000_000_000).toFixed(1) + ' tỷ'
  }
  if (Math.abs(amount) >= 1_000_000) {
    return (amount / 1_000_000).toFixed(1) + ' triệu'
  }
  if (Math.abs(amount) >= 1_000) {
    return (amount / 1_000).toFixed(0) + 'k'
  }
  return formatVND(amount)
}

/**
 * Parse formatted number strings (e.g. "1.234.567" -> 1234567)
 */
export function parseShorthandAmount(input: string): number | null {
  const cleaned = input.trim();
  if (!cleaned) return null;

  // Remove ALL dots and commas
  const numStr = cleaned.replace(/[.,]/g, '');
  
  const num = parseFloat(numStr);
  if (isNaN(num)) return null;

  return num;
}

/**
 * Auto-format number as you type (1.234.567)
 */
export function formatAmountLive(val: string): string {
  // Strip everything that is not a digit
  const digits = val.replace(/[^\d]/g, '');
  if (!digits) return ''; // return empty if no digits found
  
  // Auto-format the integer part
  return new Intl.NumberFormat('vi-VN').format(Number(digits));
}

/**
 * Format date in Vietnamese style
 */
export function formatDateVI(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

/**
 * Get greeting based on time of day
 */
export function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 5) return 'Chào đêm khuya'
  if (hour < 11) return 'Chào buổi sáng'
  if (hour < 14) return 'Chào buổi trưa'
  if (hour < 18) return 'Chào buổi chiều'
  return 'Chào buổi tối'
}

/**
 * Format date as relative time
 */
export function formatRelativeDate(date: string): string {
  const d = new Date(date)
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Hôm nay'
  if (diffDays === 1) return 'Hôm qua'
  if (diffDays < 7) return `${diffDays} ngày trước`
  return formatDateVI(date)
}

/**
 * Get month name in Vietnamese
 */
export function getMonthNameVI(month: number): string {
  return `Tháng ${month}`
}

/**
 * Format YYYY-MM to Vietnamese month string
 */
export function formatMonthVI(yyyymm: string): string {
  const [year, month] = yyyymm.split('-')
  return `Tháng ${parseInt(month)}/${year}`
}

/**
 * Get current month in YYYY-MM format
 */
export function getCurrentMonth(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

/**
 * Get today's date in YYYY-MM-DD format using LOCAL timezone.
 * Unlike toISOString() which uses UTC, this respects the user's timezone.
 */
export function getToday(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

/**
 * Get days remaining until a date
 */
export function getDaysRemaining(dateStr: string): number {
  const target = new Date(dateStr)
  const now = new Date()
  return Math.max(0, Math.floor((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)))
}

/**
 * Calculate monthly savings needed to reach a goal
 */
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

/**
 * cn utility for conditional classnames
 */
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
