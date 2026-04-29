"""
app/services/ml_pipeline_service.py
─────────────────────────────────────
Bridge to the ML pipeline in ml/pipeline.py.

At startup, call initialize() once to load all FAISS indexes, schema graphs,
and error memory into memory.  Then call run() per request.

The ML pipeline uses its own data (ml/data/), its own execute_sql, and its
own Groq LLM — no overlap with the backend's own database_service.

sys.path is patched at import time so that pipeline.py can resolve its own
utils_local dependency without installing it as a package.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_ctx: dict | None = None
_pipeline_mod: Any = None


def _ml_dir() -> Path:
    base = Path(__file__).parent.parent.parent.parent  # backend/
    return (base / settings.ml_dir).resolve()


def _ensure_module() -> Any:
    global _pipeline_mod
    if _pipeline_mod is not None:
        return _pipeline_mod

    ml_path = _ml_dir()
    if not ml_path.exists():
        raise RuntimeError(
            f"ML directory not found at {ml_path}. "
            "Set ML_DIR in .env to the correct path relative to backend/."
        )

    # Inject ml/ onto sys.path so pipeline.py can import utils_local
    ml_str = str(ml_path)
    if ml_str not in sys.path:
        sys.path.insert(0, ml_str)

    _pipeline_mod = importlib.import_module("pipeline")
    return _pipeline_mod


def initialize() -> bool:
    """
    Load all ML pipeline data into memory (FAISS, schema graphs, error memory).
    Call once at application startup.  Returns True on success.
    """
    global _ctx
    try:
        mod = _ensure_module()
        _ctx = mod.setup()
        logger.info("ML pipeline initialised — FAISS + schema graphs loaded.")
        return True
    except Exception as exc:
        logger.warning(
            "ML pipeline init failed (Groq pipeline unavailable): %s", exc)
        return False


def is_ready() -> bool:
    return _ctx is not None


def get_available_databases() -> list[str]:
    """Return all Spider database IDs known to the ML pipeline."""
    if not is_ready():
        return []
    mod = _ensure_module()
    return mod.get_available_databases(_ctx)


def run(question: str, db_id: str, pipeline: str = "rag_bt") -> dict:
    """
    Execute the ML pipeline for a single question.

    Args:
        question : natural language question
        db_id    : Spider database id (e.g. "concert_singer")
        pipeline : "raw" | "rag" | "rag_bt"

    Returns the raw dict from ml/pipeline.run():
        sql, result, error, pipeline, repairs, bt_match, issue
    """
    if not is_ready():
        raise RuntimeError(
            "ML pipeline is not initialised. Ensure initialize() succeeded at startup."
        )

    mod = _ensure_module()
    return mod.run(question, db_id, _ctx, pipeline=pipeline)


def get_schema_text(db_id: str) -> str:
    """Return schema as prompt-ready text for a Spider database."""
    if not is_ready():
        return ""
    utils = importlib.import_module("utils_local")
    return utils.get_schema_text(db_id, _ctx["schema_dict"])


def execute_query(db_id: str, sql: str) -> tuple[list[dict] | None, str | None]:
    """Execute SQL against a Spider SQLite database. Returns (rows as dicts, error)."""
    db_path = _ml_dir() / "data" / "database" / db_id / f"{db_id}.sqlite"
    print(f"db_path for execution: {db_path}")  # Debug log for database path
    if not db_path.exists():
        return None, f"Database file not found: {db_path}"
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]
        # Debug log for execution success
        print(f"Query executed successfully, {len(rows)} rows returned.")
        conn.close()
        return rows, None
    except sqlite3.Error as exc:
        return None, str(exc)
    except Exception as exc:
        return None, f"Unexpected error: {exc}"
