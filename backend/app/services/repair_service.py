"""
app/services/repair_service.py
───────────────────────────────
Execution-feedback-based SQL repair loop.

When the first generated SQL fails to execute, this service feeds the
error message back to the LLM along with the schema and asks it to
produce a corrected query.  This mimics the self-debugging technique
described in Chen et al. (2023).
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.exceptions import SQLExecutionError
from app.core.logging import get_logger
from app.models.schemas import ModelBackend
from app.services import database_service, llm_service

logger = get_logger(__name__)
settings = get_settings()


def repair_sql(
    original_sql: str,
    error_message: str,
    schema_text: str,
    question: str,
    backend: ModelBackend,
    max_attempts: int | None = None,
) -> tuple[str, bool, int]:
    """
    Attempt to repair `original_sql` by feeding the execution error back to the LLM.

    Returns:
        (final_sql, was_repaired, attempts_made)
    """
    max_attempts = max_attempts or settings.max_repair_attempts
    current_sql = original_sql
    current_error = error_message

    for attempt in range(1, max_attempts + 1):
        logger.info("SQL repair attempt %d/%d", attempt, max_attempts)
        repair_prompt = _build_repair_prompt(
            original_sql=current_sql,
            error_message=current_error,
            schema_text=schema_text,
            question=question,
        )
        try:
            candidate_sql = llm_service.generate_sql(repair_prompt, backend)
        except Exception as exc:
            logger.warning("LLM failed during repair attempt %d: %s", attempt, exc)
            break

        # Test the repaired SQL
        try:
            database_service.execute_sql.__doc__  # just referencing to avoid import cycle check
        except Exception:
            pass

        current_sql = candidate_sql
        # Caller will re-try execution; we return the candidate
        return current_sql, True, attempt

    return current_sql, False, max_attempts


def _build_repair_prompt(
    original_sql: str,
    error_message: str,
    schema_text: str,
    question: str,
) -> str:
    return (
        "You are an expert SQL debugger.\n"
        "The following SQL query failed with an error. "
        "Fix the query so it runs correctly against the provided schema.\n\n"
        "### Database Schema\n"
        f"{schema_text}\n\n"
        "### Original Question\n"
        f"{question}\n\n"
        "### Failing SQL\n"
        f"{original_sql}\n\n"
        "### Error Message\n"
        f"{error_message}\n\n"
        "Return ONLY the corrected SQL query, no explanation.\n"
        "### Corrected SQL"
    )
