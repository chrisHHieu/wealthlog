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

export interface DashboardInsights {
  savingsRate: number
  expenseDeltaPct: number
  incomeDeltaPct: number
  topCategory?: DashboardData['categoryBreakdown'][number]
  overBudgetCount: number
  urgentBillsCount: number
  insights: DashboardInsight[]
  actions: DashboardAction[]
}

function pctDelta(current: number, previous: number) {
  if (previous === 0) return current > 0 ? 100 : 0
  return ((current - previous) / previous) * 100
}

function daysUntil(dateStr: string) {
  const target = new Date(dateStr)
  const now = new Date()
  return Math.max(0, Math.ceil((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)))
}

export function buildDashboardInsights(data?: DashboardData): DashboardInsights {
  if (!data) {
    return {
      savingsRate: 0,
      expenseDeltaPct: 0,
      incomeDeltaPct: 0,
      overBudgetCount: 0,
      urgentBillsCount: 0,
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

  const insights: DashboardInsight[] = [
    {
      tone: data.currentMonth.savings >= 0 ? 'good' : 'warning',
      title: data.currentMonth.savings >= 0 ? 'Positive month-to-date cash flow' : 'Negative month-to-date cash flow',
      detail: data.currentMonth.savings >= 0
        ? `Savings rate is ${savingsRate.toFixed(1)}% for the selected month.`
        : 'Expenses are currently higher than income this month.',
    },
    {
      tone: expenseDeltaPct <= 0 ? 'good' : 'warning',
      title: expenseDeltaPct <= 0 ? 'Expenses are down' : 'Expenses are up',
      detail: `Expenses changed ${expenseDeltaPct >= 0 ? '+' : ''}${expenseDeltaPct.toFixed(1)}% vs previous month.`,
    },
  ]

  if (topCategory) {
    insights.push({
      tone: 'neutral',
      title: 'Top spending category',
      detail: `${topCategory.categoryName} is the largest expense category this month.`,
    })
  }

  const actions: DashboardAction[] = []
  if (overBudgetCount > 0) {
    actions.push({
      tone: 'warning',
      title: `${overBudgetCount} budget needs attention`,
      detail: 'Review budget usage before adding more discretionary spending.',
      href: '/budget',
    })
  }
  if (urgentBillsCount > 0) {
    actions.push({
      tone: 'warning',
      title: `${urgentBillsCount} upcoming bill due soon`,
      detail: 'Check recurring bills due within the next 3 days.',
      href: '/recurring',
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
    insights,
    actions,
  }
}
