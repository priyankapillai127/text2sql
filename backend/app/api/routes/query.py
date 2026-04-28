"""
app/api/routes/query.py
────────────────────────
Routes for natural language → SQL generation and execution.
"""

from fastapi import APIRouter
from app.models.schemas import QueryRequest, QueryResponse
from app.services.query_orchestrator import handle_query

router = APIRouter(prefix="/query", tags=["Query"])


@router.post(
    "/",
    response_model=QueryResponse,
    summary="Generate and execute SQL from natural language",
    description=(
        "Accepts a natural language question and a target database name. "
        "Optionally uses RAG context and returns the generated SQL along "
        "with execution results."
    ),
)
def generate_and_execute(request: QueryRequest) -> QueryResponse:
    return handle_query(request)
