"""Date/month helpers — used by MCP tools, services, and routers."""

from calendar import monthrange
from datetime import date


def current_month() -> str:
    """Current month as ``YYYY-MM`` (no padding issues)."""
    d = date.today()
    return f"{d.year}-{d.month:02d}"


def today() -> str:
    """Today's date as ``YYYY-MM-DD``."""
    return date.today().isoformat()


def month_range(month: str) -> tuple[str, str]:
    """Return (start, end) ISO date strings for a YYYY-MM month.

    End is the actual last day (28/29/30/31) — avoids the ``{m}-31`` hack
    that would break if ``transactions.date`` ever migrates from String to
    a real DATE column.
    """
    y, m = int(month[:4]), int(month[5:7])
    last = monthrange(y, m)[1]
    return f"{y}-{m:02d}-01", f"{y}-{m:02d}-{last:02d}"
