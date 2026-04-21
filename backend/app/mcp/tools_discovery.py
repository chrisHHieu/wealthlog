"""MCP tools for schema discovery and read-only SQL queries."""

import re

from mcp.server.fastmcp import FastMCP
from sqlalchemy import text

from app.mcp.db import get_session

# Only allow SELECT statements — block anything that modifies data
_BLOCKED_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
    "COPY", "VACUUM", "REINDEX",
}

# Column-name patterns whose values are safe to expose as samples
# (non-sensitive lookup-style columns). UUID / timestamp / numeric types
# are excluded by the data_type check in _should_sample.
_SAMPLE_PATTERNS = ("type", "status", "kind", "category", "state", "role")


def _should_sample(col_name: str, data_type: str) -> bool:
    if data_type not in ("character varying", "text"):
        return False
    name = col_name.lower()
    for pat in _SAMPLE_PATTERNS:
        if name == pat or name.endswith(f"_{pat}") or name.startswith(f"{pat}_"):
            return True
    return False


_COMMENT_LINE_RE = re.compile(r"--[^\n]*")
_COMMENT_BLOCK_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_comments(sql: str) -> str:
    """Drop SQL comments so leading `-- ...` doesn't fool the first-word check."""
    return _COMMENT_BLOCK_RE.sub(" ", _COMMENT_LINE_RE.sub(" ", sql))


def _is_read_only(sql: str) -> bool:
    # CTEs are valid read-only queries — accept both SELECT and WITH.
    normalized = _strip_comments(sql).strip().upper()
    words = normalized.split()
    first_word = words[0] if words else ""
    if first_word not in ("SELECT", "WITH"):
        return False
    for keyword in _BLOCKED_KEYWORDS:
        if keyword in normalized:
            return False
    return True


async def build_schema_summary() -> str:
    """Build rich schema description (tables, columns, enums, FKs, samples).

    Shared between the MCP tool `get_database_schema` and agent system prompt
    preloading — so the agent never has to guess enum values or FK relationships.
    """
    async with get_session() as db:
        tables_result = await db.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        ))
        tables = [r[0] for r in tables_result.all()]

        enums_result = await db.execute(text("""
            SELECT t.typname, string_agg(e.enumlabel, ' | ' ORDER BY e.enumsortorder)
            FROM pg_type t
            JOIN pg_enum e ON e.enumtypid = t.oid
            JOIN pg_namespace n ON n.oid = t.typnamespace
            WHERE n.nspname = 'public'
            GROUP BY t.typname
        """))
        enums = {r[0]: r[1] for r in enums_result.all()}

        fks_result = await db.execute(text("""
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS ref_table,
                ccu.column_name AS ref_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
        """))
        fks = {(r[0], r[1]): (r[2], r[3]) for r in fks_result.all()}

        lines = ["Database schema:"]
        for table in tables:
            cols_result = await db.execute(text(
                "SELECT column_name, data_type, is_nullable, column_default, udt_name "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :table "
                "ORDER BY ordinal_position"
            ), {"table": table})
            cols = cols_result.all()

            lines.append(f"\n## {table}")
            for col_name, data_type, nullable, default, udt_name in cols:
                null_str = "" if nullable == "YES" else " NOT NULL"
                default_str = f" DEFAULT {default}" if default else ""

                enum_hint = ""
                if data_type == "USER-DEFINED" and udt_name in enums:
                    enum_hint = f" [enum: {enums[udt_name]}]"

                fk_hint = ""
                ref = fks.get((table, col_name))
                if ref:
                    fk_hint = f" → {ref[0]}.{ref[1]}"

                sample_hint = ""
                if not enum_hint and _should_sample(col_name, data_type):
                    # Identifiers come from pg metadata, not user input — safe to interpolate.
                    sample_rows = await db.execute(text(
                        f'SELECT DISTINCT "{col_name}" FROM "{table}" '
                        f'WHERE "{col_name}" IS NOT NULL LIMIT 5'
                    ))
                    samples = [str(r[0]) for r in sample_rows.all()]
                    if samples:
                        sample_hint = f" [samples: {', '.join(samples)}]"

                lines.append(
                    f"  - {col_name}: {data_type}{null_str}{default_str}"
                    f"{enum_hint}{fk_hint}{sample_hint}"
                )

        return "\n".join(lines)


def _hint_for_sql_error(err: str) -> str | None:
    """Actionable hint for common Postgres errors — helps agent self-correct.

    Hints are agent-facing (the model reads them to retry); the agent translates
    its user-facing reply into the user's language, so English is fine here.
    """
    low = err.lower()
    if "invalid input value for enum" in low:
        return ("Enum values are case-sensitive. Check <database_schema> in the "
                "system prompt for the correct values (usually UPPERCASE).")
    if "column" in low and "does not exist" in low:
        return "Wrong column name. See <database_schema> in the system prompt."
    if "relation" in low and "does not exist" in low:
        return "Wrong table name. See <database_schema> in the system prompt."
    if "function round(double precision, integer) does not exist" in low:
        return "Postgres has no round(double, int). Cast first: ROUND(expr::numeric, 2)."
    if "operator does not exist" in low:
        return "Type mismatch. Check column types in the schema, cast with ::type if needed."
    return None


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_database_schema() -> str:
        """Return database structure (tables, columns, enum values, FKs, samples).
        Note: schema is already injected into the system prompt under
        <database_schema>. Only call this tool to re-fetch the latest schema
        (e.g., after a migration)."""
        return await build_schema_summary()

    @mcp.tool()
    async def query_database(sql: str) -> str:
        """Run a read-only SELECT on PostgreSQL 16 (default LIMIT 20 rows).
        Use when the specialized tools can't answer the question.
        Schema is in the system prompt — check <database_schema> before writing SQL.

        Postgres quirks:
        - Money columns (amount, target_amount…) are double precision.
        - ROUND(double, int) does NOT exist → cast: ROUND(expr::numeric, 2).
        - Avoid format/round in SQL; return raw numbers and format in the reply."""
        if not _is_read_only(sql):
            return "Error: only SELECT (read-only) statements are allowed."

        normalized = sql.strip().rstrip(";")
        if "LIMIT" not in normalized.upper():
            normalized += " LIMIT 20"

        async with get_session() as db:
            try:
                result = await db.execute(text(normalized))
                rows = result.all()
                columns = list(result.keys()) if result.keys() else []

                if not rows:
                    return "No results."

                lines = [" | ".join(str(c) for c in columns)]
                lines.append("-" * len(lines[0]))
                for row in rows:
                    lines.append(" | ".join(str(v) for v in row))

                return f"Results ({len(rows)} rows):\n" + "\n".join(lines)
            except Exception as e:
                err_msg = str(e)
                hint = _hint_for_sql_error(err_msg)
                out = f"SQL error: {err_msg}"
                if hint:
                    out += f"\n\nHint: {hint}"
                return out
