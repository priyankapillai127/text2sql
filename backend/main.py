"""
main.py
────────
FastAPI application factory and entry point.

Run with:
    uvicorn main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    DatabaseNotFoundError,
    LLMUnavailableError,
    RAGIndexError,
    SchemaLoadError,
    SQLExecutionError,
)
from app.core.logging import get_logger, setup_logging
from app.rag import rag_service
from app.services import ml_pipeline_service

settings = get_settings()
setup_logging(debug=settings.debug)
logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once on startup and once on shutdown.
    Attempts to load the FAISS index from disk if it exists.
    """
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    # Backend RAG index (used by ollama/openai paths)
    loaded = rag_service.load_index()
    if loaded:
        logger.info("RAG index loaded at startup.")
    else:
        logger.warning(
            "RAG index not found at startup. "
            "POST /rag/build-index to create one before using RAG."
        )

    # ML pipeline (used by groq backend)
    ml_ok = ml_pipeline_service.initialize()
    if ml_ok:
        logger.info("Groq/ML pipeline ready.")
    else:
        logger.warning(
            "Groq/ML pipeline unavailable at startup. "
            "Check GROQ_API_KEY and that ml/data/ exists."
        )

    yield
    logger.info("Shutting down.")


# ──────────────────────────────────────────────
# App factory
# ──────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Text2SQL backend: natural language → SQL generation with RAG, "
        "multi-model support (Ollama / OpenAI / Seq2SQL), execution feedback repair, "
        "and evaluation utilities."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────
# Allow the Next.js frontend (default: localhost:3000) to call the API.
# Tighten this list before production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


# ──────────────────────────────────────────────
# Global exception handlers
# ──────────────────────────────────────────────

@app.exception_handler(DatabaseNotFoundError)
async def database_not_found_handler(request: Request, exc: DatabaseNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(SchemaLoadError)
async def schema_load_handler(request: Request, exc: SchemaLoadError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(LLMUnavailableError)
async def llm_unavailable_handler(request: Request, exc: LLMUnavailableError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(SQLExecutionError)
async def sql_execution_handler(request: Request, exc: SQLExecutionError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(RAGIndexError)
async def rag_index_handler(request: Request, exc: RAGIndexError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ── Root redirect ─────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return {"message": f"{settings.app_name} is running. Visit /docs for the API reference."}
