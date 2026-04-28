"""
pipeline.py — Text2SQL Group 28
=================================
Three pipelines selectable by parameter:

    pipeline="raw"     → zero-shot: schema + question only
    pipeline="rag"     → RAG + 3-level repair loop
    pipeline="rag_bt"  → RAG + repair + back-translation validation

Usage:
    from pipeline import setup, run

    # Call once at startup
    ctx = setup()

    # Then call run() as many times as you want
    result = run("How many singers are from USA?", "concert_singer", ctx)
    result = run("...", "...", ctx, pipeline="rag_bt")

    print(result["sql"])
    print(result["result"])    # actual DB rows
    print(result["pipeline"])
    print(result["repairs"])
"""

import os
import re
from dotenv import load_dotenv
from groq import Groq

from utils_local import (
    load_all,
    get_schema_text,
    get_valid_columns,
    validate_schema,
    level1_syntax_check,
    execute_sql,
    retrieve_similar_examples,
    extract_terminals_schema_linking,
    steiner_tree_approx,
    build_from_clause,
    clean_sql_output,
    build_back_translation_prompt,
    build_semantic_check_prompt,
    build_semantic_repair_prompt,
    parse_semantic_check,
    ErrorMemory,
    PATHS,
)

load_dotenv()

# ── Groq client ───────────────────────────────────────────────
_groq_client = None

def _get_groq():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found. Add it to your .env file.")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def call_llm(prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> str:
    """Single LLM call via Groq. Returns raw text."""
    client = _get_groq()
    response = client.chat.completions.create(
        model       = "llama-3.3-70b-versatile",
        messages    = [{"role": "user", "content": prompt}],
        max_tokens  = max_tokens,
        temperature = temperature,
    )
    return response.choices[0].message.content.strip()


def extract_sql_from_response(raw: str) -> str:
    """Extract and clean SQL from LLM response."""
    raw = re.sub(r"```sql|```", "", raw, flags=re.IGNORECASE).strip()
    lines = raw.split("\n")
    sql_lines = []
    started = False
    for line in lines:
        stripped = line.strip()
        if not started:
            if stripped.upper().startswith(("SELECT", "WITH")):
                started = True
                sql_lines.append(stripped)
        else:
            if stripped == "" and sql_lines:
                break
            sql_lines.append(stripped)
    if sql_lines:
        return " ".join(sql_lines).rstrip(";").strip()
    return raw.strip().rstrip(";")


# ══════════════════════════════════════════════════════════════
# SETUP — call once at startup
# ══════════════════════════════════════════════════════════════

def setup() -> dict:
    """
    Load all data into memory. Call this once when the app starts.
    Returns a context dict to pass into run().
    """
    schema_dict, faiss_data, all_graphs = load_all()

    error_memory = ErrorMemory(max_per_type=5)
    if PATHS["error_memory"].exists():
        error_memory.load(str(PATHS["error_memory"]))
        stats = error_memory.get_stats()
        print(f"✅ Error memory loaded — {stats['total_errors']} past errors")

    return {
        "schema_dict" : schema_dict,
        "faiss_data"  : faiss_data,
        "all_graphs"  : all_graphs,
        "error_memory": error_memory,
    }


# ══════════════════════════════════════════════════════════════
# PROMPT BUILDERS
# ══════════════════════════════════════════════════════════════

def build_raw_prompt(question: str, db_id: str, schema_dict: dict) -> str:
    schema_text = get_schema_text(db_id, schema_dict)
    return f"""You are an expert SQL generator.

DATABASE SCHEMA:
{schema_text}

QUESTION: {question}

Generate the SQL query. Output ONLY the SQL, no explanation, no markdown.

SQL:"""


def build_rag_prompt(question: str, db_id: str,
                     examples: list, schema_dict: dict,
                     warning_text: str = "") -> str:
    schema_text = get_schema_text(db_id, schema_dict)
    few_shot = ""
    for ex in examples[:3]:
        sql = ex.get("sql", ex.get("query", ""))
        few_shot += f"Q: {ex['question']}\nSQL: {sql}\n\n"

    return f"""You are an expert SQL generator for the Spider benchmark.

DATABASE SCHEMA:
{schema_text}

SIMILAR EXAMPLES:
{few_shot}
{warning_text}QUESTION: {question}

Generate the SQL query. Output ONLY the SQL, no explanation, no markdown.

SQL:"""


def build_repair_prompt(question: str, schema_text: str,
                         failed_sql: str, error_msg: str,
                         attempt: int) -> str:
    if "no such column" in error_msg.lower():
        focus = "A column name is wrong. Check the DATABASE SCHEMA — use exact column names."
    elif "no such table" in error_msg.lower():
        focus = "A table name is wrong. Only use tables from the DATABASE SCHEMA."
    elif "syntax error" in error_msg.lower():
        focus = "There is a SQL syntax error. Check parentheses, commas, and keyword order."
    else:
        focus = "Fix the SQL error while keeping the same logical structure."

    return f"""You are an expert SQL debugger. Attempt {attempt}/3.

QUESTION: {question}
FAILED SQL: {failed_sql}
ERROR: {error_msg}
FIX: {focus}

DATABASE SCHEMA:
{schema_text}

Return ONLY the corrected SQL. No explanation. No markdown.

SQL:"""


# ══════════════════════════════════════════════════════════════
# PIPELINE IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════

def _run_raw(question: str, db_id: str, ctx: dict) -> dict:
    """Zero-shot: schema + question, no RAG, no repair."""
    schema_dict = ctx["schema_dict"]
    prompt      = build_raw_prompt(question, db_id, schema_dict)
    raw         = call_llm(prompt, max_tokens=300)
    sql         = extract_sql_from_response(raw)
    result, err = execute_sql(db_id, sql)

    return {
        "sql"      : sql,
        "result"   : result,
        "error"    : err,
        "pipeline" : "raw",
        "repairs"  : 0,
        "bt_match" : None,
        "issue"    : None,
    }


def _run_rag(question: str, db_id: str, ctx: dict) -> dict:
    """RAG + 3-level repair loop."""
    schema_dict  = ctx["schema_dict"]
    faiss_data   = ctx["faiss_data"]
    all_graphs   = ctx["all_graphs"]
    error_memory = ctx["error_memory"]
    schema_text  = get_schema_text(db_id, schema_dict)

    # Warning from error memory
    warning_text = error_memory.get_warnings(db_id, question)

    # RAG retrieval
    examples = retrieve_similar_examples(question, db_id, faiss_data, k=3)

    # Check if multi-table — inject Steiner hint if so
    terminals = extract_terminals_schema_linking(question, db_id, schema_dict)
    from_hint = ""
    if len(terminals) > 1:
        G = all_graphs.get(db_id)
        if G:
            try:
                steiner   = steiner_tree_approx(G, terminals)
                from_hint = f"\nSTEINER JOIN PATH (use this for your FROM clause):\n{build_from_clause(steiner)}\n"
            except Exception:
                pass

    prompt  = build_rag_prompt(question, db_id, examples, schema_dict,
                                warning_text + from_hint)
    raw     = call_llm(prompt, max_tokens=300)
    current = extract_sql_from_response(raw)
    repairs = 0

    # 3-level repair loop
    for attempt in range(1, 4):
        # Level 1 — syntax
        l1_ok, l1_err = level1_syntax_check(current)
        if not l1_ok:
            if attempt < 3:
                current = extract_sql_from_response(
                    call_llm(build_repair_prompt(
                        question, schema_text, current, l1_err, attempt
                    ), max_tokens=300, temperature=0.1)
                )
                repairs += 1
            continue

        # Level 2 — schema
        l2_ok, l2_err = validate_schema(current, db_id, schema_dict)
        if not l2_ok:
            if attempt < 3:
                current = extract_sql_from_response(
                    call_llm(build_repair_prompt(
                        question, schema_text, current, l2_err, attempt
                    ), max_tokens=300, temperature=0.1)
                )
                repairs += 1
            continue

        # Level 3 — execution
        result, exec_err = execute_sql(db_id, current)
        if exec_err:
            if attempt < 3:
                current = extract_sql_from_response(
                    call_llm(build_repair_prompt(
                        question, schema_text, current, exec_err, attempt
                    ), max_tokens=300, temperature=0.1)
                )
                repairs += 1
            continue

        break  # all levels passed

    result, err = execute_sql(db_id, current)
    return {
        "sql"      : current,
        "result"   : result,
        "error"    : err,
        "pipeline" : "rag",
        "repairs"  : repairs,
        "bt_match" : None,
        "issue"    : None,
    }


def _run_rag_bt(question: str, db_id: str, ctx: dict) -> dict:
    """RAG + repair + back-translation semantic validation."""
    schema_dict  = ctx["schema_dict"]
    error_memory = ctx["error_memory"]
    schema_text  = get_schema_text(db_id, schema_dict)

    # Start from RAG result
    base = _run_rag(question, db_id, ctx)
    current = base["sql"]
    repairs = base["repairs"]
    bt_match = None
    issue    = None

    # Only run BT if SQL executes successfully
    _, exec_err = execute_sql(db_id, current)
    if exec_err is None:
        # Back-translate
        bt_prompt = build_back_translation_prompt(current, schema_text)
        bt_desc   = call_llm(bt_prompt, max_tokens=150).strip()

        # Semantic check
        check_prompt = build_semantic_check_prompt(question, bt_desc)
        check_resp   = call_llm(check_prompt, max_tokens=100)
        parsed       = parse_semantic_check(check_resp)

        bt_match = parsed["match"]
        issue    = parsed["issue"]

        # Semantic repair if mismatch
        if not bt_match and issue != "none":
            for sem_attempt in range(1, 3):
                sem_prompt = build_semantic_repair_prompt(
                    question, schema_text, current,
                    bt_desc, issue, parsed["explanation"], sem_attempt
                )
                repaired = extract_sql_from_response(
                    call_llm(sem_prompt, max_tokens=300, temperature=0.1)
                )
                _, rep_err = execute_sql(db_id, repaired)
                if rep_err:
                    continue

                current = repaired
                repairs += 1

                # Re-check
                bt_desc2  = call_llm(
                    build_back_translation_prompt(current, schema_text),
                    max_tokens=150
                ).strip()
                parsed2  = parse_semantic_check(
                    call_llm(build_semantic_check_prompt(question, bt_desc2),
                             max_tokens=100)
                )
                bt_match = parsed2["match"]
                issue    = parsed2["issue"]
                if bt_match:
                    break

            # Record in error memory
            if not bt_match and issue != "none":
                error_memory.record(db_id, issue, question, current)

    result, err = execute_sql(db_id, current)
    return {
        "sql"      : current,
        "result"   : result,
        "error"    : err,
        "pipeline" : "rag_bt",
        "repairs"  : repairs,
        "bt_match" : bt_match,
        "issue"    : issue,
    }


# ══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════

def get_available_databases(ctx: dict) -> list:
    """Return a sorted list of all Spider database IDs available in the loaded data."""
    return sorted(ctx["schema_dict"].keys())


def run(question: str, db_id: str, ctx: dict,
        pipeline: str = "rag_bt") -> dict:
    """
    Run the Text2SQL pipeline.

    Args:
        question : natural language question
        db_id    : Spider database id (e.g. "concert_singer")
        ctx      : context dict from setup()
        pipeline : "raw" | "rag" | "rag_bt"

    Returns dict:
        sql      : generated SQL string
        result   : list of rows from DB execution (or None)
        error    : execution error string (or None)
        pipeline : which pipeline was used
        repairs  : number of repair attempts made
        bt_match : True/False/None (None if BT not run)
        issue    : detected semantic issue type (or None)
    """
    if db_id not in ctx["schema_dict"]:
        return {
            "sql": "", "result": None,
            "error": f"Database '{db_id}' not found.",
            "pipeline": pipeline, "repairs": 0,
            "bt_match": None, "issue": None,
        }

    if pipeline == "raw":
        return _run_raw(question, db_id, ctx)
    elif pipeline == "rag":
        return _run_rag(question, db_id, ctx)
    elif pipeline == "rag_bt":
        return _run_rag_bt(question, db_id, ctx)
    else:
        raise ValueError(f"Unknown pipeline: '{pipeline}'. "
                         f"Choose from: 'raw', 'rag', 'rag_bt'")


# ══════════════════════════════════════════════════════════════
# QUICK TEST — run this file directly to verify setup
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Text2SQL Pipeline — Quick Test")
    print("=" * 60)

    ctx = setup()

    test_cases = [
        ("How many singers are there?",                   "concert_singer", "raw"),
        ("What are the names of all singers from USA?",   "concert_singer", "rag"),
        ("Show the concert name with the most singers.",  "concert_singer", "rag_bt"),
    ]

    for question, db_id, pipeline in test_cases:
        print(f"\nPipeline : {pipeline}")
        print(f"Question : {question}")
        print(f"DB       : {db_id}")

        result = run(question, db_id, ctx, pipeline=pipeline)

        print(f"SQL      : {result['sql']}")
        print(f"Result   : {result['result']}")
        print(f"Repairs  : {result['repairs']}")
        if result["bt_match"] is not None:
            print(f"BT match : {result['bt_match']}  issue: {result['issue']}")
        if result["error"]:
            print(f"Error    : {result['error']}")
        print("-" * 60)
