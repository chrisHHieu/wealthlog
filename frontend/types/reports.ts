export interface PeriodSummary {
  income: number
  expense: number
  savings: number
  savingsRate: number
}

export interface CategoryComparison {
  categoryId: string
  name: string
  icon: string
  color: string
  current: number
  previous: number
  pct: number
}

export interface ChartPoint {
  label: string
  income: number
  expense: number
}

export interface TrendPoint {
  label: string
  cumExpense: number
  expense: number
}

export interface CashFlowData {
  incomeItems: CategoryComparison[]
  expenseItems: CategoryComparison[]
  totalIncome: number
  totalExpense: number
  net: number
}

export interface TopTransaction {
  type: string
  amount: number
  date: string
  description: string
  categoryName: string
  categoryIcon: string
  categoryColor: string
}

export interface ReportsData {
  current: PeriodSummary
  previous: PeriodSummary
  chartData: ChartPoint[]
  trendData: TrendPoint[]
  expenseByCategory: CategoryComparison[]
  incomeByCategory: CategoryComparison[]
  cashFlow: CashFlowData
  topTransactions: TopTransaction[]
}
