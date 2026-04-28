# ML Pipeline — Text2SQL Group 28 (CSE 573)

This folder contains the Text2SQL pipeline that converts natural language questions into SQL queries using RAG, schema linking, and back-translation validation.

---

## Setup

### 1. Download Data from Google Drive

1. Download `ml_data` folder from Google Drive: https://drive.google.com/drive/folders/1hjzf4Z8a0v8S20WbrLvguIn0i4IVob8b?usp=sharing
2. Rename it to `data` and place inside `ml/`
3. Create `.env` file inside `ml/` with:

```
ml/
└── data/
    ├── database/               ← Spider SQLite databases
    ├── tables.json             ← schema definitions
    ├── all_graphs.pkl          ← Steiner tree schema graphs
    ├── faiss_questions.index   ← FAISS question index
    ├── faiss_schemas.index     ← FAISS schema index
    ├── questions_metadata.pkl  ← question metadata
    └── schemas_metadata.pkl    ← schema metadata
```

### 2. Create a `.env` file
Create a `.env` file inside `ml/` with your Groq API key:

```
GROQ_API_KEY=your_key_here
```

Get a free API key at [console.groq.com](https://console.groq.com).

### 3. Create a virtual environment and install dependencies

```bash
cd ml
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
# .venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

### 4. Test the pipeline

```bash
python pipeline.py
```

You should see SQL queries and results printed for 3 test questions.

---

## Usage

### Basic usage

```python
from pipeline import setup, run

# Call once when the server starts
ctx = setup()

# Call for every user query
result = run(
    question = "How many singers are there?",
    db_id    = "concert_singer",
    ctx      = ctx,
    pipeline = "rag_bt"   # "raw" | "rag" | "rag_bt"
)

print(result["sql"])     # generated SQL
print(result["result"])  # list of rows from DB
print(result["error"])   # None if success
```

### Available pipelines

| Pipeline | Description |
|----------|-------------|
| `raw` | Zero-shot — schema + question only, no examples |
| `rag` | RAG + 3-level repair (syntax, schema, execution) |
| `rag_bt` | RAG + repair + back-translation semantic validation |

### Result dictionary

| Key | Type | Description |
|-----|------|-------------|
| `sql` | str | Generated SQL query |
| `result` | list | Rows returned from database execution |
| `error` | str/None | Execution error if any, else None |
| `pipeline` | str | Which pipeline was used |
| `repairs` | int | Number of repair attempts made |
| `bt_match` | bool/None | Back-translation match result (rag_bt only) |
| `issue` | str/None | Semantic issue detected (rag_bt only) |

### Get available databases

```python
from pipeline import setup, get_available_databases

ctx = setup()
dbs = get_available_databases(ctx)
print(dbs)  # ['academic', 'airline', 'car_1', 'concert_singer', ...]
```

---

## FastAPI Integration

In your `backend/` FastAPI app:

```python
import sys
sys.path.append("../ml")

from fastapi import FastAPI
from pipeline import setup, run, get_available_databases

app = FastAPI()
ctx = setup()  # loads data once on startup

@app.get("/databases")
def databases():
    return {"databases": get_available_databases(ctx)}

@app.post("/query")
def query(question: str, db_id: str, pipeline: str = "rag_bt"):
    result = run(question, db_id, ctx, pipeline=pipeline)
    return result
```

---

## File Structure

```
ml/
├── pipeline.py         ← main entry point (import this in backend)
├── utils_local.py      ← utility functions (schema, FAISS, SQL execution)
├── requirements.txt    ← dependencies
├── .env                ← GROQ_API_KEY (do not commit)
├── .gitignore          ← excludes data/, .env, .venv/
└── data/               ← downloaded from Google Drive (do not commit)
    ├── database/
    ├── tables.json
    ├── all_graphs.pkl
    ├── faiss_questions.index
    ├── faiss_schemas.index
    ├── questions_metadata.pkl
    └── schemas_metadata.pkl
```

---

## Pipeline Architecture

```
User Question
      │
      ▼
Schema Linking (deterministic keyword match → terminal tables)
      │
      ▼
RAG Retrieval (FAISS → top-3 similar examples)
      │
      ▼
Steiner Tree (schema-grounded JOIN path for multi-table queries)
      │
      ▼
LLM Generation
      │
      ▼
Level 1: Syntax Check
Level 2: Schema Validation
Level 3: Execution Check
      │ (repair loop up to 3 attempts if any level fails)
      ▼
Level 4: Back-Translation Validation (rag_bt only)
   LLM describes SQL in English → checks against original question
   If mismatch → targeted semantic repair
      │
      ▼
Final SQL + Result
```

---

## Model

Uses **Llama 3.3 70B** via Groq API (free tier). No local model download required.

---

## Notes

- The `data/` folder is not committed to GitHub — download from Google Drive
- Never commit `.env` — it contains your API key
- `setup()` takes ~10 seconds on first run (loads FAISS indexes and graphs)
- Each `run()` call makes 2-4 API calls to Groq depending on pipeline and repair needs