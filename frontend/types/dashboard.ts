export interface DashboardData {
  netWorth: number
  selectedMonth: string
  currentMonth: { income: number; expense: number; savings: number }
  previousMonth: { income: number; expense: number; savings: number }
  monthlyChart: Array<{ month: string; income: number; expense: number }>
  categoryBreakdown: Array<{
    categoryId: string
    categoryName: string
    categoryIcon: string
    categoryColor: string
    budgetGroup: string | null
    total: number
  }>
  spendingByGroup: {
    needs: number
    wants: number
    savings: number
    unassigned: number
  }
  recentTransactions: Array<{
    id: string
    type: string
    amount: number
    description: string
    date: string
    categoryName: string
    categoryIcon: string
    categoryColor: string
  }>
  budgetProgress: Array<{
    categoryId: string
    categoryName: string
    categoryIcon: string
    categoryColor: string
    budgetAmount: number
    spentAmount: number
  }>
  upcomingBills: Array<{
    id: string
    description: string
    amount: number
    type: string
    nextRunDate: string
    frequency: string
    categoryIcon: string
    categoryColor: string
  }>
  assetLiability: {
    assets: Array<{ type: string; label: string; total: number }>
    liabilities: Array<{ type: string; label: string; total: number }>
    totalAssets: number
    totalLiabilities: number
  }
}
