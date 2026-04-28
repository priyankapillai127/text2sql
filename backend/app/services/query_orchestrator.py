"""
app/services/query_orchestrator.py
────────────────────────────────────
High-level orchestrator that wires together every service to handle
a single Text2SQL request end-to-end:

  1. Load schema
  2. Retrieve RAG context (optional)
  3. Build prompt
  4. Generate SQL via LLM
  5. Execute SQL
  6. Repair on failure (optional)
  7. Return structured QueryResponse
"""

from __future__ import annotations

import time
from typing import Any

from app.core.exceptions import SQLExecutionError
from app.core.logging import get_logger
from app.models.schemas import ModelBackend, QueryRequest, QueryResponse
from app.rag import rag_service
from app.services import database_service, llm_service, ml_pipeline_service, repair_service

logger = get_logger(__name__)


def _handle_query_groq(request: QueryRequest, start: float) -> QueryResponse:
    """
    Delegate entirely to the ML pipeline (Groq + FAISS + repair + BT validation).
    The ML pipeline owns its own RAG, repair, and execution against ml/data/.
    """
    if not ml_pipeline_service.is_ready():
        raise RuntimeError(
            "Groq/ML pipeline is not available. Check GROQ_API_KEY and ml/data/ setup."
        )

    pipeline_mode = request.pipeline if request.pipeline in ("raw", "rag", "rag_bt") else "rag_bt"
    result = ml_pipeline_service.run(request.question, request.database_name, pipeline_mode)

    latency_ms = (time.perf_counter() - start) * 1000
    execution_result: list[dict[str, Any]] | None = None
    if result.get("result") is not None:
        rows = result["result"]
        if rows and isinstance(rows[0], (list, tuple)):
            execution_result = [{"value": r} for r in rows]
        else:
            execution_result = [{"value": r} if not isinstance(r, dict) else r for r in rows]

    return QueryResponse(
        question=request.question,
        generated_sql=result["sql"],
        executed=result.get("error") is None and result["sql"] != "",
        execution_result=execution_result,
        execution_error=result.get("error"),
        repaired=result["repairs"] > 0,
        repair_attempts=result["repairs"],
        rag_context_used=result["pipeline"] != "raw",
        retrieved_examples=[],
        model_backend=request.model_backend,
        pipeline_used=result["pipeline"],
        bt_match=result.get("bt_match"),
        issue=result.get("issue"),
        latency_ms=round(latency_ms, 2),
    )


def handle_query(request: QueryRequest) -> QueryResponse:
    """
    Process a Text2SQL request and return a fully populated QueryResponse.
    """
    start = time.perf_counter()

    # ── Groq backend: delegate to the full ML pipeline ─────
    if request.model_backend == ModelBackend.GROQ:
        return _handle_query_groq(request, start)

    # ── 1. Schema ──────────────────────────────────────────
    schema = database_service.get_schema(request.database_name)
    schema_text = database_service.schema_to_prompt_text(schema)

    # ── 2. RAG retrieval ────────────────────────────────────
    rag_context = ""
    retrieved_examples: list[str] = []
    rag_used = False

    if request.use_rag and rag_service.is_index_ready():
        examples = rag_service.retrieve(request.question)
        if examples:
            rag_context = rag_service.format_rag_context(examples)
            retrieved_examples = [f"{e['question']} → {e['sql']}" for e in examples]
            rag_used = True

    # ── 3. Prompt construction ──────────────────────────────
    prompt = llm_service.build_prompt(
        question=request.question,
        schema_text=schema_text,
        rag_context=rag_context,
        conversation_history=request.conversation_history or None,
    )

    # ── 4. SQL generation ───────────────────────────────────
    generated_sql = llm_service.generate_sql(prompt, request.model_backend)
    logger.info("Generated SQL: %s", generated_sql)

    # ── 5. Execution ────────────────────────────────────────
    execution_result: list[dict[str, Any]] | None = None
    execution_error: str | None = None
    executed = False
    repaired = False
    repair_attempts = 0

    try:
        execution_result = database_service.execute_sql(request.database_name, generated_sql)
        executed = True
    except SQLExecutionError as exc:
        execution_error = str(exc)
        logger.warning("Initial SQL execution failed: %s", exc)

        # ── 6. Repair loop ──────────────────────────────────
        repaired_sql, repaired, repair_attempts = repair_service.repair_sql(
            original_sql=generated_sql,
            error_message=execution_error,
            schema_text=schema_text,
            question=request.question,
            backend=request.model_backend,
        )

        if repaired:
            generated_sql = repaired_sql
            try:
                execution_result = database_service.execute_sql(
                    request.database_name, generated_sql
                )
                executed = True
                execution_error = None
                logger.info("SQL repaired successfully after %d attempt(s)", repair_attempts)
            except SQLExecutionError as exc2:
                execution_error = str(exc2)
                logger.warning("Repaired SQL still failed: %s", exc2)

    latency_ms = (time.perf_counter() - start) * 1000

    return QueryResponse(
        question=request.question,
        generated_sql=generated_sql,
        executed=executed,
        execution_result=execution_result,
        execution_error=execution_error,
        repaired=repaired,
        repair_attempts=repair_attempts,
        rag_context_used=rag_used,
        retrieved_examples=retrieved_examples,
        model_backend=request.model_backend,
        pipeline_used=None,
        bt_match=None,
        issue=None,
        latency_ms=round(latency_ms, 2),
    )
