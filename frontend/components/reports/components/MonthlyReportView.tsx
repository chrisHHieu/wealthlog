import { ScrollReveal } from '@/components/ui/ScrollReveal'
import { ReportsData } from '@/types'
import { ReportAnalysis } from '../reportAnalysis'
import { CashFlowStatement } from './CashFlowStatement'
import { IncomeExpenseChart } from './IncomeExpenseChart'
import { PeriodComparison } from './PeriodComparison'
import { ReportActionItems } from './ReportActionItems'
import { ReportHighlights } from './ReportHighlights'
import { SpendingTrend } from './SpendingTrend'
import { TopTransactionsTable } from './TopTransactionsTable'

interface MonthlyReportViewProps {
  data: ReportsData
  analysis: ReportAnalysis
  isLoading: boolean
}

export function MonthlyReportView({ data, analysis, isLoading }: MonthlyReportViewProps) {
  return (
    <>
      <ScrollReveal>
        <div className="reports-chart-grid">
          <IncomeExpenseChart data={data.chartData} mode="month" isLoading={isLoading} />
          <SpendingTrend data={data.trendData} mode="month" isLoading={isLoading} />
        </div>
      </ScrollReveal>

      <ReportHighlights analysis={analysis} mode="month" />

      <ScrollReveal delay={0.05}>
        <PeriodComparison
          expenseByCategory={data.expenseByCategory}
          incomeByCategory={data.incomeByCategory}
          isLoading={isLoading}
        />
      </ScrollReveal>

      <ScrollReveal delay={0.1}>
        <div className="reports-detail-grid">
          <TopTransactionsTable transactions={data.topTransactions} />
          <CashFlowStatement data={data.cashFlow} isLoading={isLoading} />
        </div>
      </ScrollReveal>

      <ReportActionItems analysis={analysis} />

      <style jsx>{`
        .reports-chart-grid {
          display: grid;
          grid-template-columns: minmax(0, 3fr) minmax(360px, 2fr);
          gap: var(--space-5);
        }

        .reports-detail-grid {
          display: grid;
          grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.75fr);
          gap: var(--space-5);
          align-items: start;
        }

        @media (max-width: 1280px) {
          .reports-chart-grid,
          .reports-detail-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </>
  )
}
