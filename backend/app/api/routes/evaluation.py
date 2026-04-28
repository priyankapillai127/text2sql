"""
app/api/routes/evaluation.py
─────────────────────────────
Routes for benchmarking and failure-mode analysis.
"""

import time
from fastapi import APIRouter

from app.models.schemas import (
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    ErrorCategory,
    EvaluationRequest,
    EvaluationResult,
)
from app.services import evaluation_service
from app.services.query_orchestrator import handle_query
from app.models.schemas import QueryRequest

router = APIRouter(prefix="/evaluate", tags=["Evaluation"])


def _evaluate_single(item: EvaluationRequest) -> EvaluationResult:
    start = time.perf_counter()

    # Generate SQL using the orchestrator
    q_request = QueryRequest(
        question=item.question,
        database_name=item.database_name,
        model_backend=item.model_backend,
        use_rag=item.use_rag,
    )
    q_response = handle_query(q_request)
    generated_sql = q_response.generated_sql

    # Exact Match
    em = evaluation_service.exact_match(generated_sql, item.ground_truth_sql)

    # Execution Accuracy
    ex, error_detail = evaluation_service.execution_accuracy(
        item.database_name, generated_sql, item.ground_truth_sql
    )

    # Error category (only when wrong)
    error_category: ErrorCategory | None = None
    if not ex:
        error_category = evaluation_service.categorise_error(
            generated_sql,
            error_detail or q_response.execution_error or "",
            item.ground_truth_sql,
        )

    latency_ms = (time.perf_counter() - start) * 1000

    return EvaluationResult(
        question=item.question,
        ground_truth_sql=item.ground_truth_sql,
        generated_sql=generated_sql,
        exact_match=em,
        execution_accuracy=ex,
        error_category=error_category,
        error_detail=error_detail,
        latency_ms=round(latency_ms, 2),
    )


@router.post(
    "/single",
    response_model=EvaluationResult,
    summary="Evaluate a single question against ground-truth SQL",
)
def evaluate_single(request: EvaluationRequest) -> EvaluationResult:
    return _evaluate_single(request)


@router.post(
    "/batch",
    response_model=BatchEvaluationResponse,
    summary="Batch evaluation — returns EM and EX scores across multiple examples",
)
def evaluate_batch(request: BatchEvaluationRequest) -> BatchEvaluationResponse:
    results: list[EvaluationResult] = []

    for item in request.items:
        # Override backend/rag settings from batch-level config
        item.model_backend = request.model_backend
        item.use_rag = request.use_rag
        results.append(_evaluate_single(item))

    total = len(results)
    em_score = sum(r.exact_match for r in results) / total if total else 0.0
    ex_score = sum(r.execution_accuracy for r in results) / total if total else 0.0

    return BatchEvaluationResponse(
        total=total,
        exact_match_score=round(em_score, 4),
        execution_accuracy_score=round(ex_score, 4),
        results=results,
    )
