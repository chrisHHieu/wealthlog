"""Reports aggregated response schemas — matches FE ReportsData interface."""

from app.schemas.base import CamelModel


class PeriodSummary(CamelModel):
    income: float
    expense: float
    savings: float
    savings_rate: float


class CategoryComparison(CamelModel):
    category_id: str
    name: str
    icon: str
    color: str
    current: float
    previous: float
    pct: float


class ChartPoint(CamelModel):
    label: str
    income: float
    expense: float


class TrendPoint(CamelModel):
    label: str
    cum_expense: float
    expense: float


class CashFlowData(CamelModel):
    income_items: list[CategoryComparison]
    expense_items: list[CategoryComparison]
    total_income: float
    total_expense: float
    net: float


class TopTransaction(CamelModel):
    type: str
    amount: float
    date: str
    category_name: str
    category_icon: str
    category_color: str


class ReportsResponse(CamelModel):
    current: PeriodSummary
    previous: PeriodSummary
    chart_data: list[ChartPoint]
    trend_data: list[TrendPoint]
    expense_by_category: list[CategoryComparison]
    income_by_category: list[CategoryComparison]
    cash_flow: CashFlowData
    top_transactions: list[TopTransaction]
