"""
app/services/llm_service.py
────────────────────────────
LLM backend for the Ollama path. Groq is handled by ml/pipeline.py.
"""

from __future__ import annotations

import json
import re
import urllib.request

from app.core.config import get_settings
from app.core.exceptions import LLMUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def build_prompt(
    question: str,
    schema_text: str,
    rag_context: str = "",
    conversation_history: list[str] | None = None,
) -> str:
    parts: list[str] = [
        "You are an expert SQL assistant. "
        "Given a database schema and a natural language question, "
        "write a single valid SQLite SQL query that answers the question.\n"
        "Rules:\n"
        "- Return ONLY the SQL query, no explanation, no markdown fences.\n"
        "- Use only tables and columns that exist in the provided schema.\n"
        "- Do NOT hallucinate column or table names.\n",
    ]
    parts.append("### Database Schema\n" + schema_text + "\n")
    if rag_context:
        parts.append("### Relevant Examples\n" + rag_context + "\n")
    if conversation_history:
        history_text = "\n".join(
            f"Turn {i + 1}: {turn}" for i, turn in enumerate(conversation_history)
        )
        parts.append("### Conversation History\n" + history_text + "\n")
    parts.append("### Question\n" + question + "\n")
    parts.append("### SQL Query")
    return "\n".join(parts)


def extract_sql(raw: str) -> str:
    raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE).strip("`").strip()
    if ";" in raw:
        raw = raw.split(";")[0].strip() + ";"
    return raw.strip()


def generate_sql(prompt: str) -> str:
    """Call the local Ollama model and return extracted SQL."""
    try:
        payload = json.dumps({
            "model": settings.ollama_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }).encode()
        req = urllib.request.Request(
            f"{settings.ollama_base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
        return extract_sql(result["message"]["content"])
    except Exception as exc:
        raise LLMUnavailableError(f"Ollama error: {exc}") from exc
