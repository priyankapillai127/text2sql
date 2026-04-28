"""
app/core/config.py
──────────────────
Centralised settings loaded from environment variables / .env file.
All other modules import from here — never read os.environ directly.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Text2SQL Backend"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    sqlite_db_dir: str = "./data/databases"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Groq (used by the ML pipeline)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # ML pipeline directory (relative to backend/ or absolute)
    ml_dir: str = "../ml"

    # RAG
    embedding_model: str = "all-MiniLM-L6-v2"
    faiss_index_dir: str = "./data/faiss_index"
    spider_examples_path: str = "./data/spider_train.json"
    rag_top_k: int = 3

    # SQL Repair
    max_repair_attempts: int = 2


@lru_cache
def get_settings() -> Settings:
    """Cached singleton — one Settings object for the entire process."""
    return Settings()
