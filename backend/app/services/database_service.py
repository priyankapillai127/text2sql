"""
app/services/database_service.py
─────────────────────────────────
Handles all SQLite interactions:
  - Listing available databases
  - Extracting table/column schemas
  - Executing generated SQL queries safely
"""

import os
import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import DatabaseNotFoundError, SchemaLoadError, SQLExecutionError
from app.core.logging import get_logger
from app.models.schemas import ColumnInfo, SchemaResponse, TableInfo

logger = get_logger(__name__)
settings = get_settings()


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _db_path(database_name: str) -> Path:
    """Resolve full path to the SQLite file."""
    base = Path(settings.sqlite_db_dir)
    # Spider stores each DB in its own subfolder: databases/<name>/<name>.sqlite
    candidates = [
        base / database_name / f"{database_name}.sqlite",
        base / f"{database_name}.sqlite",
        base / database_name / f"{database_name}.db",
        base / f"{database_name}.db",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise DatabaseNotFoundError(
        f"Database '{database_name}' not found under '{base}'. "
        f"Checked: {[str(c) for c in candidates]}"
    )


def _connect(database_name: str) -> sqlite3.Connection:
    path = _db_path(database_name)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row          # allows dict-style access
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def list_databases() -> list[str]:
    """Return all available database names."""
    base = Path(settings.sqlite_db_dir)
    if not base.exists():
        return []
    names: list[str] = []
    for entry in sorted(base.iterdir()):
        if entry.is_dir():
            for ext in (".sqlite", ".db"):
                if (entry / f"{entry.name}{ext}").exists():
                    names.append(entry.name)
                    break
        elif entry.suffix in (".sqlite", ".db"):
            names.append(entry.stem)
    return names


def get_schema(database_name: str) -> SchemaResponse:
    """Extract full schema (tables + columns + FK links) from the database."""
    try:
        conn = _connect(database_name)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        table_names = [row[0] for row in cursor.fetchall()]

        tables: list[TableInfo] = []
        for table_name in table_names:
            # Columns
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = [
                ColumnInfo(
                    name=row["name"],
                    type=row["type"] or "TEXT",
                    primary_key=bool(row["pk"]),
                    nullable=not bool(row["notnull"]),
                )
                for row in cursor.fetchall()
            ]

            # Foreign keys
            cursor.execute(f"PRAGMA foreign_key_list('{table_name}')")
            fks = [
                {
                    "from_column": row["from"],
                    "to_table": row["table"],
                    "to_column": row["to"],
                }
                for row in cursor.fetchall()
            ]

            tables.append(TableInfo(name=table_name, columns=columns, foreign_keys=fks))

        conn.close()
        return SchemaResponse(database_name=database_name, tables=tables)

    except DatabaseNotFoundError:
        raise
    except Exception as exc:
        raise SchemaLoadError(f"Failed to load schema for '{database_name}': {exc}") from exc


def schema_to_prompt_text(schema: SchemaResponse) -> str:
    """
    Render the schema as a compact text block suitable for LLM prompts.
    Example output:
        Table: singer (singer_id INT PK, name TEXT, country TEXT)
        Table: concert (concert_id INT PK, concert_name TEXT, singer_id INT -> singer.singer_id)
    """
    lines: list[str] = []
    for table in schema.tables:
        col_parts: list[str] = []
        for col in table.columns:
            part = f"{col.name} {col.type}"
            if col.primary_key:
                part += " PK"
            col_parts.append(part)
        fk_map = {fk["from_column"]: f"{fk['to_table']}.{fk['to_column']}" for fk in table.foreign_keys}
        col_strs = []
        for col in table.columns:
            s = f"{col.name} {col.type}"
            if col.primary_key:
                s += " PK"
            if col.name in fk_map:
                s += f" -> {fk_map[col.name]}"
            col_strs.append(s)
        lines.append(f"Table: {table.name} ({', '.join(col_strs)})")
    return "\n".join(lines)


def execute_sql(database_name: str, sql: str) -> list[dict[str, Any]]:
    """
    Execute a SQL query and return rows as a list of dicts.
    Raises SQLExecutionError on failure.
    """
    try:
        conn = _connect(database_name)
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        logger.debug("Executed SQL on '%s': %d row(s) returned", database_name, len(rows))
        return rows
    except DatabaseNotFoundError:
        raise
    except sqlite3.Error as exc:
        raise SQLExecutionError(str(exc)) from exc
    except Exception as exc:
        raise SQLExecutionError(f"Unexpected error during SQL execution: {exc}") from exc
