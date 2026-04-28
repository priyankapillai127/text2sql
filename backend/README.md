# Text2SQL Backend

Python · FastAPI · SQLite · FAISS · Ollama

Full-stack backend for the **SP26 Group 28 – Text2SQL** project.  
Handles schema extraction, RAG-based context retrieval, multi-model SQL generation, execution-feedback repair, and benchmarking.

---

## Project Structure

```
text2sql-backend/
│
├── main.py                         # FastAPI app factory & entry point
├── requirements.txt
├── .env.example                    # Copy to .env and fill in values
│
├── app/
│   ├── api/
│   │   ├── router.py               # Aggregates all sub-routers
│   │   └── routes/
│   │       ├── health.py           # GET /health, GET /health/full
│   │       ├── query.py            # POST /query
│   │       ├── schema.py           # GET /schema/databases, GET /schema/{db}
│   │       ├── rag.py              # POST /rag/build-index, GET /rag/status, etc.
│   │       └── evaluation.py       # POST /evaluate/single, POST /evaluate/batch
│   │
│   ├── core/
│   │   ├── config.py               # Pydantic settings (reads .env)
│   │   ├── exceptions.py           # Domain exceptions → HTTP error codes
│   │   └── logging.py              # Structured logging setup
│   │
│   ├── models/
│   │   └── schemas.py              # All Pydantic request / response models
│   │
│   ├── rag/
│   │   └── rag_service.py          # FAISS index build, load, retrieve
│   │
│   └── services/
│       ├── database_service.py     # Schema extraction + SQL execution
│       ├── llm_service.py          # Ollama / OpenAI / Seq2SQL dispatch
│       ├── repair_service.py       # Execution-feedback repair loop
│       ├── evaluation_service.py   # EM, EX, error categorisation
│       └── query_orchestrator.py   # End-to-end request handler
│
├── scripts/
│   ├── seed_sample_db.py           # Creates concert_singer.sqlite for local dev
│   └── generate_sample_examples.py # Creates spider_train.json for RAG index
│
└── tests/
    ├── test_health.py
    └── test_evaluation.py
```

---

## Quick Start

### 1. Clone & install

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum set OLLAMA_BASE_URL and OLLAMA_MODEL
```

### 3. Seed sample data (local dev only)

```bash
python scripts/seed_sample_db.py          # creates data/databases/concert_singer/
python scripts/generate_sample_examples.py # creates data/spider_train.json
```

> For real evaluation, download the [Spider dataset](https://yale-lily.github.io/spider)
> and place databases under `data/databases/` following Spider's folder layout.

### 4. Start Ollama (separate terminal)

```bash
ollama serve
ollama pull qwen2.5-coder:7b   # or whichever model is set in .env
```

### 5. Run the server

```bash
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## Building the RAG Index

Before RAG-augmented generation works, build the FAISS index once:

```bash
# Via HTTP
curl -X POST http://localhost:8000/api/v1/rag/build-index \
     -H "Content-Type: application/json" \
     -d '{}'

# Or pass a custom path
curl -X POST http://localhost:8000/api/v1/rag/build-index \
     -H "Content-Type: application/json" \
     -d '{"examples_path": "./data/spider_train.json"}'
```

The index persists to `data/faiss_index/` and is reloaded automatically on next startup.

---

## API Summary

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/api/v1/health/` | Liveness probe |
| GET  | `/api/v1/health/full` | Deep component status check |
| POST | `/api/v1/query/` | NL → SQL generation + execution |
| GET  | `/api/v1/schema/databases` | List all databases |
| GET  | `/api/v1/schema/{db}` | Get schema for a database |
| POST | `/api/v1/rag/build-index` | Build FAISS index |
| POST | `/api/v1/rag/load-index` | Reload index from disk |
| GET  | `/api/v1/rag/status` | Index readiness |
| GET  | `/api/v1/rag/retrieve?question=...` | Debug: retrieve examples |
| POST | `/api/v1/evaluate/single` | Single question evaluation |
| POST | `/api/v1/evaluate/batch` | Batch EM + EX scoring |

---

## Model Backends

| Backend | Value | Notes |
|---------|-------|-------|
| Ollama  | `"ollama"` | Local; set `OLLAMA_MODEL` in `.env` |
| OpenAI  | `"openai"` | Requires `OPENAI_API_KEY` in `.env` |
| Seq2SQL | `"seq2sql"` | Stub — integrate real model inference here |

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Frontend Integration Notes (for Next.js team)

- Base URL: `http://localhost:8000/api/v1`
- All endpoints accept and return JSON
- CORS is pre-configured for `http://localhost:3000`
- Import the included Postman collection (`postman_collection.json`) for ready-to-use request examples
- The `QueryResponse` shape always includes `generated_sql`, `execution_result` (array of row objects), and `execution_error` so the UI can branch on success/failure easily
