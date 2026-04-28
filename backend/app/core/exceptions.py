"""
app/core/exceptions.py
──────────────────────
Domain-level exceptions that map to HTTP error responses.
FastAPI exception handlers are registered in main.py.
"""


class Text2SQLBaseError(Exception):
    """Root exception for the application."""


class DatabaseNotFoundError(Text2SQLBaseError):
    """Raised when the requested SQLite database file does not exist."""


class SchemaLoadError(Text2SQLBaseError):
    """Raised when schema extraction from a database fails."""


class LLMUnavailableError(Text2SQLBaseError):
    """Raised when neither Ollama nor the frontier model is reachable."""


class SQLExecutionError(Text2SQLBaseError):
    """Raised when generated SQL cannot be executed after repair attempts."""


class RAGIndexError(Text2SQLBaseError):
    """Raised when the FAISS index is missing or corrupt."""
