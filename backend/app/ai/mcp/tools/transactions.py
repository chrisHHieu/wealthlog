"""MCP tools for transactions — search/aggregations + create/update/delete."""

from uuid import UUID

from mcp.server.fastmcp import FastMCP
from sqlalchemy import and_, func, select

from app.core.time import current_month, month_range, today
from app.database import get_session
from app.domain.balance import apply_balance, reverse_balance
from app.domain.resolvers import get_default_account, resolve_account, resolve_category
from app.models.category import Category
from app.models.transaction import Transaction

_VALID_TYPES = ("income", "expense", "transfer")
_TYPE_LABELS = {"income": "Income", "expense": "Expense", "transfer": "Transfer"}


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
        """Search transactions by date range, type (income/expense/transfer),
        category name, or keyword. Date format: YYYY-MM-DD. Default: latest 20."""
        if type is not None and type not in _VALID_TYPES:
            return f"Error: type must be one of {_VALID_TYPES}."
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
                return "No transactions found."

            lines = []
            for r in rows:
                t = _TYPE_LABELS.get(r.type, r.type)
                cat = f"{r.cat_icon} {r.cat_name}" if r.cat_name else "Uncategorized"
                desc = r.description or ""
                lines.append(f"- [{r.date}] {t}: {r.amount:,.0f} VND | {cat} | {desc}")

            if len(rows) == effective_limit:
                lines.append(
                    f"\n(Showing {effective_limit} results — narrow filters or raise limit for more.)"
                )
            return "\n".join(lines)

    @mcp.tool()
    async def get_spending_by_category(month: str | None = None, top_n: int = 10) -> str:
        """EXPENSE total per category for the month. Month format: YYYY-MM.
        Counts only type=expense. For income, use get_income_by_category.
        top_n: number of categories shown (default 10; rest grouped as 'Other')."""
        return await _category_aggregation(month, top_n, tx_type="expense", label="Expenses")

    @mcp.tool()
    async def get_income_by_category(month: str | None = None, top_n: int = 10) -> str:
        """INCOME total per category for the month. Month format: YYYY-MM.
        Counts only type=income. For expenses, use get_spending_by_category.
        top_n: number of categories shown (default 10; rest grouped as 'Other')."""
        return await _category_aggregation(month, top_n, tx_type="income", label="Income")

    @mcp.tool()
    async def create_transaction(
        type: str,
        amount: float,
        description: str = "",
        date: str | None = None,
        account_name: str | None = None,
        category_name: str | None = None,
        to_account_name: str | None = None,
        note: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Create a new transaction.
        - type: "income", "expense", or "transfer"
        - amount: VND, always positive
        - description: short description
        - date: YYYY-MM-DD (defaults to today)
        - account_name: source account (defaults to the user's default account)
        - category_name: category to associate (e.g., "Food", "Salary", "Investment")
        - to_account_name: destination account (only when type="transfer")
        - note: extra free-text note
        - tags: list of tag strings

        Example: user says "Spent 50k on lunch" →
            type="expense", amount=50000, category_name="Food"
        """
        if type not in _VALID_TYPES:
            return f"Error: type must be one of {_VALID_TYPES}."
        if amount <= 0:
            return "Error: amount must be greater than 0."

        tx_date = date or today()

        async with get_session() as db:
            if account_name:
                account_id = await resolve_account(db, account_name)
                if not account_id:
                    return f"Error: account '{account_name}' not found."
            else:
                account_id = await get_default_account(db)
                if not account_id:
                    return "Error: no accounts exist yet. Create an account first."

            category_id = None
            category_warning = ""
            if category_name:
                category_id = await resolve_category(db, category_name)
                if category_id is None:
                    category_warning = (
                        f"\nWarning: category '{category_name}' not found; "
                        f"transaction created uncategorized. "
                        f"See wealthlog://categories for available categories."
                    )

            to_account_id = None
            if type == "transfer":
                if not to_account_name:
                    return "Error: transfer requires to_account_name."
                to_account_id = await resolve_account(db, to_account_name)
                if not to_account_id:
                    return f"Error: destination account '{to_account_name}' not found."

            tx = Transaction(
                type=type,
                amount=amount,
                account_id=account_id,
                to_account_id=to_account_id,
                category_id=category_id,
                description=description,
                note=note,
                tags=tags,
                date=tx_date,
            )
            db.add(tx)
            await db.flush()
            await apply_balance(db, type, amount, account_id, to_account_id)

            cat_info = f" | {category_name}" if category_name else ""
            return (
                f"Created: {_TYPE_LABELS[type]} {amount:,.0f} VND{cat_info}\n"
                f"Date: {tx_date} | {description}\n"
                f"ID: {tx.id}"
                f"{category_warning}"
            )

    @mcp.tool()
    async def create_multiple_transactions(
        transactions: list[dict],
    ) -> str:
        """Create multiple transactions atomically (all or nothing).
        Each item is a dict with:
        - type: "income" | "expense" | "transfer" (required)
        - amount: VND amount (required)
        - description: short description
        - date: YYYY-MM-DD (defaults to today)
        - account_name: source account
        - category_name: category to associate
        - to_account_name: destination account (for transfer)
        - note: free-text note

        If ANY item fails validation → nothing is created; the error list is
        returned so the agent can fix and retry. This avoids partial commits
        that would corrupt account balances.

        Example user input:
        "Salary 20M, food spending 5M, savings deposit 10M"
        → transactions=[
            {"type":"income","amount":20000000,"description":"Salary","category_name":"Salary"},
            {"type":"expense","amount":5000000,"description":"Food","category_name":"Food"},
            {"type":"transfer","amount":10000000,"description":"Savings deposit",
             "account_name":"Bank","to_account_name":"Savings"}
        ]
        """
        if not transactions:
            return "Error: empty transaction list."

        async with get_session() as db:
            default_account_id = await get_default_account(db)

            # ── Pass 1: validate + resolve IDs (no writes) ────────────────
            prepared: list[dict] = []
            errors: list[str] = []
            warnings: list[str] = []

            for i, item in enumerate(transactions, 1):
                tx_type = item.get("type")
                amount = item.get("amount", 0)

                if tx_type not in _VALID_TYPES:
                    errors.append(f"{i}. invalid type '{tx_type}'")
                    continue
                if not isinstance(amount, (int, float)) or amount <= 0:
                    errors.append(f"{i}. amount must be > 0")
                    continue

                acc_name = item.get("account_name")
                if acc_name:
                    account_id = await resolve_account(db, acc_name)
                    if not account_id:
                        errors.append(f"{i}. account '{acc_name}' not found")
                        continue
                else:
                    account_id = default_account_id
                    if not account_id:
                        errors.append(f"{i}. no accounts exist yet")
                        continue

                category_id = None
                cat_name = item.get("category_name")
                if cat_name:
                    category_id = await resolve_category(db, cat_name)
                    if category_id is None:
                        warnings.append(
                            f"{i}. category '{cat_name}' not found (created uncategorized)"
                        )

                to_account_id = None
                if tx_type == "transfer":
                    to_acc_name = item.get("to_account_name")
                    if not to_acc_name:
                        errors.append(f"{i}. transfer requires to_account_name")
                        continue
                    to_account_id = await resolve_account(db, to_acc_name)
                    if not to_account_id:
                        errors.append(f"{i}. destination account '{to_acc_name}' not found")
                        continue

                prepared.append({
                    "idx": i,
                    "type": tx_type,
                    "amount": amount,
                    "account_id": account_id,
                    "to_account_id": to_account_id,
                    "category_id": category_id,
                    "description": item.get("description", ""),
                    "note": item.get("note"),
                    "tags": item.get("tags"),
                    "date": item.get("date") or today(),
                })

            if errors:
                # Raise to rollback the session — no writes happened yet, but be explicit.
                raise ValueError(
                    f"Failed to create {len(errors)}/{len(transactions)} transactions. "
                    f"Fix and retry:\n" + "\n".join(f"- {e}" for e in errors)
                )

            # ── Pass 2: write all (pre-validated, safe) ──────────────────
            results = []
            for p in prepared:
                tx = Transaction(
                    type=p["type"],
                    amount=p["amount"],
                    account_id=p["account_id"],
                    to_account_id=p["to_account_id"],
                    category_id=p["category_id"],
                    description=p["description"],
                    note=p["note"],
                    tags=p["tags"],
                    date=p["date"],
                )
                db.add(tx)
                await db.flush()
                await apply_balance(
                    db, p["type"], p["amount"], p["account_id"], p["to_account_id"],
                )
                results.append(
                    f"{p['idx']}. ✓ {_TYPE_LABELS[p['type']]} {p['amount']:,.0f} VND"
                    f" | {p['description']}"
                )

            out = f"Created {len(prepared)} transactions:\n" + "\n".join(results)
            if warnings:
                out += "\n\nWarnings:\n" + "\n".join(f"- {w}" for w in warnings)
            return out

    @mcp.tool()
    async def update_transaction(
        transaction_id: str,
        type: str | None = None,
        amount: float | None = None,
        description: str | None = None,
        date: str | None = None,
        account_name: str | None = None,
        category_name: str | None = None,
        to_account_name: str | None = None,
        note: str | None = None,
    ) -> str:
        """Update a transaction by ID. Pass only the fields you want to change.
        - transaction_id: UUID of the transaction
        - Other fields: same as create_transaction; only pass what changes.
        """
        try:
            tx_uuid = UUID(transaction_id)
        except ValueError:
            return "Error: transaction_id is not a valid UUID."

        async with get_session() as db:
            tx = await db.get(Transaction, tx_uuid)
            if not tx:
                return f"Error: transaction {transaction_id} not found."

            # Validate + resolve everything BEFORE touching balance — otherwise
            # a failed validation after reverse_balance leaves the account
            # balance out of sync with the (still-existing) transaction.
            if type is not None and type not in _VALID_TYPES:
                return f"Error: type must be one of {_VALID_TYPES}."
            if amount is not None and amount <= 0:
                return "Error: amount must be > 0."

            new_account_id = None
            if account_name is not None:
                new_account_id = await resolve_account(db, account_name)
                if not new_account_id:
                    return f"Error: account '{account_name}' not found."

            new_to_account_id = None
            if to_account_name is not None:
                new_to_account_id = await resolve_account(db, to_account_name)
                if not new_to_account_id:
                    return f"Error: destination account '{to_account_name}' not found."

            new_category_id = None
            category_warning = ""
            if category_name is not None:
                new_category_id = await resolve_category(db, category_name)
                if new_category_id is None:
                    category_warning = (
                        f"\nWarning: category '{category_name}' not found; "
                        f"transaction is now uncategorized."
                    )

            # All inputs validated — safe to modify balance.
            old_type = tx.type.value if hasattr(tx.type, "value") else tx.type
            await reverse_balance(
                db, old_type, tx.amount, tx.account_id, tx.to_account_id,
            )

            if type is not None:
                tx.type = type
            if amount is not None:
                tx.amount = amount
            if description is not None:
                tx.description = description
            if date is not None:
                tx.date = date
            if note is not None:
                tx.note = note
            if account_name is not None:
                tx.account_id = new_account_id
            if category_name is not None:
                tx.category_id = new_category_id
            if to_account_name is not None:
                tx.to_account_id = new_to_account_id

            await db.flush()

            new_type = tx.type.value if hasattr(tx.type, "value") else tx.type
            await apply_balance(db, new_type, tx.amount, tx.account_id, tx.to_account_id)

            return f"Updated transaction {transaction_id}.{category_warning}"

    @mcp.tool()
    async def delete_transaction(transaction_id: str) -> str:
        """Delete a transaction by ID. Affected account balances are
        automatically restored.
        - transaction_id: UUID of the transaction.
        """
        try:
            tx_uuid = UUID(transaction_id)
        except ValueError:
            return "Error: transaction_id is not a valid UUID."

        async with get_session() as db:
            tx = await db.get(Transaction, tx_uuid)
            if not tx:
                return f"Error: transaction {transaction_id} not found."

            tx_type = tx.type.value if hasattr(tx.type, "value") else tx.type
            await reverse_balance(db, tx_type, tx.amount, tx.account_id, tx.to_account_id)
            await db.delete(tx)
            await db.flush()

            return f"Deleted transaction {transaction_id}. Account balance restored."


async def _category_aggregation(
    month: str | None,
    top_n: int,
    tx_type: str,
    label: str,
) -> str:
    """Shared body for spending-by-category and income-by-category."""
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
                        Transaction.type == tx_type,
                        Transaction.date >= start,
                        Transaction.date <= end,
                    )
                )
                .group_by(Category.name, Category.icon)
                .order_by(func.sum(Transaction.amount).desc())
            )
        ).all()

        if not rows:
            return f"Month {m}: no {tx_type} recorded."

        total = sum(r.total for r in rows)
        lines = [f"{label} for {m} (total: {total:,.0f} VND):"]
        shown = rows[:top_n]
        rest = rows[top_n:]
        for r in shown:
            name = r.name or "Uncategorized"
            icon = r.icon or "📦"
            pct = round((r.total / total) * 100, 1) if total > 0 else 0
            lines.append(f"- {icon} {name}: {r.total:,.0f} VND ({pct}%)")
        if rest:
            rest_total = sum(r.total for r in rest)
            rest_pct = round((rest_total / total) * 100, 1) if total > 0 else 0
            lines.append(
                f"- 📦 Other ({len(rest)} categories): {rest_total:,.0f} VND ({rest_pct}%)"
            )
        return "\n".join(lines)
