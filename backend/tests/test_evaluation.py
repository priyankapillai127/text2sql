"""
tests/test_evaluation.py
──────────────────────────
Unit tests for the evaluation service.
No LLM or database is required — these are pure logic tests.
"""

import pytest
from app.models.schemas import ErrorCategory
from app.services.evaluation_service import (
    categorise_error,
    exact_match,
)


# ──────────────────────────────────────────────
# Exact Match
# ──────────────────────────────────────────────

def test_exact_match_identical():
    assert exact_match("SELECT * FROM singer", "SELECT * FROM singer") is True


def test_exact_match_case_insensitive():
    assert exact_match("select * from singer", "SELECT * FROM singer") is True


def test_exact_match_trailing_semicolon():
    assert exact_match("SELECT * FROM singer;", "SELECT * FROM singer") is True


def test_exact_match_whitespace_normalised():
    assert exact_match("SELECT  *  FROM  singer", "SELECT * FROM singer") is True


def test_exact_match_different_query():
    assert exact_match("SELECT name FROM singer", "SELECT * FROM singer") is False


# ──────────────────────────────────────────────
# Error categorisation
# ──────────────────────────────────────────────

def test_categorise_schema_linking():
    cat = categorise_error(
        "SELECT * FROM singers",
        "no such table: singers",
        "SELECT * FROM singer",
    )
    assert cat == ErrorCategory.SCHEMA_LINKING


def test_categorise_syntax():
    cat = categorise_error(
        "SELECT FROM singer",
        "syntax error near FROM",
        "SELECT * FROM singer",
    )
    assert cat == ErrorCategory.SYNTAX


def test_categorise_aggregation_by_structure():
    cat = categorise_error(
        "SELECT name FROM singer",
        "",
        "SELECT count(*) FROM singer",
    )
    assert cat == ErrorCategory.AGGREGATION


def test_categorise_join_by_structure():
    cat = categorise_error(
        "SELECT * FROM singer",
        "",
        "SELECT s.name FROM singer s JOIN concert c ON s.singer_id = c.singer_id",
    )
    assert cat == ErrorCategory.JOIN_CONSTRUCTION


def test_categorise_unknown():
    cat = categorise_error("SELECT x FROM y", "", "SELECT a FROM b")
    assert cat == ErrorCategory.UNKNOWN
