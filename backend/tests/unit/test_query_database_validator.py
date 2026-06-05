"""Regression tests for the read-only SQL validator used by query_database.

Bug history: a substring check ('CREATE' in normalized_sql) blocked legitimate
SELECTs that touched columns like ``created_at`` or ``updated_at``. The fix
tokenizes by word boundary so column names containing keyword substrings
no longer poison the validator.
"""

from app.ai.mcp.tools.discovery import _is_read_only

# ── Legit SELECTs (must pass) ──────────────────────────────────────────────


def test_select_with_created_at_column_passes():
    """The exact shape that triggered the original 'CREATE' substring bug."""
    sql = (
        "SELECT id, fact, category, importance, verified_by_user, created_at "
        "FROM user_facts "
        "ORDER BY importance DESC, updated_at DESC "
        "LIMIT 100"
    )
    assert _is_read_only(sql) is True


def test_select_with_updated_at_column_passes():
    """`updated_at` contains the substring 'UPDATE' — must not trip the check."""
    sql = "SELECT updated_at FROM session_summaries"
    assert _is_read_only(sql) is True


def test_select_with_dropdown_label_column_passes():
    """`dropdown_label` contains 'DROP' — must not trip the check."""
    sql = "SELECT dropdown_label FROM categories"
    assert _is_read_only(sql) is True


def test_simple_select_passes():
    assert _is_read_only("SELECT 1") is True


def test_cte_with_select_passes():
    """WITH ... SELECT is the recursive/CTE form of a read-only query."""
    sql = "WITH recent AS (SELECT * FROM transactions LIMIT 10) SELECT * FROM recent"
    assert _is_read_only(sql) is True


def test_select_with_leading_comment_passes():
    """`-- ...` and `/* ... */` get stripped before the first-word check."""
    sql = "-- pull recent goals\nSELECT * FROM goals"
    assert _is_read_only(sql) is True
    sql2 = "/* analytics */ SELECT count(*) FROM transactions"
    assert _is_read_only(sql2) is True


# ── Mutations (must be blocked) ────────────────────────────────────────────


def test_insert_blocked():
    assert _is_read_only("INSERT INTO foo VALUES (1)") is False


def test_update_blocked():
    assert _is_read_only("UPDATE foo SET x = 1") is False


def test_delete_blocked():
    assert _is_read_only("DELETE FROM foo") is False


def test_drop_blocked():
    assert _is_read_only("DROP TABLE foo") is False


def test_statement_chaining_attack_blocked():
    """A trailing DROP after a benign SELECT must still be caught."""
    sql = "SELECT 1; DROP TABLE user_facts"
    assert _is_read_only(sql) is False


def test_chain_with_legit_columns_still_blocks_drop():
    """Mixing legit `created_at` with a chained DROP — keyword still triggers block."""
    sql = "SELECT created_at FROM user_facts; DROP TABLE x"
    assert _is_read_only(sql) is False


def test_uppercase_mutation_blocked():
    """Validator normalizes case; lowercase mutations are equally rejected."""
    assert _is_read_only("insert into foo values (1)") is False
    assert _is_read_only("delete from foo") is False


def test_empty_sql_blocked():
    assert _is_read_only("") is False
    assert _is_read_only("   ") is False
    assert _is_read_only("-- only a comment") is False


def test_non_select_first_word_blocked():
    """Even a benign-looking command like EXPLAIN is rejected — only SELECT/WITH allowed."""
    assert _is_read_only("EXPLAIN SELECT * FROM foo") is False
