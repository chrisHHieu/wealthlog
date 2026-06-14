import { formatVNDCompact } from '@/lib/utils'
import { DashboardData } from '@/types'

export interface DashboardInsight {
  tone: 'good' | 'warning' | 'neutral'
  title: string
  detail: string
}

export interface DashboardAction {
  title: string
  detail: string
  href: string
  tone: 'good' | 'warning' | 'neutral'
}

export interface DashboardForecast {
  /** True when the selected month is the current calendar month. */
  isCurrentMonth: boolean
  daysElapsed: number
  daysLeft: number
  projectedExpense: number
  projectedSavings: number
  /** Daily spend that keeps the month cash-flow positive; null when already negative. */
  safeToSpendPerDay: number | null
  /** Liquid assets ÷ average monthly expense; null without enough history. */
  runwayMonths: number | null
}

export interface DashboardInsights {
  savingsRate: number
  expenseDeltaPct: number
  incomeDeltaPct: number
  topCategory?: DashboardData['categoryBreakdown'][number]
  overBudgetCount: number
  urgentBillsCount: number
  forecast: DashboardForecast
  insights: DashboardInsight[]
  actions: DashboardAction[]
}

const LIQUID_ASSET_TYPES = new Set(['cash', 'bank', 'ewallet', 'savings'])

function pctDelta(current: number, previous: number) {
  if (previous === 0) return current > 0 ? 100 : 0
  return ((current - previous) / previous) * 100
}

function daysUntil(dateStr: string) {
  const target = new Date(dateStr)
  const now = new Date()
  return Math.max(0, Math.ceil((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)))
}

function currentMonthStr() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function buildForecast(data: DashboardData): DashboardForecast {
  const selected = data.selectedMonth
  const isCurrentMonth = selected === currentMonthStr()
  const [year, month] = selected.split('-').map(Number)
  const daysInMonth = new Date(year, month, 0).getDate()
  const daysElapsed = isCurrentMonth ? Math.max(1, new Date().getDate()) : daysInMonth
  const daysLeft = daysInMonth - daysElapsed

  const { income, expense, savings } = data.currentMonth
  const projectedExpense = isCurrentMonth ? (expense / daysElapsed) * daysInMonth : expense
  const projectedSavings = income - projectedExpense
  const safeToSpendPerDay = isCurrentMonth && daysLeft > 0 && savings > 0
    ? savings / daysLeft
    : null

  // Runway: liquid assets ÷ average monthly spend over completed months with activity
  const liquidAssets = data.assetLiability.assets
    .filter(a => LIQUID_ASSET_TYPES.has(a.type))
    .reduce((sum, a) => sum + a.total, 0)
  const completedMonths = data.monthlyChart
    .slice(0, isCurrentMonth ? -1 : undefined)
    .filter(m => m.expense > 0)
  const avgMonthlyExpense = completedMonths.length > 0
    ? completedMonths.reduce((s, m) => s + m.expense, 0) / completedMonths.length
    : expense
  const runwayMonths = avgMonthlyExpense > 0 && liquidAssets > 0
    ? liquidAssets / avgMonthlyExpense
    : null

  return {
    isCurrentMonth,
    daysElapsed,
    daysLeft,
    projectedExpense,
    projectedSavings,
    safeToSpendPerDay,
    runwayMonths,
  }
}

/** Consecutive months with positive net savings, counting back from the latest active month. */
function savingsStreak(monthlyChart: DashboardData['monthlyChart']): number {
  const active = monthlyChart.filter(m => m.income > 0 || m.expense > 0)
  let streak = 0
  for (let i = active.length - 1; i >= 0; i--) {
    if (active[i].income - active[i].expense >= 0) streak++
    else break
  }
  return streak
}

export function buildDashboardInsights(data?: DashboardData): DashboardInsights {
  if (!data) {
    return {
      savingsRate: 0,
      expenseDeltaPct: 0,
      incomeDeltaPct: 0,
      overBudgetCount: 0,
      urgentBillsCount: 0,
      forecast: {
        isCurrentMonth: true,
        daysElapsed: 0,
        daysLeft: 0,
        projectedExpense: 0,
        projectedSavings: 0,
        safeToSpendPerDay: null,
        runwayMonths: null,
      },
      insights: [],
      actions: [],
    }
  }

  const savingsRate = data.currentMonth.income > 0
    ? (data.currentMonth.savings / data.currentMonth.income) * 100
    : 0
  const expenseDeltaPct = pctDelta(data.currentMonth.expense, data.previousMonth.expense)
  const incomeDeltaPct = pctDelta(data.currentMonth.income, data.previousMonth.income)
  const topCategory = data.categoryBreakdown[0]
  const overBudgetCount = data.budgetProgress.filter(b => b.budgetAmount > 0 && b.spentAmount / b.budgetAmount >= 0.9).length
  const urgentBillsCount = data.upcomingBills.filter(b => daysUntil(b.nextRunDate) <= 3).length
  const forecast = buildForecast(data)
  const streak = savingsStreak(data.monthlyChart)

  const insights: DashboardInsight[] = []

  // Headline: forward-looking for the current month, retrospective for past months
  if (forecast.isCurrentMonth && forecast.daysLeft > 0 && data.currentMonth.expense > 0) {
    insights.push({
      tone: forecast.projectedSavings >= 0 ? 'good' : 'warning',
      title: forecast.projectedSavings >= 0
        ? `On pace to save ${formatVNDCompact(forecast.projectedSavings)} this month`
        : `On pace to overspend by ${formatVNDCompact(Math.abs(forecast.projectedSavings))}`,
      detail: `At the current rate, month-end expenses land around ${formatVNDCompact(forecast.projectedExpense)} with ${forecast.daysLeft} days to go.`,
    })
  } else {
    insights.push({
      tone: data.currentMonth.savings >= 0 ? 'good' : 'warning',
      title: data.currentMonth.savings >= 0 ? 'Positive cash flow' : 'Negative cash flow',
      detail: data.currentMonth.savings >= 0
        ? `Savings rate is ${savingsRate.toFixed(1)}% for the selected month.`
        : 'Expenses are higher than income this month.',
    })
  }

  insights.push({
    tone: expenseDeltaPct <= 0 ? 'good' : 'warning',
    title: expenseDeltaPct <= 0 ? 'Expenses are down' : 'Expenses are up',
    detail: `Expenses changed ${expenseDeltaPct >= 0 ? '+' : ''}${expenseDeltaPct.toFixed(1)}% vs previous month.`,
  })

  if (topCategory && data.currentMonth.expense > 0) {
    const pct = (topCategory.total / data.currentMonth.expense) * 100
    insights.push({
      tone: pct >= 40 ? 'warning' : 'neutral',
      title: `${topCategory.categoryName} leads spending`,
      detail: `${formatVNDCompact(topCategory.total)} so far — ${pct.toFixed(0)}% of this month's expenses.`,
    })
  }

  if (streak >= 2) {
    insights.push({
      tone: 'good',
      title: `${streak}-month savings streak`,
      detail: `Net savings have stayed positive for ${streak} months in a row. Keep it going.`,
    })
  }

  const actions: DashboardAction[] = []
  if (overBudgetCount > 0) {
    actions.push({
      tone: 'warning',
      title: `${overBudgetCount} budget${overBudgetCount > 1 ? 's' : ''} need attention`,
      detail: 'Review budget usage before adding more discretionary spending.',
      href: '/budget',
    })
  }
  if (urgentBillsCount > 0) {
    actions.push({
      tone: 'warning',
      title: `${urgentBillsCount} upcoming bill${urgentBillsCount > 1 ? 's' : ''} due soon`,
      detail: 'Check recurring bills due within the next 3 days.',
      href: '/recurring',
    })
  }
  if (forecast.runwayMonths !== null && forecast.runwayMonths < 3) {
    actions.push({
      tone: 'warning',
      title: 'Emergency fund is thin',
      detail: `Liquid assets cover ~${forecast.runwayMonths.toFixed(1)} months of typical spending. Aim for 3-6 months.`,
      href: '/goals',
    })
  }
  actions.push({
    tone: data.currentMonth.savings >= 0 ? 'good' : 'neutral',
    title: 'Review monthly report',
    detail: 'Open detailed reports for category movement and largest transactions.',
    href: '/reports',
  })

  return {
    savingsRate,
    expenseDeltaPct,
    incomeDeltaPct,
    topCategory,
    overBudgetCount,
    urgentBillsCount,
    forecast,
    insights,
    actions,
  }
}
