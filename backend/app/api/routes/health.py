"""
app/api/routes/health.py
─────────────────────────
Status and health-check endpoints.

GET /health       — lightweight liveness probe (always fast)
GET /health/full  — deep check of all system components
"""

import httpx
from fastapi import APIRouter

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import ComponentStatus, HealthResponse
from app.rag import rag_service
from app.services.database_service import list_databases

router = APIRouter(prefix="/health", tags=["Health"])
settings = get_settings()
logger = get_logger(__name__)


@router.get(
    "/",
    response_model=HealthResponse,
    summary="Liveness check — always returns quickly",
)
def health_check() -> HealthResponse:
    """Minimal probe used by load-balancers / Kubernetes liveness checks."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        components=[ComponentStatus(name="api", status="ok")],
    )


@router.get(
    "/full",
    response_model=HealthResponse,
    summary="Deep status check — probes Ollama, databases, and RAG index",
)
def full_health_check() -> HealthResponse:
    """
    Checks every major component and returns a consolidated status.
    Overall status is 'healthy' only when all components are 'ok'.
    """
    components: list[ComponentStatus] = []

    # ── API itself ─────────────────────────────────────────
    components.append(ComponentStatus(name="api", status="ok"))

    # ── Ollama ─────────────────────────────────────────────
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{settings.ollama_base_url}/api/tags")
            resp.raise_for_status()
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            detail = f"available models: {', '.join(models) or 'none'}"
            components.append(ComponentStatus(name="ollama", status="ok", detail=detail))
    except Exception as exc:
        components.append(
            ComponentStatus(name="ollama", status="unavailable", detail=str(exc))
        )

    # ── Databases ──────────────────────────────────────────
    try:
        dbs = list_databases()
        components.append(
            ComponentStatus(
                name="databases",
                status="ok",
                detail=f"{len(dbs)} database(s) found: {', '.join(dbs[:5])}{'...' if len(dbs) > 5 else ''}",
            )
        )
    except Exception as exc:
        components.append(ComponentStatus(name="databases", status="degraded", detail=str(exc)))

    # ── RAG Index ──────────────────────────────────────────
    if rag_service.is_index_ready():
        components.append(
            ComponentStatus(
                name="rag_index",
                status="ok",
                detail=f"{len(rag_service._examples)} examples indexed",
            )
        )
    else:
        components.append(
            ComponentStatus(
                name="rag_index",
                status="degraded",
                detail="Index not built yet. POST /rag/build-index to create it.",
            )
        )

    # ── OpenAI (optional) ─────────────────────────────────
    if settings.openai_api_key:
        components.append(ComponentStatus(name="openai", status="ok", detail="API key configured"))
    else:
        components.append(
            ComponentStatus(name="openai", status="degraded", detail="OPENAI_API_KEY not set")
        )

    # ── Derive overall status ─────────────────────────────
    statuses = {c.status for c in components}
    if "unavailable" in statuses:
        overall = "unhealthy"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        components=components,
    )
