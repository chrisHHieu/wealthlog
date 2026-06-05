'use client'

import { useDashboard } from '@/hooks/useDashboard'
import { KPICards } from './components/KPICards'
import { CashFlowChart } from './components/CashFlowChart'
import { SpendingBreakdown } from './components/SpendingBreakdown'
import { BudgetProgress } from './components/BudgetProgress'
import { GoalsSnapshot } from './components/GoalsSnapshot'
import { UpcomingBills } from './components/UpcomingBills'
import { RecentTransactions } from './components/RecentTransactions'
import { AssetLiability } from './components/AssetLiability'
import { DashboardSummary } from './components/DashboardSummary'
import { DashboardActionCenter } from './components/DashboardActionCenter'
import { PageTransition, StaggerItem } from '@/components/ui/PageTransition'
import { ScrollReveal } from '@/components/ui/ScrollReveal'
import { buildDashboardInsights } from './dashboardInsights'

function getCurrentMonthStr() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

export function Dashboard() {
  const selectedMonth = getCurrentMonthStr()
  const { data, isLoading, activeGoals, stats } = useDashboard('12months', selectedMonth)
  const insights = buildDashboardInsights(data)

  return (
    <PageTransition>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)', paddingBottom: 'var(--space-10)' }}>
        {/* Row 1: KPI Cards - Hero Net Worth + 3 smaller cards */}
        <StaggerItem>
          <KPICards
            data={data}
            isLoading={isLoading}
            incomePct={stats.incomePct}
            expensePct={stats.expensePct}
          />
        </StaggerItem>

        <ScrollReveal>
          <div className="dashboard-summary-row">
            <DashboardSummary data={data} insights={insights} isLoading={isLoading} />
            <DashboardActionCenter insights={insights} isLoading={isLoading} />
          </div>
        </ScrollReveal>

        {/* Row 2: Cash Flow (3fr) + Spending Donut (2fr) */}
        <ScrollReveal>
          <div className="dashboard-row-2">
            <CashFlowChart data={data} isLoading={isLoading} />
            <SpendingBreakdown data={data} isLoading={isLoading} />
          </div>
        </ScrollReveal>

        {/* Row 3: Budget + Goals + Upcoming Bills */}
        <ScrollReveal delay={0.05}>
          <div className="dashboard-row-3">
            <BudgetProgress data={data} isLoading={isLoading} />
            <GoalsSnapshot goals={activeGoals} isLoading={isLoading} />
            <UpcomingBills data={data} isLoading={isLoading} />
          </div>
        </ScrollReveal>

        {/* Row 4: Recent Transactions (3fr) + Asset & Liability (2fr) */}
        <ScrollReveal delay={0.1}>
          <div className="dashboard-row-2">
            <RecentTransactions data={data} isLoading={isLoading} />
            <AssetLiability data={data} isLoading={isLoading} />
          </div>
        </ScrollReveal>
      </div>

      <style jsx>{`
        .dashboard-row-2 {
          display: grid;
          grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
          gap: var(--space-5);
        }
        .dashboard-row-3 {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: var(--space-5);
        }
        .dashboard-summary-row {
          display: grid;
          grid-template-columns: minmax(0, 1.6fr) minmax(320px, 0.7fr);
          gap: var(--space-5);
        }
        @media (max-width: 1280px) {
          .dashboard-row-2 {
            grid-template-columns: 1fr;
          }
          .dashboard-summary-row {
            grid-template-columns: 1fr;
          }
          .dashboard-row-3 {
            grid-template-columns: 1fr 1fr;
          }
          .dashboard-row-3 > :last-child {
            grid-column: span 2;
          }
        }
        @media (max-width: 639px) {
          .dashboard-row-3 {
            grid-template-columns: 1fr;
          }
          .dashboard-row-3 > :last-child {
            grid-column: span 1;
          }
        }
      `}</style>
    </PageTransition>
  )
}
