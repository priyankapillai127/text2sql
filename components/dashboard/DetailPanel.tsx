"use client";

import { useState } from "react";
import { Model, EVAL_METRICS, MODEL_LABELS, HISTORY, QueryRecord } from "@/lib/mockData";

interface DetailPanelProps {
  model: Model;
  setModel: (m: Model) => void;
  selected: QueryRecord | null;
  setSelected: (q: QueryRecord) => void;
}

export default function DetailPanel({ model, setModel, selected, setSelected }: DetailPanelProps) {
  const [rag, setRag] = useState(true);
  const [schemaConstrained, setSchemaConstrained] = useState(true);
  const [autoRepair, setAutoRepair] = useState(false);

  const metrics = EVAL_METRICS[model];

  return (
    <aside className="w-[280px] shrink-0 bg-white border-l border-zinc-100 flex flex-col overflow-y-auto">

      {/* Eval Metrics */}
      <div className="p-4 border-b border-zinc-100">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 mb-3">Eval Metrics</p>
        <div className="grid grid-cols-2 gap-2">
          <MetricCard label="Exec Accuracy" value={`${Math.round(metrics.execAcc * 100)}%`} sub="Spider test set" />
          <MetricCard label="Exact Match" value={`${Math.round(metrics.exactMatch * 100)}%`} sub="Spider test set" />
          <MetricCard
            label="RAG Boost"
            value={`+${Math.round(metrics.ragBoost * 100)}%`}
            sub="vs. no retrieval"
            highlight
          />
          <MetricCard label="Queries Run" value={String(metrics.queriesRun)} sub="this session" />
        </div>
      </div>

      {/* Model Selector */}
      <div className="p-4 border-b border-zinc-100">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 mb-3">Model</p>
        <div className="flex flex-col gap-2">
          {(Object.keys(MODEL_LABELS) as Model[]).map((m) => {
            const info = MODEL_LABELS[m];
            const active = model === m;
            return (
              <button
                key={m}
                onClick={() => setModel(m)}
                className={`flex items-center gap-2.5 p-2.5 rounded-xl border text-left transition-all ${
                  active
                    ? "border-emerald-300 bg-emerald-50"
                    : "border-zinc-100 hover:border-zinc-200 hover:bg-zinc-50"
                }`}
              >
                <div className={`w-3.5 h-3.5 rounded-full border-2 shrink-0 flex items-center justify-center ${
                  active ? "border-emerald-600 bg-emerald-600" : "border-zinc-300"
                }`}>
                  {active && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-xs font-semibold ${active ? "text-emerald-900" : "text-zinc-700"}`}>
                    {info.name}
                  </p>
                  <p className="text-[10px] text-zinc-400">{info.sub}</p>
                </div>
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full shrink-0 ${info.tagColor}`}>
                  {info.tag}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Settings / Toggles */}
      <div className="p-4 border-b border-zinc-100">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 mb-3">Settings</p>
        <div className="flex flex-col gap-3">
          <Toggle label="RAG Retrieval" value={rag} onChange={setRag} />
          <Toggle label="Schema-constrained gen." value={schemaConstrained} onChange={setSchemaConstrained} />
          <Toggle label="Auto-repair on failure" value={autoRepair} onChange={setAutoRepair} />
        </div>
      </div>

      {/* Recent Queries */}
      <div className="p-4">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 mb-3">Recent Queries</p>
        <div className="flex flex-col gap-2">
          {HISTORY.map((h) => {
            const isActive = selected?.id === h.id;
            return (
              <button
                key={h.id}
                onClick={() => setSelected(h)}
                className={`text-left p-2.5 rounded-xl border transition-all ${
                  isActive
                    ? "border-zinc-300 bg-zinc-50"
                    : "border-zinc-100 hover:border-zinc-200 hover:bg-zinc-50"
                }`}
              >
                <p className="text-[10px] text-zinc-400 mb-0.5">{h.timestamp}</p>
                <p className="text-xs text-zinc-600 leading-snug line-clamp-2">{h.natural}</p>
                <div className="flex items-center gap-1.5 mt-1.5">
                  <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${
                    h.status === "ok" ? "bg-emerald-50 text-emerald-700" :
                    h.status === "repaired" ? "bg-amber-50 text-amber-700" :
                    "bg-red-50 text-red-600"
                  }`}>
                    {h.status === "ok" ? "✓ ok" : h.status === "repaired" ? "⚡ repaired" : "✗ error"}
                  </span>
                  <span className="text-[9px] text-zinc-400">{MODEL_LABELS[h.model].name}</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </aside>
  );
}

function MetricCard({ label, value, sub, highlight }: {
  label: string; value: string; sub: string; highlight?: boolean;
}) {
  return (
    <div className={`rounded-xl p-3 ${highlight ? "bg-emerald-50" : "bg-zinc-50"}`}>
      <p className="text-[10px] text-zinc-400 mb-1">{label}</p>
      <p className={`text-xl font-bold ${highlight ? "text-emerald-700" : "text-zinc-800"}`}>{value}</p>
      <p className="text-[10px] text-zinc-400">{sub}</p>
    </div>
  );
}

function Toggle({ label, value, onChange }: {
  label: string; value: boolean; onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <button
        onClick={() => onChange(!value)}
        className={`relative w-9 h-5 rounded-full transition-colors shrink-0 ${
          value ? "bg-emerald-600" : "bg-zinc-200"
        }`}
      >
        <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-all ${
          value ? "left-[18px]" : "left-0.5"
        }`} />
      </button>
      <span className="text-xs text-zinc-600">{label}</span>
    </div>
  );
}
