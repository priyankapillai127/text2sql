# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository structure

This is a monorepo with two independent sub-projects:

- `frontend/` — Next.js 14 dashboard (TypeScript + Tailwind CSS)
- `ml/` — Python Text2SQL pipeline (Groq API + FAISS + SQLite)

There is no shared build system. Each sub-project must be run from its own directory.

## Frontend

All commands must be run from `frontend/`:

```bash
cd frontend
npm run dev      # dev server at http://localhost:3000
npm run build    # production build
npm run lint     # ESLint
```

The frontend talks to a backend API. The base URL defaults to an ngrok tunnel and can be overridden via `NEXT_PUBLIC_API_URL` in `frontend/.env.local`.

### Frontend architecture

- `app/page.tsx` renders `<Dashboard />` — the single entry point.
- `components/dashboard/Dashboard.tsx` owns all shared state (model selection, RAG toggle, query history, active schema/dataset) and composes four child components:
  - `Navbar` — top bar showing active model
  - `Sidebar` — dataset/schema picker and nav links (query, evaluation, failures, compare)
  - `QueryPanel` — main query input and result display
  - `DetailPanel` — right panel for settings and query history
- `lib/api.ts` — all typed API calls. The backend exposes `/health`, `/schema`, `/rag`, `/query`, and `/evaluate` endpoints.
- `lib/mockData.ts` — static mock data and the `Model` type (`"qwen" | "gpt4o" | "seq2sql"`). The `ModelBackend` type in `api.ts` (`"ollama" | "openai" | "seq2sql"`) is what gets sent to the API; `Dashboard.tsx` maps between the two.
- Evaluation, Failure Analysis, and Model Comparison nav views are currently placeholder stubs in `Dashboard.tsx`.

## ML pipeline

All commands must be run from `ml/`:

```bash
cd ml
source .venv/bin/activate
pip install -r requirements.txt   # first-time setup

python pipeline.py                 # quick self-test across all three pipelines
```

Requires a `ml/.env` file with `GROQ_API_KEY=<your key>`.

Requires the `ml/data/` folder (not committed). Download from the Google Drive link in `ml/REAME.md`, rename to `data/`, and place inside `ml/`. It contains FAISS indexes, schema graphs (NetworkX pickles), Spider SQLite databases, and `tables.json`.

### ML architecture

`pipeline.py` exposes two functions:

```python
ctx = setup()                                         # call once at startup
result = run(question, db_id, ctx, pipeline="rag_bt") # call per query
```

Three pipeline modes, selected by the `pipeline` parameter:

| Mode | Description |
|------|-------------|
| `raw` | Zero-shot: schema + question, single LLM call |
| `rag` | RAG retrieval (FAISS, k=3) + 3-level repair loop (syntax → schema → execution) |
| `rag_bt` | `rag` + back-translation semantic validation and repair |

`utils_local.py` provides all utilities: data loaders, schema text formatting, SQL execution against Spider SQLite DBs, FAISS retrieval, Steiner tree JOIN path inference, SQL validation, back-translation prompts, and the `ErrorMemory` class (persisted to `data/error_memory.json`) that records past semantic failures and injects warnings into future prompts.

The LLM is `llama-3.3-70b-versatile` via Groq. All calls go through `pipeline.call_llm()`.