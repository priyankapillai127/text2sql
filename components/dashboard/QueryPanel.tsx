"use client";

import { useState } from "react";
import { highlightSQL } from "@/lib/highlight";
import { HISTORY, QueryRecord } from "@/lib/mockData";

interface QueryPanelProps {
  selected: QueryRecord | null;
  setSelected: (q: QueryRecord) => void;
}

export default function QueryPanel({ selected, setSelected }: QueryPanelProps) {
  const [input, setInput] = useState(HISTORY[0].natural);
  const [copied, setCopied] = useState(false);

  const current = selected ?? HISTORY[0];

  function handleRun() {
    // Mock: cycle through history entries based on input match, else default
    const match = HISTORY.find((h) =>
      h.natural.toLowerCase().includes(input.toLowerCase().slice(0, 15))
    );
    setSelected(match ?? HISTORY[0]);
  }

  function handleCopy() {
    navigator.clipboard.writeText(current.sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  const statusConfig = {
    ok:       { label: "Execution OK",  cls: "bg-emerald-50 text-emerald-700" },
    error:    { label: "Exec Error",    cls: "bg-red-50 text-red-600" },
    repaired: { label: "Auto-Repaired", cls: "bg-amber-50 text-amber-700" },
  };

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
            placeholder="Ask a question about your database…"
            className="flex-1 bg-zinc-50 border border-zinc-200 rounded-xl px-3 py-2.5 text-sm text-zinc-800 placeholder-zinc-400 outline-none focus:border-zinc-400 resize-none leading-relaxed font-mono"
          />
          <button
            onClick={handleRun}
            className="shrink-0 bg-emerald-700 hover:bg-emerald-800 active:scale-95 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-all"
          >
            Run ↗
          </button>
        </div>
        <div className="flex gap-2 px-4 pb-3">
          {HISTORY.map((h) => (
            <button
              key={h.id}
              onClick={() => { setInput(h.natural); setSelected(h); }}
              className="text-[11px] text-zinc-400 hover:text-zinc-700 bg-zinc-50 hover:bg-zinc-100 border border-zinc-200 px-2.5 py-1 rounded-lg truncate max-w-[180px] transition-colors"
            >
              {h.natural.slice(0, 32)}…
            </button>
          ))}
        </div>
      </div>

      {/* SQL Output */}
      <div className="bg-white border border-zinc-100 rounded-2xl overflow-hidden shadow-sm">
        <div className="flex items-center gap-2 px-4 py-2.5 border-b border-zinc-100">
          <svg className="w-3.5 h-3.5 text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M3 9h18M9 9v12" strokeLinecap="round" />
          </svg>
          <span className="text-xs font-medium text-zinc-500 flex-1">Generated SQL</span>
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${statusConfig[current.status].cls}`}>
            {statusConfig[current.status].label}
          </span>
          <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-sky-50 text-sky-700">
            RAG: {current.ragExamples} examples
          </span>
          <button
            onClick={handleCopy}
            className="text-[11px] text-zinc-400 hover:text-zinc-700 border border-zinc-200 px-2 py-0.5 rounded transition-colors"
          >
            {copied ? "copied!" : "copy"}
          </button>
        </div>
        <pre className="px-4 py-3 text-[12.5px] leading-7 overflow-x-auto font-mono">
          <code dangerouslySetInnerHTML={{ __html: highlightSQL(current.sql) }} />
        </pre>
      </div>

      {/* Results Table */}
      {current.result && (
        <div className="bg-white border border-zinc-100 rounded-2xl overflow-hidden shadow-sm">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-zinc-100">
            <svg className="w-3.5 h-3.5 text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <path d="M3 10h18M3 14h18M10 3v18M14 3v18" />
              <rect x="3" y="3" width="18" height="18" rx="2" />
            </svg>
            <span className="text-xs font-medium text-zinc-500 flex-1">Query Results</span>
            <span className="text-[11px] text-zinc-400">
              {current.result.rowCount} rows · {current.result.execTimeMs}ms
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-zinc-50">
                  {current.result.columns.map((col) => (
                    <th key={col} className="text-left text-[10px] font-semibold uppercase tracking-wider text-zinc-400 px-4 py-2.5 border-b border-zinc-100">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {current.result.rows.map((row, i) => (
                  <tr key={i} className="hover:bg-zinc-50 transition-colors">
                    {row.map((cell, j) => (
                      <td key={j} className="px-4 py-2.5 text-zinc-700 font-mono text-xs border-b border-zinc-50">
                        {String(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
