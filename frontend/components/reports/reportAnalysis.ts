import { CategoryComparison, ChartPoint, ReportsData } from '@/types'

export interface ReportInsight {
  tone: 'good' | 'warning' | 'neutral'
  title: string
  detail: string
}

export interface ReportAnalysis {
  expenseDeltaPct: number
  incomeDeltaPct: number
  savingsDeltaPct: number
  expenseDeltaAmount: number
  topExpense?: CategoryComparison
  topIncome?: CategoryComparison
  topIncrease?: CategoryComparison
  topDecrease?: CategoryComparison
  bestPoint?: ChartPoint
  worstPoint?: ChartPoint
  fixedExpense: number
  variableExpense: number
  fixedExpensePct: number
  /** Average expense per chart point: per day (month mode) or per month (year mode). */
  avgExpensePerPoint: number
  /** Points (days/months) with any spending. */
  activeSpendingPoints: number
  /** Total chart points in the period: days (month mode) or months (year mode). */
  totalPoints: number
  insights: ReportInsight[]
}

const FIXED_CATEGORY_NAMES = new Set([
  'Housing',
  'Rent',
  'Bills & Utilities',
  'Bank fees',
  'Transportation',
  'Laundry / Living',
])

function pctDelta(current: number, previous: number) {
  if (previous === 0) return current > 0 ? 100 : 0
  return ((current - previous) / previous) * 100
}

function asSignedPct(value: number) {
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`
}

function movement(category: CategoryComparison) {
  return category.current - category.previous
}

function pointSavings(point: ChartPoint) {
  return point.income - point.expense
}

export function analyzeReport(data: ReportsData): ReportAnalysis {
  const expenseDeltaPct = pctDelta(data.current.expense, data.previous.expense)
  const incomeDeltaPct = pctDelta(data.current.income, data.previous.income)
  const savingsDeltaPct = pctDelta(data.current.savings, data.previous.savings)

  const expenseItems = data.expenseByCategory.filter(c => c.current > 0)
  const incomeItems = data.incomeByCategory.filter(c => c.current > 0)
  const topExpense = expenseItems[0]
  const topIncome = incomeItems[0]

  const movedExpenses = data.expenseByCategory
    .filter(c => c.current > 0 || c.previous > 0)
    .sort((a, b) => Math.abs(movement(b)) - Math.abs(movement(a)))
  const topIncrease = movedExpenses.find(c => movement(c) > 0)
  const topDecrease = movedExpenses.find(c => movement(c) < 0)

  const pointsWithActivity = data.chartData.filter(p => p.income > 0 || p.expense > 0)
  const bestPoint = pointsWithActivity.length
    ? [...pointsWithActivity].sort((a, b) => pointSavings(b) - pointSavings(a))[0]
    : undefined
  const worstPoint = pointsWithActivity.length
    ? [...pointsWithActivity].sort((a, b) => pointSavings(a) - pointSavings(b))[0]
    : undefined

  const fixedExpense = expenseItems
    .filter(c => FIXED_CATEGORY_NAMES.has(c.name))
    .reduce((sum, item) => sum + item.current, 0)
  const variableExpense = Math.max(0, data.current.expense - fixedExpense)
  const fixedExpensePct = data.current.expense > 0 ? (fixedExpense / data.current.expense) * 100 : 0

  const expenseDeltaAmount = data.current.expense - data.previous.expense
  const avgExpensePerPoint = data.chartData.length > 0
    ? data.current.expense / data.chartData.length
    : 0
  const activeSpendingPoints = data.chartData.filter(p => p.expense > 0).length
  const totalPoints = data.chartData.length

  const insights: ReportInsight[] = [
    {
      tone: data.current.savings >= 0 ? 'good' : 'warning',
      title: data.current.savings >= 0 ? 'Positive cash flow' : 'Negative cash flow',
      detail: data.current.savings >= 0
        ? `Net savings are positive with a ${data.current.savingsRate.toFixed(1)}% savings rate.`
        : `Expenses are higher than income by ${Math.abs(data.current.savings).toLocaleString('en-US')} VND.`,
    },
    {
      tone: expenseDeltaPct <= 0 ? 'good' : 'warning',
      title: expenseDeltaPct <= 0 ? 'Expenses improved' : 'Expenses increased',
      detail: `Expenses changed ${asSignedPct(expenseDeltaPct)} compared with the previous period.`,
    },
    {
      tone: incomeDeltaPct >= 0 ? 'good' : 'neutral',
      title: incomeDeltaPct >= 0 ? 'Income is stable or higher' : 'Income declined',
      detail: `Income changed ${asSignedPct(incomeDeltaPct)} compared with the previous period.`,
    },
  ]

  if (topExpense) {
    insights.push({
      tone: topExpense.pct >= 50 ? 'warning' : 'neutral',
      title: 'Largest expense category',
      detail: `${topExpense.name} represents ${topExpense.pct.toFixed(1)}% of total expenses.`,
    })
  }

  // Category spike: >50% jump vs previous period with a meaningful base amount
  const spike = movedExpenses.find(c =>
    c.previous > 0 &&
    c.current > c.previous * 1.5 &&
    c.current >= data.current.expense * 0.1,
  )
  if (spike) {
    insights.push({
      tone: 'warning',
      title: `${spike.name} spiked`,
      detail: `${spike.name} jumped ${asSignedPct(pctDelta(spike.current, spike.previous))} to ${spike.current.toLocaleString('en-US')} VND vs the previous period.`,
    })
  }

  return {
    expenseDeltaPct,
    incomeDeltaPct,
    savingsDeltaPct,
    expenseDeltaAmount,
    topExpense,
    topIncome,
    topIncrease,
    topDecrease,
    bestPoint,
    worstPoint,
    fixedExpense,
    variableExpense,
    fixedExpensePct,
    avgExpensePerPoint,
    activeSpendingPoints,
    totalPoints,
    insights,
  }
}
