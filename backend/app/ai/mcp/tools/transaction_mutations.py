"""Update and delete MCP tools for transactions."""

from uuid import UUID

from mcp.server.fastmcp import FastMCP

from app.ai.mcp.tools.transaction_constants import VALID_TYPES as _VALID_TYPES
from app.database import get_session
from app.domain.balance import apply_balance, reverse_balance
from app.domain.resolvers import resolve_account, resolve_category
from app.models.transaction import Transaction


def register_mutation_tools(mcp: FastMCP) -> None:
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
