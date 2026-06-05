'use client'

import { useReports } from '@/hooks/useReports'
import { PageTransition } from '@/components/ui/PageTransition'
import { ReportHeader } from './components/ReportHeader'
import { ComparisonKPIs } from './components/ComparisonKPIs'
import { ExecutiveSummary } from './components/ExecutiveSummary'
import { MonthlyReportView } from './components/MonthlyReportView'
import { YearlyReportView } from './components/YearlyReportView'
import { analyzeReport } from './reportAnalysis'

export function ReportsPage() {
  const {
    mode, setMode,
    selectedMonth, setSelectedMonth,
    selectedYear, setSelectedYear,
    isLoading,
    data,
  } = useReports()
  const analysis = analyzeReport(data)
  const periodLabel = mode === 'month'
    ? (() => { const [year, month] = selectedMonth.split('-'); return `${new Date(Number(year), Number(month) - 1, 1).toLocaleString('en-US', { month: 'long' })} ${year}` })()
    : String(selectedYear)

  return (
    <PageTransition>
    <div className="reports-page">
      {/* Header: title + mode toggle + period nav + export */}
      <ReportHeader
        mode={mode}
        setMode={setMode}
        selectedMonth={selectedMonth}
        setSelectedMonth={setSelectedMonth}
        selectedYear={selectedYear}
        setSelectedYear={setSelectedYear}
      />

      <ExecutiveSummary analysis={analysis} mode={mode} periodLabel={periodLabel} />

      <ComparisonKPIs
        current={data.current}
        previous={data.previous}
        isLoading={isLoading}
      />

      {mode === 'month' ? (
        <MonthlyReportView data={data} analysis={analysis} isLoading={isLoading} />
      ) : (
        <YearlyReportView data={data} analysis={analysis} isLoading={isLoading} />
      )}
    </div>
    <style jsx>{`
      .reports-page {
        display: flex;
        flex-direction: column;
        gap: var(--space-5);
        padding-bottom: var(--space-10);
        min-width: 0;
        overflow-x: hidden;
      }

      .reports-page > :global(*) {
        min-width: 0;
      }

      @media (max-width: 900px) {
        .reports-page {
          gap: var(--space-4);
        }
      }
    `}</style>
    </PageTransition>
  )
}
