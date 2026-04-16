"""Dashboard aggregated response schemas — matches FE DashboardData interface."""

from app.schemas.base import CamelModel


class MonthSummary(CamelModel):
    income: float
    expense: float
    savings: float


class MonthlyChartPoint(CamelModel):
    month: str
    income: float
    expense: float


class CategoryBreakdownItem(CamelModel):
    category_id: str
    category_name: str
    category_icon: str
    category_color: str
    budget_group: str | None
    total: float


class SpendingByGroup(CamelModel):
    needs: float
    wants: float
    savings: float
    unassigned: float


class RecentTransaction(CamelModel):
    id: str
    type: str
    amount: float
    description: str
    date: str
    category_name: str
    category_icon: str
    category_color: str


class BudgetProgressItem(CamelModel):
    category_id: str
    category_name: str
    category_icon: str
    category_color: str
    budget_amount: float
    spent_amount: float


class UpcomingBill(CamelModel):
    id: str
    description: str
    amount: float
    type: str
    next_run_date: str
    frequency: str
    category_icon: str
    category_color: str


class AssetLiabilityItem(CamelModel):
    type: str
    label: str
    total: float


class AssetLiability(CamelModel):
    assets: list[AssetLiabilityItem]
    liabilities: list[AssetLiabilityItem]
    total_assets: float
    total_liabilities: float


class DashboardResponse(CamelModel):
    net_worth: float
    selected_month: str
    current_month: MonthSummary
    previous_month: MonthSummary
    monthly_chart: list[MonthlyChartPoint]
    category_breakdown: list[CategoryBreakdownItem]
    spending_by_group: SpendingByGroup
    recent_transactions: list[RecentTransaction]
    budget_progress: list[BudgetProgressItem]
    upcoming_bills: list[UpcomingBill]
    asset_liability: AssetLiability
