"""
app/rag/rag_service.py
──────────────────────
Retrieval-Augmented Generation module.

Responsibilities:
  1. Build FAISS index from Spider training examples (question + SQL pairs)
  2. Retrieve top-K similar examples for a given user question
  3. Format retrieved context for injection into LLM prompts

The index is loaded once at startup and reused across requests.
"""

from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

from app.core.config import get_settings
from app.core.exceptions import RAGIndexError
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Lazy imports — only pulled in when RAG is actually used
_faiss = None
_model = None


def _get_faiss():
    global _faiss
    if _faiss is None:
        import faiss as faiss_lib
        _faiss = faiss_lib
    return _faiss


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model: %s", settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model)
    return _model


# ──────────────────────────────────────────────
# Internal state (module-level singletons)
# ──────────────────────────────────────────────

_index = None           # faiss.IndexFlatIP
_examples: list[dict] = []   # [{question, sql, db_id}, ...]


# ──────────────────────────────────────────────
# Index management
# ──────────────────────────────────────────────

def build_index(examples_path: Optional[str] = None) -> int:
    """
    Embed Spider training examples and persist a FAISS index.
    Returns the number of indexed examples.
    """
    global _index, _examples

    faiss = _get_faiss()
    model = _get_model()

    path = examples_path or settings.spider_examples_path
    if not Path(path).exists():
        raise RAGIndexError(f"Examples file not found: {path}")

    with open(path, "r") as f:
        raw = json.load(f)

    # Spider format: list of {question, query, db_id}
    _examples = [
        {"question": item["question"], "sql": item["query"], "db_id": item.get("db_id", "")}
        for item in raw
        if "question" in item and "query" in item
    ]

    if not _examples:
        raise RAGIndexError("No valid examples found in the provided file.")

    questions = [ex["question"] for ex in _examples]
    logger.info("Embedding %d examples...", len(questions))
    embeddings = model.encode(questions, batch_size=64, show_progress_bar=False)
    embeddings = np.array(embeddings, dtype="float32")

    # Normalise for cosine similarity via inner product
    faiss.normalize_L2(embeddings)

    dim = embeddings.shape[1]
    _index = faiss.IndexFlatIP(dim)
    _index.add(embeddings)

    # Persist
    index_dir = Path(settings.faiss_index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(_index, str(index_dir / "examples.index"))
    with open(index_dir / "examples_meta.pkl", "wb") as f:
        pickle.dump(_examples, f)

    logger.info("FAISS index built and saved (%d vectors, dim=%d)", len(_examples), dim)
    return len(_examples)


def load_index() -> bool:
    """
    Load a previously built FAISS index from disk.
    Returns True on success, False if index does not exist yet.
    """
    global _index, _examples

    faiss = _get_faiss()
    index_dir = Path(settings.faiss_index_dir)
    index_file = index_dir / "examples.index"
    meta_file = index_dir / "examples_meta.pkl"

    if not index_file.exists() or not meta_file.exists():
        logger.warning("FAISS index not found at %s — RAG will be unavailable until built.", index_dir)
        return False

    _index = faiss.read_index(str(index_file))
    with open(meta_file, "rb") as f:
        _examples = pickle.load(f)
    logger.info("FAISS index loaded: %d examples", len(_examples))
    return True


def is_index_ready() -> bool:
    return _index is not None and len(_examples) > 0


# ──────────────────────────────────────────────
# Retrieval
# ──────────────────────────────────────────────

def retrieve(question: str, top_k: Optional[int] = None) -> list[dict]:
    """
    Retrieve the top-K most similar (question, SQL) pairs for a query.

    Returns a list of dicts: [{question, sql, db_id, score}, ...]
    """
    if not is_index_ready():
        logger.warning("RAG index not ready — returning empty context.")
        return []

    faiss = _get_faiss()
    model = _get_model()
    k = top_k or settings.rag_top_k

    vec = model.encode([question], show_progress_bar=False)
    vec = np.array(vec, dtype="float32")
    faiss.normalize_L2(vec)

    scores, indices = _index.search(vec, k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        entry = _examples[idx].copy()
        entry["score"] = float(score)
        results.append(entry)
    return results


def format_rag_context(examples: list[dict]) -> str:
    """
    Format retrieved examples into a prompt-friendly string block.
    """
    if not examples:
        return ""
    lines = ["-- Similar examples from training data:"]
    for i, ex in enumerate(examples, 1):
        lines.append(f"-- Example {i}:")
        lines.append(f"--   Question: {ex['question']}")
        lines.append(f"--   SQL: {ex['sql']}")
    return "\n".join(lines)
