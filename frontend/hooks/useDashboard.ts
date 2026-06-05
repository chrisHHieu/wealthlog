import { useQuery } from '@tanstack/react-query'
import { DashboardData } from '@/types'
import { apiGet, queryKeys } from '@/lib/api'
import { useGoals } from './useGoals'

export function useDashboard(chartPeriod: string, selectedMonth: string) {
  const dashboardQuery = useQuery<DashboardData>({
    queryKey: queryKeys.dashboard(chartPeriod, selectedMonth),
    queryFn: () => apiGet<DashboardData>('/api/dashboard', {
      period: chartPeriod,
      month: selectedMonth,
    }),
  })

  const { data: goals = [] } = useGoals()
  const activeGoals = goals.filter(g => !g?.isCompleted).slice(0, 3)

  const data = dashboardQuery.data
  const incomeDiff = data ? data.currentMonth.income - data.previousMonth.income : 0
  const expenseDiff = data ? data.currentMonth.expense - data.previousMonth.expense : 0

  function calcPct(current: number, previous: number) {
    if (previous === 0 || current === 0) return null
    return ((current - previous) / Math.abs(previous) * 100).toFixed(1)
  }

  const incomePct = data ? calcPct(data.currentMonth.income, data.previousMonth.income) : null
  const expensePct = data ? calcPct(data.currentMonth.expense, data.previousMonth.expense) : null

  return {
    ...dashboardQuery,
    activeGoals,
    stats: {
      incomeDiff,
      expenseDiff,
      incomePct,
      expensePct
    }
  }
}
