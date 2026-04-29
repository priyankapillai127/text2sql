"""
app/services/repair_service.py
───────────────────────────────
Execution-feedback SQL repair loop for the Ollama path.
(Groq repair is handled internally by ml/pipeline.py.)
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services import llm_service

logger = get_logger(__name__)
settings = get_settings()


def repair_sql(
    original_sql: str,
    error_message: str,
    schema_text: str,
    question: str,
    max_attempts: int | None = None,
) -> tuple[str, bool, int]:
    """
    Feed the execution error back to Ollama and ask for a corrected query.
    Returns (final_sql, was_repaired, attempts_made).
    """
    max_attempts = max_attempts or settings.max_repair_attempts
    current_sql = original_sql

    for attempt in range(1, max_attempts + 1):
        logger.info("SQL repair attempt %d/%d", attempt, max_attempts)
        prompt = _build_repair_prompt(current_sql, error_message, schema_text, question)
        try:
            current_sql = llm_service.generate_sql(prompt)
            return current_sql, True, attempt
        except Exception as exc:
            logger.warning("LLM failed during repair attempt %d: %s", attempt, exc)

    return current_sql, False, max_attempts


def _build_repair_prompt(sql: str, error: str, schema_text: str, question: str) -> str:
    return (
        "You are an expert SQL debugger.\n"
        "The following SQL query failed. Fix it so it runs correctly.\n\n"
        f"### Database Schema\n{schema_text}\n\n"
        f"### Original Question\n{question}\n\n"
        f"### Failing SQL\n{sql}\n\n"
        f"### Error\n{error}\n\n"
        "Return ONLY the corrected SQL. No explanation.\n"
        "### Corrected SQL"
    )
