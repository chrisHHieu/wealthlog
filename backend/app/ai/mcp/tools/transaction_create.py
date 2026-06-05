"""Create MCP tools for transactions."""

from mcp.server.fastmcp import FastMCP

from app.ai.mcp.tools.transaction_constants import TYPE_LABELS as _TYPE_LABELS
from app.ai.mcp.tools.transaction_constants import VALID_TYPES as _VALID_TYPES
from app.core.time import today
from app.database import get_session
from app.domain.balance import apply_balance
from app.domain.resolvers import get_default_account, resolve_account, resolve_category
from app.models.transaction import Transaction


def register_create_tools(mcp: FastMCP) -> None:
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

        BEFORE calling: confirm with the user that you have all three:
        1. description — what is this transaction for?
        2. category_name — which category? (check wealthlog://categories for exact names)
        3. account_name — which wallet/account? (ask if user has multiple and didn't specify)
        Do NOT guess these — ask the user if any is unclear.

        Parameters:
        - type: "income", "expense", or "transfer"
        - amount: VND, always positive
        - description: short label for the transaction
        - date: YYYY-MM-DD (defaults to today)
        - account_name: source account (auto-use if only one exists)
        - category_name: must match an existing category name exactly
        - to_account_name: destination account (only for type="transfer")
        - note: extra free-text note
        - tags: list of tag strings

        Example: user says "Spent 50k on lunch" →
            type="expense", amount=50000, description="Lunch", category_name="Food"
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

    async def create_multiple_transactions(
        transactions: list[dict],
    ) -> str:
        """Create multiple transactions atomically (all or nothing).

        BEFORE calling: for each transaction confirm you have:
        1. description — what is each transaction for?
        2. category_name — check wealthlog://categories for exact names
        3. account_name — which wallet? (ask if multiple accounts and not specified)
        Do NOT guess — ask the user if any item is unclear.

        Each item is a dict with:
        - type: "income" | "expense" | "transfer" (required)
        - amount: VND amount (required)
        - description: short label
        - date: YYYY-MM-DD (defaults to today)
        - account_name: source account
        - category_name: must match an existing category name
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
