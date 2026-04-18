const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://giggling-detector-treble.ngrok-free.dev/api/v1";


// ─── Types ────────────────────────────────────────────────────────────────────

export type ModelBackend = "ollama" | "openai" | "seq2sql";

export interface QueryRequest {
  question: string;
  database_name: string;
  model_backend: ModelBackend;
  use_rag: boolean;
  conversation_history?: string[];
}

export interface QueryResponse {
  question: string;
  generated_sql: string;
  executed: boolean;
  execution_result: Record<string, unknown>[] | null;
  execution_error: string | null;
  repaired: boolean;
  repair_attempts: number;
  rag_context_used: boolean;
  retrieved_examples: string[];
  model_backend: ModelBackend;
  latency_ms: number;
}

export interface SchemaColumn {
  name: string;
  type: string;
  primary_key: boolean;
  nullable: boolean;
}

export interface SchemaTable {
  name: string;
  columns: SchemaColumn[];
  foreign_keys: { column: string; ref_table: string; ref_column: string }[];
}

export interface SchemaResponse {
  database_name: string;
  tables: SchemaTable[];
}

export interface HealthComponent {
  name: string;
  status: "ok" | "degraded" | "unhealthy";
  detail: string | null;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  components: HealthComponent[];
}

export interface RagStatusResponse {
  loaded: boolean;
  indexed_count: number | null;
  index_path: string | null;
}

export interface EvaluationResult {
  question: string;
  ground_truth_sql?: string;
  generated_sql?: string;
  exact_match: boolean;
  execution_accuracy: boolean;
  error_category: string | null;
  error_detail?: string | null;
  latency_ms: number;
}

export interface BatchEvaluationResponse {
  total: number;
  exact_match_score: number;
  execution_accuracy_score: number;
  results: EvaluationResult[];
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json","ngrok-skip-browser-warning": "true", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `API error ${res.status}`);
  }
  return res.json();
}

// ─── Health ───────────────────────────────────────────────────────────────────

export const healthCheck  = ()             => apiFetch<HealthResponse>("/health/");
export const healthFull   = ()             => apiFetch<HealthResponse>("/health/full");

// ─── Schema ───────────────────────────────────────────────────────────────────

export const listDatabases = ()            => apiFetch<string[]>("/schema/databases");
export const getSchema     = (db: string) => apiFetch<SchemaResponse>(`/schema/${db}`);

// ─── RAG ─────────────────────────────────────────────────────────────────────

export const ragStatus     = ()            => apiFetch<RagStatusResponse>("/rag/status");
export const ragBuildIndex = ()            => apiFetch<{ indexed_count: number; message: string }>("/rag/build-index", { method: "POST", body: JSON.stringify({ examples_path: null }) });
export const ragLoadIndex  = ()            => apiFetch<{ loaded: boolean; message: string }>("/rag/load-index", { method: "POST" });

// ─── Query ────────────────────────────────────────────────────────────────────

export const generateSQL = (body: QueryRequest) =>
  apiFetch<QueryResponse>("/query/", { method: "POST", body: JSON.stringify(body) });

// ─── Evaluate ─────────────────────────────────────────────────────────────────

export interface SingleEvalRequest {
  database_name: string;
  question: string;
  ground_truth_sql: string;
  model_backend: ModelBackend;
  use_rag: boolean;
}

export const evaluateSingle = (body: SingleEvalRequest) =>
  apiFetch<EvaluationResult>("/evaluate/single", { method: "POST", body: JSON.stringify(body) });

export interface BatchEvalItem extends SingleEvalRequest {}

export interface BatchEvalRequest {
  model_backend: ModelBackend;
  use_rag: boolean;
  items: BatchEvalItem[];
}

export const evaluateBatch = (body: BatchEvalRequest) =>
  apiFetch<BatchEvaluationResponse>("/evaluate/batch", { method: "POST", body: JSON.stringify(body) });
