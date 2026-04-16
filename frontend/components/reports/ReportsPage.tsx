'use client'

import { useReports } from '@/hooks/useReports'
import { PageTransition } from '@/components/ui/PageTransition'
import { ScrollReveal } from '@/components/ui/ScrollReveal'
import { ReportHeader } from './components/ReportHeader'
import { ComparisonKPIs } from './components/ComparisonKPIs'
import { IncomeExpenseChart } from './components/IncomeExpenseChart'
import { SpendingTrend } from './components/SpendingTrend'
import { PeriodComparison } from './components/PeriodComparison'
import { CashFlowStatement } from './components/CashFlowStatement'

export function ReportsPage() {
  const {
    mode, setMode,
    selectedMonth, setSelectedMonth,
    selectedYear, setSelectedYear,
    isLoading,
    data,
  } = useReports()

  return (
    <PageTransition>
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)', paddingBottom: 'var(--space-10)' }}>
      {/* Header: title + mode toggle + period nav + export */}
      <ReportHeader
        mode={mode}
        setMode={setMode}
        selectedMonth={selectedMonth}
        setSelectedMonth={setSelectedMonth}
        selectedYear={selectedYear}
        setSelectedYear={setSelectedYear}
      />

      {/* Row 1: 4 Comparison KPI cards with period delta */}
      <ComparisonKPIs
        current={data.current}
        previous={data.previous}
        isLoading={isLoading}
      />

      {/* Row 2: Income vs Expense bar chart (60%) + Spending Trend area (40%) */}
      <ScrollReveal>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 3fr) minmax(0, 2fr)', gap: 'var(--space-5)' }}>
        <IncomeExpenseChart data={data.chartData} mode={mode} isLoading={isLoading} />
        <SpendingTrend data={data.trendData} mode={mode} isLoading={isLoading} />
      </div>
      </ScrollReveal>

      {/* Row 3: Period comparison tables (expense + income side by side) */}
      <PeriodComparison
        expenseByCategory={data.expenseByCategory}
        incomeByCategory={data.incomeByCategory}
        isLoading={isLoading}
      />

      {/* Row 4: Cash Flow Statement */}
      <ScrollReveal delay={0.1}>
        <CashFlowStatement data={data.cashFlow} isLoading={isLoading} />
      </ScrollReveal>
    </div>
    </PageTransition>
  )
}
