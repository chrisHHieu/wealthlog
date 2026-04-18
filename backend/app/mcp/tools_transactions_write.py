"""MCP tools for transactions (create, update, delete)."""

from uuid import UUID

from mcp.server.fastmcp import FastMCP

from app.mcp._helpers import (
    apply_balance,
    get_default_account,
    resolve_account,
    resolve_category,
    reverse_balance,
    today,
)
from app.mcp.db import get_session
from app.models.transaction import Transaction


def register(mcp: FastMCP) -> None:
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
        """Tạo giao dịch mới.
        - type: "income", "expense", hoặc "transfer"
        - amount: số tiền (VND, luôn dương)
        - description: mô tả giao dịch
        - date: ngày giao dịch YYYY-MM-DD (mặc định hôm nay)
        - account_name: tên tài khoản (nếu không truyền sẽ dùng tài khoản mặc định)
        - category_name: tên danh mục (ví dụ: "Ăn uống", "Lương", "Đầu tư")
        - to_account_name: tên tài khoản đích (chỉ dùng khi type="transfer")
        - note: ghi chú thêm
        - tags: danh sách tag

        Ví dụ: user nói "Chi ăn cơm 50k" → type="expense", amount=50000, category_name="Ăn uống"
        """
        if type not in ("income", "expense", "transfer"):
            return "Lỗi: type phải là income, expense, hoặc transfer."
        if amount <= 0:
            return "Lỗi: amount phải lớn hơn 0."

        tx_date = date or today()

        async with get_session() as db:
            account_id = None
            if account_name:
                account_id = await resolve_account(db, account_name)
                if not account_id:
                    return f"Lỗi: Không tìm thấy tài khoản '{account_name}'."
            else:
                account_id = await get_default_account(db)
                if not account_id:
                    return "Lỗi: Chưa có tài khoản nào. Hãy tạo tài khoản trước."

            category_id = None
            if category_name:
                category_id = await resolve_category(db, category_name)

            to_account_id = None
            if type == "transfer":
                if not to_account_name:
                    return "Lỗi: Chuyển khoản cần có to_account_name."
                to_account_id = await resolve_account(db, to_account_name)
                if not to_account_id:
                    return f"Lỗi: Không tìm thấy tài khoản đích '{to_account_name}'."

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

            type_labels = {"income": "Thu", "expense": "Chi", "transfer": "Chuyển"}
            cat_info = f" | {category_name}" if category_name else ""
            return (
                f"Đã tạo giao dịch: {type_labels[type]} {amount:,.0f} VND{cat_info}\n"
                f"Ngày: {tx_date} | {description}\n"
                f"ID: {tx.id}"
            )

    @mcp.tool()
    async def create_multiple_transactions(
        transactions: list[dict],
    ) -> str:
        """Tạo nhiều giao dịch cùng lúc (batch).
        Mỗi item trong danh sách là dict với các trường:
        - type: "income" | "expense" | "transfer" (bắt buộc)
        - amount: số tiền VND (bắt buộc)
        - description: mô tả
        - date: YYYY-MM-DD (mặc định hôm nay)
        - account_name: tên tài khoản
        - category_name: tên danh mục
        - to_account_name: tên tài khoản đích (cho transfer)
        - note: ghi chú

        Ví dụ user nói:
        "Lương 20tr, chi ăn uống 5tr, gửi tiết kiệm 10tr"
        → transactions=[
            {"type":"income","amount":20000000,"description":"Lương","category_name":"Lương"},
            {"type":"expense","amount":5000000,"description":"Ăn uống","category_name":"Ăn uống"},
            {"type":"transfer","amount":10000000,"description":"Gửi tiết kiệm",
             "account_name":"Ngân hàng","to_account_name":"Tiết kiệm"}
        ]
        """
        if not transactions:
            return "Lỗi: Danh sách giao dịch trống."

        results = []
        async with get_session() as db:
            default_account_id = await get_default_account(db)

            for i, item in enumerate(transactions, 1):
                tx_type = item.get("type")
                amount = item.get("amount", 0)

                if tx_type not in ("income", "expense", "transfer"):
                    results.append(f"{i}. Lỗi: type không hợp lệ '{tx_type}'")
                    continue
                if amount <= 0:
                    results.append(f"{i}. Lỗi: amount phải > 0")
                    continue

                account_id = None
                acc_name = item.get("account_name")
                if acc_name:
                    account_id = await resolve_account(db, acc_name)
                    if not account_id:
                        results.append(f"{i}. Lỗi: Không tìm thấy tài khoản '{acc_name}'")
                        continue
                else:
                    account_id = default_account_id
                    if not account_id:
                        results.append(f"{i}. Lỗi: Chưa có tài khoản nào")
                        continue

                category_id = None
                cat_name = item.get("category_name")
                if cat_name:
                    category_id = await resolve_category(db, cat_name)

                to_account_id = None
                if tx_type == "transfer":
                    to_acc_name = item.get("to_account_name")
                    if not to_acc_name:
                        results.append(f"{i}. Lỗi: transfer cần to_account_name")
                        continue
                    to_account_id = await resolve_account(db, to_acc_name)
                    if not to_account_id:
                        results.append(
                            f"{i}. Lỗi: Không tìm thấy tài khoản đích '{to_acc_name}'"
                        )
                        continue

                tx = Transaction(
                    type=tx_type,
                    amount=amount,
                    account_id=account_id,
                    to_account_id=to_account_id,
                    category_id=category_id,
                    description=item.get("description", ""),
                    note=item.get("note"),
                    tags=item.get("tags"),
                    date=item.get("date") or today(),
                )
                db.add(tx)
                await db.flush()
                await apply_balance(db, tx_type, amount, account_id, to_account_id)

                type_labels = {"income": "Thu", "expense": "Chi", "transfer": "Chuyển"}
                results.append(
                    f"{i}. ✓ {type_labels[tx_type]} {amount:,.0f} VND"
                    f" | {item.get('description', '')}"
                )

        return f"Kết quả tạo {len(transactions)} giao dịch:\n" + "\n".join(results)

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
        """Sửa giao dịch theo ID. Chỉ truyền các trường cần thay đổi.
        - transaction_id: ID giao dịch (UUID)
        - Các trường khác giống create_transaction, chỉ truyền field muốn sửa
        """
        try:
            tx_uuid = UUID(transaction_id)
        except ValueError:
            return "Lỗi: transaction_id không hợp lệ."

        async with get_session() as db:
            tx = await db.get(Transaction, tx_uuid)
            if not tx:
                return f"Lỗi: Không tìm thấy giao dịch ID {transaction_id}."

            await reverse_balance(
                db, tx.type.value if hasattr(tx.type, "value") else tx.type,
                tx.amount, tx.account_id, tx.to_account_id,
            )

            if type is not None:
                if type not in ("income", "expense", "transfer"):
                    return "Lỗi: type phải là income, expense, hoặc transfer."
                tx.type = type
            if amount is not None:
                if amount <= 0:
                    return "Lỗi: amount phải > 0."
                tx.amount = amount
            if description is not None:
                tx.description = description
            if date is not None:
                tx.date = date
            if note is not None:
                tx.note = note
            if account_name is not None:
                acc_id = await resolve_account(db, account_name)
                if not acc_id:
                    return f"Lỗi: Không tìm thấy tài khoản '{account_name}'."
                tx.account_id = acc_id
            if category_name is not None:
                tx.category_id = await resolve_category(db, category_name)
            if to_account_name is not None:
                to_id = await resolve_account(db, to_account_name)
                if not to_id:
                    return f"Lỗi: Không tìm thấy tài khoản đích '{to_account_name}'."
                tx.to_account_id = to_id

            await db.flush()

            tx_type = tx.type.value if hasattr(tx.type, "value") else tx.type
            await apply_balance(db, tx_type, tx.amount, tx.account_id, tx.to_account_id)

            return f"Đã cập nhật giao dịch {transaction_id}."

    @mcp.tool()
    async def delete_transaction(transaction_id: str) -> str:
        """Xóa giao dịch theo ID. Số dư tài khoản sẽ được hoàn lại tự động.
        - transaction_id: ID giao dịch (UUID)
        """
        try:
            tx_uuid = UUID(transaction_id)
        except ValueError:
            return "Lỗi: transaction_id không hợp lệ."

        async with get_session() as db:
            tx = await db.get(Transaction, tx_uuid)
            if not tx:
                return f"Lỗi: Không tìm thấy giao dịch ID {transaction_id}."

            tx_type = tx.type.value if hasattr(tx.type, "value") else tx.type
            await reverse_balance(db, tx_type, tx.amount, tx.account_id, tx.to_account_id)
            await db.delete(tx)
            await db.flush()

            return f"Đã xóa giao dịch {transaction_id}. Số dư tài khoản đã được hoàn lại."
