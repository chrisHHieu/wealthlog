"""MCP tools for transactions (read-only queries)."""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import and_, func, select

from app.mcp._helpers import current_month, month_range
from app.mcp.db import get_session
from app.models.category import Category
from app.models.transaction import Transaction

_VALID_TYPES = ("income", "expense", "transfer")


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def search_transactions(
        start_date: str | None = None,
        end_date: str | None = None,
        type: str | None = None,
        category_name: str | None = None,
        keyword: str | None = None,
        limit: int = 20,
    ) -> str:
        """Tìm kiếm giao dịch theo ngày, loại (income/expense/transfer), tên danh mục, từ khóa.
        Ngày theo format YYYY-MM-DD. Mặc định trả về 20 giao dịch gần nhất."""
        if type is not None and type not in _VALID_TYPES:
            return f"Lỗi: type phải là một trong {_VALID_TYPES}."
        async with get_session() as db:
            stmt = (
                select(
                    Transaction.type,
                    Transaction.amount,
                    Transaction.description,
                    Transaction.date,
                    Category.name.label("cat_name"),
                    Category.icon.label("cat_icon"),
                )
                .outerjoin(Category, Transaction.category_id == Category.id)
            )
            conditions = []
            if start_date:
                conditions.append(Transaction.date >= start_date)
            if end_date:
                conditions.append(Transaction.date <= end_date)
            if type:
                conditions.append(Transaction.type == type)
            if category_name:
                conditions.append(Category.name.ilike(f"%{category_name}%"))
            if keyword:
                conditions.append(Transaction.description.ilike(f"%{keyword}%"))
            if conditions:
                stmt = stmt.where(and_(*conditions))

            effective_limit = min(limit, 50)
            stmt = stmt.order_by(Transaction.date.desc()).limit(effective_limit)
            rows = (await db.execute(stmt)).all()

            if not rows:
                return "Không tìm thấy giao dịch nào."

            type_labels = {"income": "Thu", "expense": "Chi", "transfer": "Chuyển"}
            lines = []
            for r in rows:
                t = type_labels.get(r.type, r.type)
                cat = f"{r.cat_icon} {r.cat_name}" if r.cat_name else "Không phân loại"
                desc = r.description or ""
                lines.append(f"- [{r.date}] {t}: {r.amount:,.0f} VND | {cat} | {desc}")

            if len(rows) == effective_limit:
                lines.append(f"\n(Hiển thị {effective_limit} kết quả, có thể còn thêm — thu hẹp điều kiện hoặc tăng limit)")
            return "\n".join(lines)

    @mcp.tool()
    async def get_spending_by_category(month: str | None = None, top_n: int = 10) -> str:
        """CHI TIÊU (expense) theo từng danh mục trong tháng. Format tháng: YYYY-MM.
        Chỉ tính giao dịch type=expense. Muốn xem thu nhập → dùng get_income_by_category.
        top_n: số danh mục hiển thị (mặc định 10, còn lại gộp vào 'Khác')."""
        m = month or current_month()
        start, end = month_range(m)
        async with get_session() as db:
            rows = (
                await db.execute(
                    select(
                        Category.name,
                        Category.icon,
                        func.sum(Transaction.amount).label("total"),
                    )
                    .outerjoin(Category, Transaction.category_id == Category.id)
                    .where(
                        and_(
                            Transaction.type == "expense",
                            Transaction.date >= start,
                            Transaction.date <= end,
                        )
                    )
                    .group_by(Category.name, Category.icon)
                    .order_by(func.sum(Transaction.amount).desc())
                )
            ).all()

            if not rows:
                return f"Tháng {m}: Không có chi tiêu."

            total_expense = sum(r.total for r in rows)
            lines = [f"Chi tiêu tháng {m} (tổng: {total_expense:,.0f} VND):"]
            shown = rows[:top_n]
            rest = rows[top_n:]
            for r in shown:
                name = r.name or "Khác"
                icon = r.icon or "📦"
                pct = round((r.total / total_expense) * 100, 1) if total_expense > 0 else 0
                lines.append(f"- {icon} {name}: {r.total:,.0f} VND ({pct}%)")
            if rest:
                rest_total = sum(r.total for r in rest)
                rest_pct = round((rest_total / total_expense) * 100, 1) if total_expense > 0 else 0
                lines.append(f"- 📦 Khác ({len(rest)} danh mục): {rest_total:,.0f} VND ({rest_pct}%)")
            return "\n".join(lines)

    @mcp.tool()
    async def get_income_by_category(month: str | None = None, top_n: int = 10) -> str:
        """THU NHẬP (income) theo từng danh mục trong tháng. Format tháng: YYYY-MM.
        Chỉ tính giao dịch type=income. Muốn xem chi tiêu → dùng get_spending_by_category.
        top_n: số danh mục hiển thị (mặc định 10, còn lại gộp vào 'Khác')."""
        m = month or current_month()
        start, end = month_range(m)
        async with get_session() as db:
            rows = (
                await db.execute(
                    select(
                        Category.name,
                        Category.icon,
                        func.sum(Transaction.amount).label("total"),
                    )
                    .outerjoin(Category, Transaction.category_id == Category.id)
                    .where(
                        and_(
                            Transaction.type == "income",
                            Transaction.date >= start,
                            Transaction.date <= end,
                        )
                    )
                    .group_by(Category.name, Category.icon)
                    .order_by(func.sum(Transaction.amount).desc())
                )
            ).all()

            if not rows:
                return f"Tháng {m}: Không có thu nhập."

            total = sum(r.total for r in rows)
            lines = [f"Thu nhập tháng {m} (tổng: {total:,.0f} VND):"]
            shown = rows[:top_n]
            rest = rows[top_n:]
            for r in shown:
                name = r.name or "Khác"
                icon = r.icon or "📦"
                pct = round((r.total / total) * 100, 1) if total > 0 else 0
                lines.append(f"- {icon} {name}: {r.total:,.0f} VND ({pct}%)")
            if rest:
                rest_total = sum(r.total for r in rest)
                rest_pct = round((rest_total / total) * 100, 1) if total > 0 else 0
                lines.append(f"- 📦 Khác ({len(rest)} danh mục): {rest_total:,.0f} VND ({rest_pct}%)")
            return "\n".join(lines)
