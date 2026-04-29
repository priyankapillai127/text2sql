"""
app/models/schemas.py
─────────────────────
Pydantic models for all API request bodies and response payloads.
Keeping them in one file makes it easy for the frontend team to
review the contract at a glance.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────

class ModelBackend(str, Enum):
    GROQ   = "groq"    # Groq-hosted Llama via ml/pipeline.py
    OLLAMA = "ollama"  # Local Ollama model


class ErrorCategory(str, Enum):
    SCHEMA_LINKING = "schema_linking"
    JOIN_CONSTRUCTION = "join_construction"
    AGGREGATION = "aggregation"
    NESTED_QUERY = "nested_query"
    CONVERSATIONAL_CONTEXT = "conversational_context"
    SYNTAX = "syntax"
    EXECUTION = "execution"
    UNKNOWN = "unknown"


# ──────────────────────────────────────────────
# Query / Generation
# ──────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Natural language question")
    database_name: str = Field(..., description="Target Spider/CoSQL database name")
    model_backend: ModelBackend = Field(ModelBackend.GROQ, description="LLM backend to use")
    pipeline: str = Field("rag_bt", description="ML pipeline mode (groq only): raw | rag | rag_bt")
    conversation_history: list[str] = Field(
        default_factory=list,
        description="Previous turns (for CoSQL conversational mode)"
    )

    model_config = {"json_schema_extra": {
        "example": {
            "question": "How many singers are there?",
            "database_name": "concert_singer",
            "model_backend": "groq",
            "pipeline": "rag_bt",
            "conversation_history": []
        }
    }}


class QueryResponse(BaseModel):
    question: str
    generated_sql: str
    executed: bool
    execution_result: Optional[list[dict[str, Any]]] = None
    execution_error: Optional[str] = None
    repaired: bool = False
    repair_attempts: int = 0
    rag_context_used: bool = False
    retrieved_examples: list[str] = Field(default_factory=list)
    model_backend: ModelBackend
    pipeline_used: Optional[str] = None
    bt_match: Optional[bool] = None
    issue: Optional[str] = None
    latency_ms: float


# ──────────────────────────────────────────────
# Schema
# ──────────────────────────────────────────────

class ColumnInfo(BaseModel):
    name: str
    type: str
    primary_key: bool = False
    nullable: bool = True


class TableInfo(BaseModel):
    name: str
    columns: list[ColumnInfo]
    foreign_keys: list[dict[str, str]] = Field(default_factory=list)


class SchemaResponse(BaseModel):
    database_name: str
    tables: list[TableInfo]


# ──────────────────────────────────────────────
# Evaluation
# ──────────────────────────────────────────────

class EvaluationRequest(BaseModel):
    database_name: str
    question: str
    ground_truth_sql: str
    pipeline: str = "rag_bt"


class EvaluationResult(BaseModel):
    question: str
    ground_truth_sql: str
    generated_sql: str
    exact_match: bool
    execution_accuracy: bool
    error_category: Optional[ErrorCategory] = None
    error_detail: Optional[str] = None
    latency_ms: float


class BatchEvaluationRequest(BaseModel):
    items: list[EvaluationRequest]
    pipeline: str = "rag_bt"


class BatchEvaluationResponse(BaseModel):
    total: int
    exact_match_score: float
    execution_accuracy_score: float
    results: list[EvaluationResult]


# ──────────────────────────────────────────────
# RAG Index Management
# ──────────────────────────────────────────────

class IndexBuildRequest(BaseModel):
    examples_path: Optional[str] = Field(
        None,
        description="Path to Spider-format JSON examples. Defaults to configured path."
    )


class IndexBuildResponse(BaseModel):
    indexed_count: int
    index_path: str
    message: str


# ──────────────────────────────────────────────
# Health / Status
# ──────────────────────────────────────────────

class ComponentStatus(BaseModel):
    name: str
    status: str          # "ok" | "degraded" | "unavailable"
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str          # "healthy" | "degraded" | "unhealthy"
    version: str
    components: list[ComponentStatus]
