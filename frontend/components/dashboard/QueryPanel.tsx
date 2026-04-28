"use client";

import { useState } from "react";
import { highlightSQL } from "@/lib/highlight";
import { generateSQL, QueryResponse, ModelBackend } from "@/lib/api";

interface QueryPanelProps {
  database: string;
  model: ModelBackend;
  useRag: boolean;
  useSchemaConstrained: boolean;
  conversationHistory: string[];
  onQueryComplete: (q: string, sql: string) => void;
}

export default function QueryPanel({
  database, model, useRag, conversationHistory, onQueryComplete,
}: QueryPanelProps) {
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [result, setResult]     = useState<QueryResponse | null>(null);
  const [copied, setCopied]     = useState(false);

  async function handleRun() {
    if (!input.trim() || !database) return;
    setLoading(true);
    setError(null);
    try {
      const res = await generateSQL({
        question: input.trim(),
        database_name: database,
        model_backend: model,
        use_rag: useRag,
        conversation_history: conversationHistory,
      });
      setResult(res);
      onQueryComplete(input.trim(), res.generated_sql);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  function handleCopy() {
    if (!result) return;
    navigator.clipboard.writeText(result.generated_sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  const resultRows = result?.execution_result ?? [];
  const columns    = resultRows.length > 0 ? Object.keys(resultRows[0]) : [];

  const statusConfig = {
    ok:       { label: "Execution OK",  cls: "bg-emerald-50 text-emerald-700" },
    error:    { label: "Exec Error",    cls: "bg-red-50 text-red-600" },
    repaired: { label: "Auto-Repaired", cls: "bg-amber-50 text-amber-700" },
  };

  const status = !result ? null
    : result.repaired         ? "repaired"
    : result.execution_error  ? "error"
    : "ok";

  return (
    <div className="flex flex-col gap-4">

      {/* Query input */}
      <div className="bg-white border border-zinc-100 rounded-2xl overflow-hidden shadow-sm">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 px-4 pt-3 pb-1">
          Natural Language Query
        </p>
        <div className="flex items-start gap-2 px-3 pb-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleRun(); } }}
            rows={2}
            placeholder={database ? `Ask a question about "${database}"…` : "Select a database first…"}
            disabled={!database || loading}
            className="flex-1 bg-zinc-50 border border-zinc-200 rounded-xl px-3 py-2.5 text-sm text-zinc-800 placeholder-zinc-400 outline-none focus:border-zinc-400 resize-none leading-relaxed font-mono disabled:opacity-50"
          />
          <button
            onClick={handleRun}
            disabled={!input.trim() || !database || loading}
            className="shrink-0 bg-emerald-700 hover:bg-emerald-800 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-all flex items-center gap-2"
          >
            {loading ? (
              <><span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" /> Running…</>
            ) : "Run ↗"}
          </button>
        </div>
        {!database && (
          <p className="text-xs text-amber-600 bg-amber-50 px-4 py-2 border-t border-amber-100">
            ⚠ No database loaded yet — waiting for backend connection
          </p>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border border-red-100 rounded-2xl px-4 py-3 text-sm text-red-700">
          <span className="font-semibold">Error: </span>{error}
        </div>
      )}

      {/* SQL Output */}
      {result && (
        <div className="bg-white border border-zinc-100 rounded-2xl overflow-hidden shadow-sm">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-zinc-100">
            <svg className="w-3.5 h-3.5 text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 9v12" strokeLinecap="round" />
            </svg>
            <span className="text-xs font-medium text-zinc-500 flex-1">Generated SQL</span>
            {status && (
              <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${statusConfig[status].cls}`}>
                {statusConfig[status].label}
              </span>
            )}
            {result.rag_context_used && (
              <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-sky-50 text-sky-700">
                RAG: {result.retrieved_examples.length} examples
              </span>
            )}
            <span className="text-[10px] text-zinc-400">{result.latency_ms.toFixed(0)}ms</span>
            <button onClick={handleCopy} className="text-[11px] text-zinc-400 hover:text-zinc-700 border border-zinc-200 px-2 py-0.5 rounded transition-colors">
              {copied ? "copied!" : "copy"}
            </button>
          </div>
          <pre className="px-4 py-3 text-[12.5px] leading-7 overflow-x-auto font-mono">
            <code dangerouslySetInnerHTML={{ __html: highlightSQL(result.generated_sql) }} />
          </pre>

          {/* RAG examples used */}
          {result.retrieved_examples.length > 0 && (
            <details className="border-t border-zinc-100">
              <summary className="px-4 py-2 text-[11px] text-zinc-400 cursor-pointer hover:text-zinc-600 select-none">
                Retrieved RAG examples ({result.retrieved_examples.length})
              </summary>
              <div className="px-4 pb-3 flex flex-col gap-1">
                {result.retrieved_examples.map((ex, i) => (
                  <p key={i} className="text-[11px] text-zinc-500 font-mono bg-zinc-50 rounded px-2 py-1">{ex}</p>
                ))}
              </div>
            </details>
          )}

          {/* Execution error */}
          {result.execution_error && (
            <div className="border-t border-red-100 bg-red-50 px-4 py-2.5 text-xs text-red-700 font-mono">
              {result.execution_error}
            </div>
          )}
        </div>
      )}

      {/* Results Table */}
      {result?.executed && resultRows.length > 0 && (
        <div className="bg-white border border-zinc-100 rounded-2xl overflow-hidden shadow-sm">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-zinc-100">
            <svg className="w-3.5 h-3.5 text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <path d="M3 10h18M3 14h18M10 3v18M14 3v18" /><rect x="3" y="3" width="18" height="18" rx="2" />
            </svg>
            <span className="text-xs font-medium text-zinc-500 flex-1">Query Results</span>
            <span className="text-[11px] text-zinc-400">{resultRows.length} rows</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-zinc-50">
                  {columns.map((col) => (
                    <th key={col} className="text-left text-[10px] font-semibold uppercase tracking-wider text-zinc-400 px-4 py-2.5 border-b border-zinc-100">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {resultRows.map((row, i) => (
                  <tr key={i} className="hover:bg-zinc-50 transition-colors">
                    {columns.map((col) => (
                      <td key={col} className="px-4 py-2.5 text-zinc-700 font-mono text-xs border-b border-zinc-50">
                        {String(row[col] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty result */}
      {result?.executed && resultRows.length === 0 && !result.execution_error && (
        <div className="bg-white border border-zinc-100 rounded-2xl px-4 py-8 text-center shadow-sm">
          <p className="text-sm text-zinc-400">Query executed successfully — no rows returned.</p>
        </div>
      )}
    </div>
  );
}
