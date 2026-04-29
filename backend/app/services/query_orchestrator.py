"""
app/services/query_orchestrator.py
────────────────────────────────────
Routes requests to the right backend:
  - groq   → ml/pipeline.py (Groq LLM + FAISS RAG + repair + BT validation)
  - ollama → local Ollama model + Spider schema/execution via ml_pipeline_service
"""

from __future__ import annotations

import time
from typing import Any

from app.core.logging import get_logger
from app.models.schemas import ModelBackend, QueryRequest, QueryResponse
from app.services import llm_service, ml_pipeline_service, repair_service

logger = get_logger(__name__)


def handle_query(request: QueryRequest) -> QueryResponse:
    if request.model_backend == ModelBackend.GROQ:
        return _handle_groq(request)
    return _handle_ollama(request)


# ── Groq path ─────────────────────────────────────────────────────────────────

def _handle_groq(request: QueryRequest) -> QueryResponse:
    if not ml_pipeline_service.is_ready():
        raise RuntimeError(
            "ML pipeline is not available. Check GROQ_API_KEY and ml/data/ setup."
        )
    start = time.perf_counter()
    pipeline_mode = request.pipeline if request.pipeline in (
        "raw", "rag", "rag_bt") else "rag_bt"
    result = ml_pipeline_service.run(
        request.question, request.database_name, pipeline_mode)

    print(f"ML pipeline result: {result}")  # Debug log for pipeline output

    if result["sql"]:
        rows, exec_error = ml_pipeline_service.execute_query(
            request.database_name, result["sql"])
        result["result"] = rows
        result["error"] = exec_error

    latency_ms = (time.perf_counter() - start) * 1000
    execution_result = _normalise_rows(result.get("result"))

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


# ── Ollama path ────────────────────────────────────────────────────────────────

def _handle_ollama(request: QueryRequest) -> QueryResponse:
    start = time.perf_counter()

    schema_text = ml_pipeline_service.get_schema_text(request.database_name)
    prompt = llm_service.build_prompt(
        question=request.question,
        schema_text=schema_text,
        conversation_history=request.conversation_history or None,
    )
    generated_sql = llm_service.generate_sql(prompt)

    print(f"Ollama generated SQL: {generated_sql}")

    rows, exec_error = ml_pipeline_service.execute_query(
        request.database_name, generated_sql)
    repaired = False
    repair_attempts = 0

    if exec_error:
        repaired_sql, repaired, repair_attempts = repair_service.repair_sql(
            original_sql=generated_sql,
            error_message=exec_error,
            schema_text=schema_text,
            question=request.question,
        )
        if repaired:
            generated_sql = repaired_sql
            rows, exec_error = ml_pipeline_service.execute_query(
                request.database_name, generated_sql)

    latency_ms = (time.perf_counter() - start) * 1000
    execution_result = _normalise_rows(rows) if rows is not None else None

    return QueryResponse(
        question=request.question,
        generated_sql=generated_sql,
        executed=exec_error is None and generated_sql != "",
        execution_result=execution_result,
        execution_error=exec_error,
        repaired=repaired,
        repair_attempts=repair_attempts,
        rag_context_used=False,
        retrieved_examples=[],
        model_backend=request.model_backend,
        pipeline_used=None,
        bt_match=None,
        issue=None,
        latency_ms=round(latency_ms, 2),
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _normalise_rows(rows: Any) -> list[dict[str, Any]] | None:
    if rows is None:
        return None
    if rows and isinstance(rows[0], (list, tuple)):
        return [{"value": r} for r in rows]
    return [{"value": r} if not isinstance(r, dict) else r for r in rows]
