"""
utils_local.py — Text2SQL Group 28
====================================
Local version of utils_v4.py with no torch/transformers dependency.
All LLM calls go through Groq API.
Loads FAISS indexes, schema graphs, and Spider databases from local data/ folder.
"""

import os
import re
import json
import pickle
import sqlite3
from pathlib import Path

# ── Base paths ────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = DATA_DIR / "database"

PATHS = {
    "tables_json": DATA_DIR / "tables.json",
    "faiss_questions": DATA_DIR / "faiss_questions.index",
    "faiss_schemas": DATA_DIR / "faiss_schemas.index",
    "q_meta": DATA_DIR / "questions_metadata.pkl",
    "s_meta": DATA_DIR / "schemas_metadata.pkl",
    "all_graphs": DATA_DIR / "all_graphs.pkl",
    "error_memory": DATA_DIR / "error_memory.json",
}


# ══════════════════════════════════════════════════════════════
# 1. DATA LOADERS
# ══════════════════════════════════════════════════════════════

def load_schemas():
    with open(PATHS["tables_json"]) as f:
        tables_info = json.load(f)
    schema_dict = {db["db_id"]: db for db in tables_info}
    print(f"✅ Schemas loaded — {len(schema_dict)} databases")
    return schema_dict


def load_faiss_indexes():
    import faiss
    from sentence_transformers import SentenceTransformer

    q_index = faiss.read_index(str(PATHS["faiss_questions"]))
    s_index = faiss.read_index(str(PATHS["faiss_schemas"]))

    with open(PATHS["q_meta"], "rb") as f:
        q_meta = pickle.load(f)
    with open(PATHS["s_meta"], "rb") as f:
        s_meta = pickle.load(f)

    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    print(
        f"✅ FAISS loaded — questions: {q_index.ntotal:,}  schemas: {s_index.ntotal:,}")
    return {
        "q_index": q_index,
        "s_index": s_index,
        "q_meta": q_meta,
        "s_meta": s_meta,
        "embedder": embedder,
    }


def load_graphs():
    with open(PATHS["all_graphs"], "rb") as f:
        all_graphs = pickle.load(f)
    print(f"✅ Schema graphs loaded — {len(all_graphs)} databases")
    return all_graphs


def load_all():
    print("Loading Text2SQL data...")
    schema_dict = load_schemas()
    faiss_data = load_faiss_indexes()
    all_graphs = load_graphs()
    print("✅ All data loaded\n")
    return schema_dict, faiss_data, all_graphs


# ══════════════════════════════════════════════════════════════
# 2. SCHEMA UTILITIES
# ══════════════════════════════════════════════════════════════

def get_schema_text(db_id: str, schema_dict: dict) -> str:
    schema = schema_dict.get(db_id)
    if not schema:
        return f"Schema not found: {db_id}"

    tables = schema["table_names_original"]
    cols = schema["column_names_original"]
    types = schema["column_types"]
    pks = schema["primary_keys"]
    fks = schema["foreign_keys"]

    lines = [f"Database: {db_id}"]
    for t_idx, table in enumerate(tables):
        table_cols = []
        for i, (t_i, col_name) in enumerate(cols):
            if t_i == t_idx:
                pk_tag = " (PK)" if i in pks else ""
                table_cols.append(f"{col_name}{pk_tag} [{types[i]}]")
        lines.append(f"\nTable: {table}")
        lines.append(f"  Columns: {', '.join(table_cols)}")

    if fks:
        lines.append("\nForeign Keys:")
        for fk in fks:
            col1 = cols[fk[0]][1]
            col2 = cols[fk[1]][1]
            t1 = tables[cols[fk[0]][0]]
            t2 = tables[cols[fk[1]][0]]
            lines.append(f"  {t1}.{col1} → {t2}.{col2}")

    return "\n".join(lines)


def get_valid_columns(db_id: str, schema_dict: dict) -> dict:
    schema = schema_dict.get(db_id, {})
    tables = schema.get("table_names_original", [])
    cols = schema.get("column_names_original", [])
    result = {t.lower(): [] for t in tables}
    for t_i, col_name in cols:
        if t_i >= 0:
            result[tables[t_i].lower()].append(col_name.lower())
    return result


# ══════════════════════════════════════════════════════════════
# 3. SQL EXECUTION
# ══════════════════════════════════════════════════════════════

def execute_sql(db_id: str, sql: str):
    print(f"Executing SQL on DB '{db_id}':\n{sql}\n---")
    db_path = DB_DIR / db_id / f"{db_id}.sqlite"
    if not db_path.exists():
        return None, f"Database not found: {db_path}"
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        conn.close()
        return results, None
    except Exception as e:
        return None, str(e)


# ══════════════════════════════════════════════════════════════
# 4. SCHEMA VALIDATION
# ══════════════════════════════════════════════════════════════

def validate_schema(sql: str, db_id: str, schema_dict: dict) -> tuple:
    valid_cols = get_valid_columns(db_id, schema_dict)
    valid_tables = set(valid_cols.keys())

    for t1, t2 in re.findall(r"\bFROM\s+(\w+)|\bJOIN\s+(\w+)", sql, re.IGNORECASE):
        t = (t1 or t2).lower()
        if t and t not in valid_tables:
            return False, f"Table '{t}' not in database '{db_id}'"

    for table_alias, col in re.findall(r"\b(\w+)\.(\w+)\b", sql):
        if table_alias.upper() in ("SELECT", "FROM", "WHERE", "GROUP",
                                   "ORDER", "HAVING", "LIMIT", "ON"):
            continue
        t_lower = table_alias.lower()
        c_lower = col.lower()
        if t_lower in valid_cols:
            if c_lower not in valid_cols[t_lower] and c_lower != "*":
                return False, f"Column '{col}' not in table '{table_alias}'"

    return True, ""


def level1_syntax_check(sql: str) -> tuple:
    try:
        import sqlparse
        parsed = sqlparse.parse(sql)
        if not parsed or not parsed[0].tokens:
            return False, "Empty or unparseable SQL"
        if not sql.strip().upper().startswith(("SELECT", "WITH")):
            return False, "SQL does not start with SELECT or WITH"
        return True, ""
    except Exception as e:
        return False, str(e)


# ══════════════════════════════════════════════════════════════
# 5. RAG RETRIEVAL
# ══════════════════════════════════════════════════════════════

def retrieve_similar_examples(question: str, db_id: str,
                              faiss_data: dict, k: int = 3) -> list:
    import faiss
    import numpy as np

    embedder = faiss_data["embedder"]
    q_index = faiss_data["q_index"]
    q_meta = faiss_data["q_meta"]

    query_vec = embedder.encode([question]).astype("float32")
    faiss.normalize_L2(query_vec)
    distances, indices = q_index.search(query_vec, k=k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        results.append({
            "question": q_meta["questions"][idx],
            "sql": q_meta["sql_queries"][idx],
            "db_id": q_meta["db_ids"][idx],
            "similarity": float(dist),
        })
    return results


# ══════════════════════════════════════════════════════════════
# 6. STEINER TREE (copied from utils_v4)
# ══════════════════════════════════════════════════════════════

GENERIC_COLUMNS = {
    "country", "name", "id", "code", "type", "year", "date",
    "status", "description", "value", "count", "total", "number",
    "no", "rank", "order", "level", "class", "grade", "size",
    "weight", "height", "age", "sex", "gender", "city", "state",
    "address", "notes"
}


def steiner_tree_approx(G, terminal_tables: list):
    import networkx as nx
    terminals = [t.lower() for t in terminal_tables if t.lower() in G.nodes()]
    if not terminals:
        return nx.Graph()
    if len(terminals) == 1:
        sg = nx.Graph()
        sg.add_node(terminals[0])
        return sg
    connected = [terminals[0]]
    remaining = terminals[1:]
    steiner = nx.Graph()
    steiner.add_node(terminals[0])
    while remaining:
        best_path = best_target = None
        best_len = float("inf")
        for source in connected:
            for target in remaining:
                try:
                    path = nx.shortest_path(G, source, target)
                    if len(path) < best_len:
                        best_len = len(path)
                        best_path = path
                        best_target = target
                except nx.NetworkXNoPath:
                    continue
        if best_path is None:
            break
        for i in range(len(best_path) - 1):
            u, v = best_path[i], best_path[i + 1]
            steiner.add_node(u)
            steiner.add_node(v)
            if G.has_edge(u, v):
                steiner.add_edge(u, v, **G[u][v])
        connected.append(best_target)
        remaining.remove(best_target)
    return steiner


def build_from_clause(steiner) -> str:
    if steiner.number_of_nodes() == 0:
        return "FROM unknown_table"
    if steiner.number_of_edges() == 0:
        return f"FROM {list(steiner.nodes())[0]}"
    join_path = []
    for u, v, data in steiner.edges(data=True):
        join_path.append({"table1": u, "table2": v,
                          "condition": data.get("join_cond", "")})
    if not join_path:
        return f"FROM {list(steiner.nodes())[0]}"
    from_clause = f"FROM {join_path[0]['table1']}"
    visited = {join_path[0]["table1"]}
    for join in join_path:
        if join["table2"] not in visited:
            from_clause += f" JOIN {join['table2']} ON {join['condition']}"
            visited.add(join["table2"])
        elif join["table1"] not in visited:
            from_clause += f" JOIN {join['table1']} ON {join['condition']}"
            visited.add(join["table1"])
    return from_clause


def extract_terminals_schema_linking(question: str, db_id: str,
                                     schema_dict: dict) -> list:
    schema = schema_dict.get(db_id, {})
    tables = schema.get("table_names_original", [])
    cols = schema.get("column_names_original", [])
    q_lower = question.lower()
    q_tokens = set(re.sub(r"[^\w\s]", " ", q_lower).split())
    matched = set()

    for t in tables:
        t_lower = t.lower()
        if t_lower in q_lower:
            matched.add(t_lower)
        elif t_lower.rstrip("s") in q_tokens:
            matched.add(t_lower)
        elif t_lower + "s" in q_tokens:
            matched.add(t_lower)

    for t_idx, col in cols:
        if t_idx < 0:
            continue
        col_lower = col.lower()
        if col_lower in {"id", "name", "type", "date", "year",
                         "code", "no", "number", "count", "total"}:
            continue
        if col_lower in q_lower or col_lower in q_tokens:
            matched.add(tables[t_idx].lower())

    if not matched:
        return [tables[0].lower()] if tables else []
    return list(matched)


# ══════════════════════════════════════════════════════════════
# 7. SQL CLEANING
# ══════════════════════════════════════════════════════════════

def clean_sql_output(raw: str) -> str:
    raw = re.sub(r"```sql|```", "", raw, flags=re.IGNORECASE).strip()
    lines = raw.split("\n")
    sql_lines = []
    for line in lines:
        sql_lines.append(line)
        if ";" in line:
            break
    sql = " ".join(sql_lines).strip()
    if not sql:
        sql = raw
    sql = sql.rstrip(";").strip() + ";"
    return sql


# ══════════════════════════════════════════════════════════════
# 8. BACK-TRANSLATION PROMPTS (from utils_v4)
# ══════════════════════════════════════════════════════════════

def build_back_translation_prompt(sql: str, schema_text: str) -> str:
    return f"""You are an expert SQL reader.

DATABASE SCHEMA:
{schema_text}

SQL QUERY:
{sql}

Describe what this SQL query does in one plain English sentence.
Focus on: what data it retrieves, what tables it uses, what filters/conditions it applies, what aggregations it performs, and how results are grouped or ordered.

Be specific. Do NOT say "it retrieves data from the database."

One sentence only. No SQL. No markdown.

Description:"""


def build_semantic_check_prompt(original_question: str,
                                back_translation: str) -> str:
    return f"""You are a strict SQL validation expert. Your job is to find mistakes.

ORIGINAL QUESTION (what the user asked):
{original_question}

SQL DESCRIPTION (what the generated SQL actually does):
{back_translation}

You must be SKEPTICAL. Look for ANY of these mismatches:
1. WRONG COLUMN: Does the SQL filter or select using a different column than the question implies?
2. WRONG TABLE: Does the SQL pull data from the wrong table?
3. WRONG FILTER: Does the SQL apply a different condition than asked?
4. MISSING/WRONG AGGREGATION: Question asks "how many" but no COUNT? Asks "average" but no AVG?
5. MISSING GROUP BY: Question says "for each" or "per" but SQL doesn't group?
6. WRONG ORDERING: Question asks "highest/most/top" but ORDER BY is wrong or missing?
7. MISSING LIMIT: Question asks for "the one" or "top N" but no LIMIT?
8. LOGIC REVERSAL: SQL does the opposite of what's asked

If you find ANY mismatch, even a subtle one, answer NO.
Only answer YES if the SQL does EXACTLY what the question asks.

Respond in EXACTLY this format:
MATCH: YES or NO
ISSUE: <one of: none, wrong_columns, wrong_tables, wrong_filter, wrong_aggregation, missing_groupby, wrong_ordering, missing_limit, wrong_logic>
EXPLANATION: <one sentence>

Nothing else."""


def build_semantic_repair_prompt(question: str, schema_text: str,
                                 failed_sql: str, back_translation: str,
                                 issue_type: str, explanation: str,
                                 attempt: int) -> str:
    fix_instructions = {
        "wrong_columns": "Your SQL selects the wrong columns. Re-read the question and pick only the columns asked for.",
        "wrong_tables": "Your SQL queries the wrong table(s). Check which tables contain the data the question asks about.",
        "wrong_filter": "Your WHERE clause filters on the wrong condition. Re-read the question to identify the correct filter.",
        "wrong_aggregation": "The question asks for an aggregation but your SQL uses the wrong one or is missing it.",
        "missing_groupby": "The question asks for results 'per' or 'for each' category but your SQL is missing GROUP BY.",
        "wrong_ordering": "The question asks for 'highest/lowest/most' but your SQL has wrong or missing ORDER BY.",
        "missing_limit": "The question asks for 'top N' or 'the one with' but your SQL is missing LIMIT.",
        "wrong_logic": "The overall logic doesn't match the question. Re-read carefully and restructure.",
    }
    fix_hint = fix_instructions.get(
        issue_type, "Fix the SQL so it matches the question intent.")

    return f"""You are an expert SQL debugger. Semantic repair attempt {attempt}.

QUESTION: {question}

YOUR SQL (semantically wrong):
{failed_sql}

WHAT YOUR SQL ACTUALLY DOES:
{back_translation}

PROBLEM: {issue_type}
DETAILS: {explanation}

FIX INSTRUCTION:
{fix_hint}

DATABASE SCHEMA:
{schema_text}

RULES:
- Fix the SQL so it answers the QUESTION correctly
- Only use tables and columns from the DATABASE SCHEMA
- Return ONLY the corrected SQL — no explanation, no markdown

SQL:"""


def parse_semantic_check(response: str) -> dict:
    result = {"match": True, "issue": "none", "explanation": "none"}
    for line in response.strip().split("\n"):
        line = line.strip()
        if line.upper().startswith("MATCH:"):
            val = line.split(":", 1)[1].strip().upper()
            result["match"] = val in ("YES", "TRUE", "Y")
        elif line.upper().startswith("ISSUE:"):
            result["issue"] = line.split(":", 1)[1].strip().lower()
        elif line.upper().startswith("EXPLANATION:"):
            result["explanation"] = line.split(":", 1)[1].strip()
    return result


# ══════════════════════════════════════════════════════════════
# 9. ERROR MEMORY
# ══════════════════════════════════════════════════════════════

class ErrorMemory:
    def __init__(self, max_per_type: int = 5):
        self.memories = {}
        self.global_patterns = {}
        self.max_per_type = max_per_type

    def record(self, db_id, issue_type, question, bad_sql, fixed_sql=""):
        entry = {"issue_type": issue_type, "question": question,
                 "bad_sql": bad_sql, "fixed_sql": fixed_sql}
        if db_id not in self.memories:
            self.memories[db_id] = []
        self.memories[db_id].append(entry)
        if len(self.memories[db_id]) > self.max_per_type * 5:
            self.memories[db_id] = self.memories[db_id][-self.max_per_type * 5:]
        if issue_type not in self.global_patterns:
            self.global_patterns[issue_type] = []
        self.global_patterns[issue_type].append(entry)
        if len(self.global_patterns[issue_type]) > self.max_per_type:
            self.global_patterns[issue_type] = \
                self.global_patterns[issue_type][-self.max_per_type:]

    def get_warnings(self, db_id, question=""):
        from collections import Counter
        warnings = []
        db_errors = self.memories.get(db_id, [])
        if db_errors:
            for issue, count in Counter(
                e["issue_type"] for e in db_errors
            ).most_common(2):
                example = next(e for e in reversed(db_errors)
                               if e["issue_type"] == issue)
                warnings.append(
                    f"- Common mistake on this database: {issue}. "
                    f"Example Q: \"{example['question'][:80]}\""
                )
        for issue, count in sorted(
            {k: len(v) for k, v in self.global_patterns.items()}.items(),
            key=lambda x: -x[1]
        )[:2]:
            if count >= 3:
                warnings.append(
                    f"- Frequent error pattern: {issue} ({count} occurrences)."
                )
        if not warnings:
            return ""
        return "WARNINGS FROM PAST MISTAKES:\n" + "\n".join(warnings) + "\n"

    def get_stats(self):
        from collections import Counter
        all_issues = [e["issue_type"] for db_errors in self.memories.values()
                      for e in db_errors]
        return {"total_errors": len(all_issues),
                "by_type": dict(Counter(all_issues)),
                "databases_affected": len(self.memories)}

    def save(self, path):
        with open(path, "w") as f:
            json.dump({"memories": self.memories,
                       "global_patterns": self.global_patterns}, f, indent=2)

    def load(self, path):
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            self.memories = data.get("memories", {})
            self.global_patterns = data.get("global_patterns", {})
