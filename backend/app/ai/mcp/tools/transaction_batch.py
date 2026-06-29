"""Batch update/delete MCP tools — one confirmation card for a bulk change.

Without these, recategorizing N transactions means N single-tool calls and N
confirmation cards (approval fatigue). These run the whole batch atomically so
the user reviews and confirms once.
"""

from uuid import UUID

from mcp.server.fastmcp import FastMCP

from app.ai.mcp.tools.transaction_constants import VALID_TYPES as _VALID_TYPES
from app.database import get_session
from app.domain.balance import apply_balance, reverse_balance
from app.domain.resolvers import resolve_account, resolve_category
from app.models.transaction import Transaction


def register_batch_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    async def update_multiple_transactions(updates: list[dict]) -> str:
        """Update several transactions atomically (all or nothing).

        Prefer this over calling update_transaction in a loop — it produces ONE
        confirmation card for the whole batch instead of one per transaction.

        Each item is a dict with:
        - transaction_id: UUID (required)
        - type / amount / description / date / account_name / category_name /
          to_account_name / note: only the fields to change (same as
          update_transaction)

        If ANY item fails validation, nothing is changed; the error list is
        returned so you can fix and retry.
        """
        if not updates:
            raise ValueError("empty update list.")

        async with get_session() as db:
            # ── Pass 1: validate + resolve (no writes) ───────────────────────
            prepared: list[dict] = []
            errors: list[str] = []
            warnings: list[str] = []

            for i, item in enumerate(updates, 1):
                tid = item.get("transaction_id")
                try:
                    tx_uuid = UUID(str(tid))
                except (ValueError, TypeError):
                    errors.append(f"{i}. invalid transaction_id '{tid}'")
                    continue
                tx = await db.get(Transaction, tx_uuid)
                if tx is None:
                    errors.append(f"{i}. transaction {tid} not found")
                    continue

                type_ = item.get("type")
                if type_ is not None and type_ not in _VALID_TYPES:
                    errors.append(f"{i}. invalid type '{type_}'")
                    continue
                amount = item.get("amount")
                if amount is not None and (not isinstance(amount, (int, float)) or amount <= 0):
                    errors.append(f"{i}. amount must be > 0")
                    continue

                account_id = None
                if item.get("account_name") is not None:
                    account_id = await resolve_account(db, item["account_name"])
                    if not account_id:
                        errors.append(f"{i}. account '{item['account_name']}' not found")
                        continue

                to_account_id = None
                if item.get("to_account_name") is not None:
                    to_account_id = await resolve_account(db, item["to_account_name"])
                    if not to_account_id:
                        errors.append(f"{i}. destination account '{item['to_account_name']}' not found")
                        continue

                category_id = None
                if item.get("category_name") is not None:
                    category_id = await resolve_category(db, item["category_name"])
                    if category_id is None:
                        warnings.append(
                            f"{i}. category '{item['category_name']}' not found (left uncategorized)"
                        )

                prepared.append({
                    "tx": tx,
                    "item": item,
                    "account_id": account_id,
                    "to_account_id": to_account_id,
                    "category_id": category_id,
                })

            if errors:
                raise ValueError(
                    f"Failed to update {len(errors)}/{len(updates)} transactions. "
                    "Fix and retry:\n" + "\n".join(f"- {e}" for e in errors)
                )

            # ── Pass 2: apply (reverse old balance → set fields → re-apply) ───
            for p in prepared:
                tx, item = p["tx"], p["item"]
                old_type = tx.type.value if hasattr(tx.type, "value") else tx.type
                await reverse_balance(db, old_type, tx.amount, tx.account_id, tx.to_account_id)

                if item.get("type") is not None:
                    tx.type = item["type"]
                if item.get("amount") is not None:
                    tx.amount = item["amount"]
                if item.get("description") is not None:
                    tx.description = item["description"]
                if item.get("date") is not None:
                    tx.date = item["date"]
                if item.get("note") is not None:
                    tx.note = item["note"]
                if item.get("account_name") is not None:
                    tx.account_id = p["account_id"]
                if item.get("category_name") is not None:
                    tx.category_id = p["category_id"]
                if item.get("to_account_name") is not None:
                    tx.to_account_id = p["to_account_id"]

                await db.flush()
                new_type = tx.type.value if hasattr(tx.type, "value") else tx.type
                await apply_balance(db, new_type, tx.amount, tx.account_id, tx.to_account_id)

            out = f"Updated {len(prepared)} transactions."
            if warnings:
                out += "\n\nWarnings:\n" + "\n".join(f"- {w}" for w in warnings)
            return out

    @mcp.tool()
    async def delete_multiple_transactions(transaction_ids: list[str]) -> str:
        """Delete several transactions atomically (all or nothing). Balances restored.

        Prefer this over calling delete_transaction in a loop — it produces ONE
        confirmation card. If ANY id is invalid or missing, nothing is deleted.
        """
        if not transaction_ids:
            raise ValueError("empty transaction id list.")

        async with get_session() as db:
            txs: list[Transaction] = []
            errors: list[str] = []
            for i, tid in enumerate(transaction_ids, 1):
                try:
                    tx_uuid = UUID(str(tid))
                except (ValueError, TypeError):
                    errors.append(f"{i}. invalid transaction_id '{tid}'")
                    continue
                tx = await db.get(Transaction, tx_uuid)
                if tx is None:
                    errors.append(f"{i}. transaction {tid} not found")
                    continue
                txs.append(tx)

            if errors:
                raise ValueError(
                    f"Failed to delete {len(errors)}/{len(transaction_ids)} transactions. "
                    "Fix and retry:\n" + "\n".join(f"- {e}" for e in errors)
                )

            for tx in txs:
                tx_type = tx.type.value if hasattr(tx.type, "value") else tx.type
                await reverse_balance(db, tx_type, tx.amount, tx.account_id, tx.to_account_id)
                await db.delete(tx)
            await db.flush()

            return f"Deleted {len(txs)} transactions. Account balances restored."
