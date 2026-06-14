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

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** Backend emits "T1".."T12" for yearly points; map to English month names. */
function localizeLabel(label: string): string {
  const m = /^T(\d{1,2})$/.exec(label)
  return m ? MONTH_LABELS[Number(m[1]) - 1] ?? label : label
}

function localizeLabels(data: ReportsData): ReportsData {
  return {
    ...data,
    chartData: data.chartData.map(p => ({ ...p, label: localizeLabel(p.label) })),
    trendData: data.trendData.map(p => ({ ...p, label: localizeLabel(p.label) })),
  }
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
    queryFn: async () => localizeLabels(await apiGet<ReportsData>('/api/reports', {
      mode,
      month: mode === 'month' ? selectedMonth : undefined,
      year: mode === 'year' ? selectedYear : undefined,
    })),
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
