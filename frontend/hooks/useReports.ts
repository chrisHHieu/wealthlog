import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ReportsData } from '@/types'
import { apiGet, queryKeys } from '@/lib/api'

export type ReportMode = 'month' | 'year'

function getCurrentMonthStr() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function getCurrentYear() {
  return new Date().getFullYear()
}

export function navigateMonth(yyyymm: string, delta: number): string {
  const [y, m] = yyyymm.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const emptyData: ReportsData = {
  current: { income: 0, expense: 0, savings: 0, savingsRate: 0 },
  previous: { income: 0, expense: 0, savings: 0, savingsRate: 0 },
  chartData: [],
  trendData: [],
  expenseByCategory: [],
  incomeByCategory: [],
  cashFlow: { incomeItems: [], expenseItems: [], totalIncome: 0, totalExpense: 0, net: 0 },
  topTransactions: [],
}

export function useReports() {
  const [mode, setMode] = useState<ReportMode>('month')
  const [selectedMonth, setSelectedMonth] = useState(getCurrentMonthStr)
  const [selectedYear, setSelectedYear] = useState(getCurrentYear)

  const { data = emptyData, isLoading } = useQuery<ReportsData>({
    queryKey: queryKeys.reports(mode, selectedMonth, selectedYear),
    queryFn: () => apiGet<ReportsData>('/api/reports', {
      mode,
      month: mode === 'month' ? selectedMonth : undefined,
      year: mode === 'year' ? selectedYear : undefined,
    }),
  })

  return {
    mode, setMode,
    selectedMonth, setSelectedMonth,
    selectedYear, setSelectedYear,
    isLoading,
    data,
  }
}

export { getCurrentMonthStr, getCurrentYear }
