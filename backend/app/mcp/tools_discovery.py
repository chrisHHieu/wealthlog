"""MCP tools for schema discovery and read-only SQL queries."""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import text

from app.mcp.db import get_session

# Only allow SELECT statements — block anything that modifies data
_BLOCKED_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
    "COPY", "VACUUM", "REINDEX",
}


def _is_read_only(sql: str) -> bool:
    normalized = sql.strip().upper()
    first_word = normalized.split()[0] if normalized.split() else ""
    if first_word != "SELECT":
        return False
    for keyword in _BLOCKED_KEYWORDS:
        if keyword in normalized:
            return False
    return True


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_database_schema() -> str:
        """Khám phá cấu trúc database PostgreSQL: danh sách bảng, cột, kiểu dữ liệu.
        Dùng khi cần hiểu data model để trả lời câu hỏi phức tạp.
        Database: PostgreSQL 16."""
        async with get_session() as db:
            # Get all tables
            tables_result = await db.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            ))
            tables = [r[0] for r in tables_result.all()]

            lines = ["Database schema:"]
            for table in tables:
                cols_result = await db.execute(text(
                    "SELECT column_name, data_type, is_nullable, column_default "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = :table "
                    "ORDER BY ordinal_position"
                ), {"table": table})
                cols = cols_result.all()

                lines.append(f"\n## {table}")
                for col_name, data_type, nullable, default in cols:
                    null_str = "" if nullable == "YES" else " NOT NULL"
                    default_str = f" DEFAULT {default}" if default else ""
                    lines.append(f"  - {col_name}: {data_type}{null_str}{default_str}")

            return "\n".join(lines)

    @mcp.tool()
    async def query_database(sql: str) -> str:
        """Thực thi câu lệnh SQL read-only (chỉ SELECT) trên PostgreSQL 16.
        Dùng PostgreSQL syntax (e.g. ::type cast, EXTRACT(), TO_CHAR(), INTERVAL, CTE).
        Mặc định giới hạn 20 dòng kết quả.
        QUAN TRỌNG: Chỉ dùng khi các tool chuyên dụng không đủ thông tin.
        Gọi get_database_schema trước để biết cấu trúc bảng."""
        if not _is_read_only(sql):
            return "Lỗi: Chỉ cho phép câu lệnh SELECT (read-only)."

        # Force limit to prevent huge result sets
        normalized = sql.strip().rstrip(";")
        if "LIMIT" not in normalized.upper():
            normalized += " LIMIT 20"

        async with get_session() as db:
            try:
                result = await db.execute(text(normalized))
                rows = result.all()
                columns = list(result.keys()) if result.keys() else []

                if not rows:
                    return "Không có kết quả."

                # Format as table
                lines = [" | ".join(str(c) for c in columns)]
                lines.append("-" * len(lines[0]))
                for row in rows:
                    lines.append(" | ".join(str(v) for v in row))

                return f"Kết quả ({len(rows)} dòng):\n" + "\n".join(lines)
            except Exception as e:
                return f"Lỗi SQL: {e}"
