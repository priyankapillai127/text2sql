"""
app/services/evaluation_service.py
────────────────────────────────────
Evaluation utilities:
  - Exact Match (EM) comparison
  - Execution Accuracy (EX) by running both SQLs and comparing result sets
  - Automatic error categorisation
"""

from __future__ import annotations

import re
from typing import Optional

from app.core.exceptions import SQLExecutionError
from app.core.logging import get_logger
from app.models.schemas import ErrorCategory
from app.services.database_service import execute_sql

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Normalisation
# ──────────────────────────────────────────────

def _normalise(sql: str) -> str:
    """Lower-case, collapse whitespace, strip trailing semicolon."""
    sql = sql.lower().strip().rstrip(";").strip()
    sql = re.sub(r"\s+", " ", sql)
    return sql


# ──────────────────────────────────────────────
# Exact Match
# ──────────────────────────────────────────────

def exact_match(generated: str, ground_truth: str) -> bool:
    return _normalise(generated) == _normalise(ground_truth)


# ──────────────────────────────────────────────
# Execution Accuracy
# ──────────────────────────────────────────────

def execution_accuracy(
    database_name: str,
    generated_sql: str,
    ground_truth_sql: str,
) -> tuple[bool, Optional[str]]:
    """
    Run both queries and compare their result sets.
    Returns (match: bool, error_detail: str | None).
    """
    try:
        gen_rows = execute_sql(database_name, generated_sql)
    except SQLExecutionError as exc:
        return False, f"Generated SQL failed: {exc}"

    try:
        gt_rows = execute_sql(database_name, ground_truth_sql)
    except SQLExecutionError as exc:
        return False, f"Ground-truth SQL failed: {exc}"

    # Compare as sorted lists of frozensets (order-insensitive, key-insensitive)
    def normalise_rows(rows):
        return sorted(
            [frozenset((k.lower(), str(v)) for k, v in row.items()) for row in rows]
        )

    match = normalise_rows(gen_rows) == normalise_rows(gt_rows)
    return match, None


# ──────────────────────────────────────────────
# Error categorisation
# ──────────────────────────────────────────────

_CATEGORY_PATTERNS: list[tuple[ErrorCategory, list[str]]] = [
    (ErrorCategory.SCHEMA_LINKING,    ["no such table", "no such column", "ambiguous column"]),
    (ErrorCategory.JOIN_CONSTRUCTION, ["join", "foreign key", "cartesian"]),
    (ErrorCategory.AGGREGATION,       ["aggregate", "group by", "having", "count", "sum", "avg"]),
    (ErrorCategory.NESTED_QUERY,      ["subquery", "nested", "exists", "in ("]),
    (ErrorCategory.SYNTAX,            ["syntax error", "parse error", "near"]),
    (ErrorCategory.EXECUTION,         ["execution", "runtime"]),
]


def categorise_error(
    generated_sql: str,
    error_message: str,
    ground_truth_sql: str,
) -> ErrorCategory:
    """
    Heuristically classify an error into one of the defined categories.
    """
    combined = (error_message + " " + generated_sql).lower()

    for category, keywords in _CATEGORY_PATTERNS:
        if any(kw in combined for kw in keywords):
            return category

    # Structural comparison: if GT has JOIN but generated doesn't → JOIN error
    if "join" in ground_truth_sql.lower() and "join" not in generated_sql.lower():
        return ErrorCategory.JOIN_CONSTRUCTION

    if any(agg in ground_truth_sql.lower() for agg in ["count(", "sum(", "avg(", "max(", "min("]):
        if not any(agg in generated_sql.lower() for agg in ["count(", "sum(", "avg(", "max(", "min("]):
            return ErrorCategory.AGGREGATION

    return ErrorCategory.UNKNOWN
