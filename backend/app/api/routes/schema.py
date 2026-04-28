"""
app/api/routes/schema.py
─────────────────────────
Routes for database schema inspection.
"""

from fastapi import APIRouter
from app.models.schemas import SchemaResponse
from app.services import ml_pipeline_service
from app.services.database_service import get_schema, list_databases

router = APIRouter(prefix="/schema", tags=["Schema"])


@router.get(
    "/databases",
    summary="List all available databases",
    response_model=list[str],
)
def list_all_databases() -> list[str]:
    """
    Returns Spider database IDs from the ML pipeline (tables.json) when ready,
    falling back to filesystem scanning of SQLITE_DB_DIR.
    """
    if ml_pipeline_service.is_ready():
        return ml_pipeline_service.get_available_databases()
    return list_databases()


@router.get(
    "/{database_name}",
    response_model=SchemaResponse,
    summary="Get schema for a specific database",
)
def get_database_schema(database_name: str) -> SchemaResponse:
    """Return tables, columns, types, and foreign-key links for the given database."""
    return get_schema(database_name)
