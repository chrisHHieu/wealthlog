"""Regression tests for the read-only SQL validator used by query_database.

Bug history: a substring check ('CREATE' in normalized_sql) blocked legitimate
SELECTs that touched columns like ``created_at`` or ``updated_at``. The fix
tokenizes by word boundary so column names containing keyword substrings
no longer poison the validator.
"""

from app.ai.mcp.tools.discovery import _fan_out_risk, _is_read_only

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


# ── Fan-out (cartesian) risk detection ─────────────────────────────────────


def test_fan_out_flagged_for_join_plus_aggregate():
    """JOIN two fact tables and SUM without a CTE — the inflated-sum trap."""
    sql = (
        "SELECT SUM(t.amount) FROM transactions t "
        "JOIN budgets b ON b.category_id = t.category_id"
    )
    assert _fan_out_risk(sql) is True


def test_fan_out_not_flagged_without_aggregate():
    """A plain JOIN that returns rows (no aggregate) can't be inflated into a wrong sum."""
    sql = "SELECT t.id, c.name FROM transactions t JOIN categories c ON c.id = t.category_id"
    assert _fan_out_risk(sql) is False


def test_fan_out_not_flagged_without_join():
    """Single-table aggregation has nothing to fan out against."""
    sql = "SELECT SUM(amount) FROM transactions"
    assert _fan_out_risk(sql) is False


def test_fan_out_not_flagged_when_cte_used():
    """A CTE is assumed to isolate aggregates — the recommended safe shape."""
    sql = (
        "WITH tx AS (SELECT category_id, SUM(amount) s FROM transactions GROUP BY 1) "
        "SELECT b.name, tx.s FROM budgets b JOIN tx ON tx.category_id = b.category_id"
    )
    assert _fan_out_risk(sql) is False


def test_fan_out_ignores_keyword_in_comment():
    """A JOIN/SUM mentioned only in a comment must not trip the detector."""
    sql = "-- no JOIN, no SUM here\nSELECT amount FROM transactions"
    assert _fan_out_risk(sql) is False
