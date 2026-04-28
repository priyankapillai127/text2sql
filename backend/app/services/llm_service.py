"""
app/services/llm_service.py
────────────────────────────
Unified interface for all LLM backends:
  - Ollama   (local open-source model)
  - OpenAI   (proprietary frontier model)
  - Seq2SQL  (classical baseline — stub returning a placeholder)

Each backend implements the same signature:
    generate_sql(prompt: str) -> str
"""

from __future__ import annotations

import re

from app.core.config import get_settings
from app.core.exceptions import LLMUnavailableError
from app.core.logging import get_logger
from app.models.schemas import ModelBackend

logger = get_logger(__name__)
settings = get_settings()


# ──────────────────────────────────────────────
# Prompt builder
# ──────────────────────────────────────────────

def build_prompt(
    question: str,
    schema_text: str,
    rag_context: str = "",
    conversation_history: list[str] | None = None,
) -> str:
    """
    Assemble the full prompt sent to the LLM.
    Structure:
      1. System instruction
      2. Schema
      3. RAG examples (optional)
      4. Conversation history (optional, for CoSQL)
      5. Current question
    """
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
    """
    Strip markdown fences or preamble text that some models include.
    Returns the clean SQL string.
    """
    # Remove ```sql ... ``` or ``` ... ```
    raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE).strip("`").strip()
    # Take the first statement if multiple are returned
    if ";" in raw:
        raw = raw.split(";")[0].strip() + ";"
    return raw.strip()


# ──────────────────────────────────────────────
# OpenAI backend
# ──────────────────────────────────────────────

def _generate_openai(prompt: str) -> str:
    if not settings.openai_api_key:
        raise LLMUnavailableError("OPENAI_API_KEY is not configured.")
    try:
        from openai import OpenAI  # imported here to avoid hard dep at startup
        client = OpenAI(api_key=settings.openai_api_key)
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        raw = completion.choices[0].message.content or ""
        return extract_sql(raw)
    except ImportError as exc:
        raise LLMUnavailableError("openai package is not installed.") from exc
    except Exception as exc:
        raise LLMUnavailableError(f"OpenAI API error: {exc}") from exc


# ──────────────────────────────────────────────
# Groq backend
# ──────────────────────────────────────────────

def _generate_groq(prompt: str) -> str:
    if not settings.groq_api_key:
        raise LLMUnavailableError("GROQ_API_KEY is not configured.")
    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.0,
        )
        raw = response.choices[0].message.content or ""
        return extract_sql(raw)
    except ImportError as exc:
        raise LLMUnavailableError("groq package is not installed.") from exc
    except Exception as exc:
        raise LLMUnavailableError(f"Groq API error: {exc}") from exc


# ──────────────────────────────────────────────
# Seq2SQL stub (classical baseline placeholder)
# ──────────────────────────────────────────────

def _generate_seq2sql(prompt: str) -> str:
    """
    Seq2SQL is not re-implemented here; the original model requires a
    separate training/inference pipeline.  This stub returns a clearly
    labelled placeholder so the evaluation pipeline can track it as a
    separate system without crashing.
    """
    logger.warning("Seq2SQL stub called — returning placeholder SQL.")
    return "SELECT * FROM table_name LIMIT 10;  -- Seq2SQL stub: integrate real model here"


# ──────────────────────────────────────────────
# Dispatcher
# ──────────────────────────────────────────────

def generate_sql(prompt: str, backend: ModelBackend) -> str:
    """Route the prompt to the correct LLM backend."""
    logger.debug("Generating SQL with backend=%s", backend)
    if backend == ModelBackend.GROQ:
        return _generate_groq(prompt)
    elif backend == ModelBackend.OPENAI:
        return _generate_openai(prompt)
    elif backend == ModelBackend.SEQ2SQL:
        return _generate_seq2sql(prompt)
    else:
        raise LLMUnavailableError(f"Unknown backend: {backend}")
