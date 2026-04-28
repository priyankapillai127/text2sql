"""
app/api/routes/rag.py
──────────────────────
Routes for RAG index management and ad-hoc retrieval inspection.
"""

from fastapi import APIRouter
from app.models.schemas import IndexBuildRequest, IndexBuildResponse
from app.rag import rag_service
from app.core.config import get_settings

router = APIRouter(prefix="/rag", tags=["RAG"])
settings = get_settings()


@router.post(
    "/build-index",
    response_model=IndexBuildResponse,
    summary="Build FAISS index from Spider training examples",
    description=(
        "Embeds all (question, SQL) pairs from the Spider training file and "
        "writes a FAISS index to disk. Must be called once before RAG is active."
    ),
)
def build_index(request: IndexBuildRequest) -> IndexBuildResponse:
    count = rag_service.build_index(request.examples_path)
    return IndexBuildResponse(
        indexed_count=count,
        index_path=settings.faiss_index_dir,
        message=f"Index built successfully with {count} examples.",
    )


@router.post(
    "/load-index",
    summary="Load a previously built FAISS index from disk",
)
def load_index() -> dict:
    success = rag_service.load_index()
    return {
        "loaded": success,
        "message": "Index loaded." if success else "No index found on disk. Build it first.",
    }


@router.get(
    "/status",
    summary="Check whether the RAG index is ready",
)
def rag_status() -> dict:
    ready = rag_service.is_index_ready()
    return {
        "ready": ready,
        "indexed_examples": len(rag_service._examples) if ready else 0,
    }


@router.get(
    "/retrieve",
    summary="Retrieve similar examples for a question (debug / inspection)",
)
def retrieve_examples(question: str, top_k: int = 3) -> dict:
    examples = rag_service.retrieve(question, top_k=top_k)
    return {"question": question, "retrieved": examples}
