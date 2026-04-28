"use client";

import { useState, useEffect } from "react";
import { Model, MODEL_LABELS } from "@/lib/mockData";
import { ragStatus, ragBuildIndex, healthCheck, HealthComponent } from "@/lib/api";

interface QueryHistoryItem {
  question: string;
  sql: string;
  timestamp: string;
}

interface DetailPanelProps {
  model: Model;
  setModel: (m: Model) => void;
  useRag: boolean;
  setUseRag: (v: boolean) => void;
  useSchemaConstrained: boolean;
  setUseSchemaConstrained: (v: boolean) => void;
  autoRepair: boolean;
  setAutoRepair: (v: boolean) => void;
  history: QueryHistoryItem[];
  onSelectHistory: (q: string) => void;
}

export default function DetailPanel({
  model, setModel,
  useRag, setUseRag,
  useSchemaConstrained, setUseSchemaConstrained,
  autoRepair, setAutoRepair,
  history, onSelectHistory,
}: DetailPanelProps) {
  const [healthComponents, setHealthComponents] = useState<HealthComponent[]>([]);
  const [ragIndexed, setRagIndexed]             = useState<number | null>(null);
  const [ragLoaded, setRagLoaded]               = useState<boolean | null>(null);
  const [buildingRag, setBuildingRag]           = useState(false);
  const [ragMsg, setRagMsg]                     = useState<string | null>(null);

  useEffect(() => {
    healthCheck().then((h) => setHealthComponents(h.components)).catch(() => {});
    ragStatus().then((s) => { setRagLoaded(s.loaded); setRagIndexed(s.indexed_count); }).catch(() => {});
  }, []);

  async function handleBuildIndex() {
    setBuildingRag(true);
    setRagMsg(null);
    try {
      const r = await ragBuildIndex();
      setRagMsg(r.message);
      setRagLoaded(true);
      setRagIndexed(r.indexed_count);
    } catch (e) {
      setRagMsg(e instanceof Error ? e.message : "Failed");
    } finally {
      setBuildingRag(false);
    }
  }

  return (
    <aside className="w-[280px] shrink-0 bg-white border-l border-zinc-100 flex flex-col overflow-y-auto">

      {/* Backend Health */}
      <div className="p-4 border-b border-zinc-100">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 mb-3">Backend Health</p>
        {healthComponents.length === 0 ? (
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <span className="w-3 h-3 border-2 border-zinc-200 border-t-zinc-400 rounded-full animate-spin" />
            Checking…
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            {healthComponents.map((c) => (
              <div key={c.name} className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full shrink-0 ${
                  c.status === "ok"       ? "bg-emerald-400" :
                  c.status === "degraded" ? "bg-amber-400"   : "bg-red-400"
                }`} />
                <span className="text-xs text-zinc-600 flex-1 capitalize">{c.name.replace("_", " ")}</span>
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                  c.status === "ok"       ? "bg-emerald-50 text-emerald-700" :
                  c.status === "degraded" ? "bg-amber-50 text-amber-700"     : "bg-red-50 text-red-600"
                }`}>{c.status}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* RAG Status */}
      <div className="p-4 border-b border-zinc-100">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 mb-3">RAG Index</p>
        <div className="flex items-center gap-2 mb-2">
          <span className={`w-2 h-2 rounded-full ${ragLoaded ? "bg-emerald-400" : "bg-zinc-300"}`} />
          <span className="text-xs text-zinc-600">
            {ragLoaded === null ? "Checking…" : ragLoaded ? `Loaded · ${ragIndexed ?? "?"} examples` : "Not loaded"}
          </span>
        </div>
        {!ragLoaded && ragLoaded !== null && (
          <button
            onClick={handleBuildIndex}
            disabled={buildingRag}
            className="w-full text-xs bg-zinc-50 hover:bg-zinc-100 border border-zinc-200 text-zinc-700 font-medium px-3 py-2 rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {buildingRag ? <><span className="w-3 h-3 border-2 border-zinc-300 border-t-zinc-600 rounded-full animate-spin" /> Building…</> : "Build Index"}
          </button>
        )}
        {ragMsg && <p className="text-[11px] text-zinc-500 mt-2">{ragMsg}</p>}
      </div>

      {/* Model Selector */}
      <div className="p-4 border-b border-zinc-100">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 mb-3">Model</p>
        <div className="flex flex-col gap-2">
          {(Object.keys(MODEL_LABELS) as Model[]).map((m) => {
            const info   = MODEL_LABELS[m];
            const active = model === m;
            return (
              <button key={m} onClick={() => setModel(m)}
                className={`flex items-center gap-2.5 p-2.5 rounded-xl border text-left transition-all ${
                  active ? "border-emerald-300 bg-emerald-50" : "border-zinc-100 hover:border-zinc-200 hover:bg-zinc-50"
                }`}>
                <div className={`w-3.5 h-3.5 rounded-full border-2 shrink-0 flex items-center justify-center ${active ? "border-emerald-600 bg-emerald-600" : "border-zinc-300"}`}>
                  {active && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-xs font-semibold ${active ? "text-emerald-900" : "text-zinc-700"}`}>{info.name}</p>
                  <p className="text-[10px] text-zinc-400">{info.sub}</p>
                </div>
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full shrink-0 ${info.tagColor}`}>{info.tag}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Settings */}
      <div className="p-4 border-b border-zinc-100">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 mb-3">Settings</p>
        <div className="flex flex-col gap-3">
          <Toggle label="RAG Retrieval"            value={useRag}               onChange={setUseRag} />
          <Toggle label="Schema-constrained gen."  value={useSchemaConstrained} onChange={setUseSchemaConstrained} />
          <Toggle label="Auto-repair on failure"   value={autoRepair}           onChange={setAutoRepair} />
        </div>
      </div>

      {/* Query History */}
      <div className="p-4">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 mb-3">Recent Queries</p>
        {history.length === 0 ? (
          <p className="text-xs text-zinc-400">No queries yet — run one above!</p>
        ) : (
          <div className="flex flex-col gap-2">
            {history.slice().reverse().map((h, i) => (
              <button key={i} onClick={() => onSelectHistory(h.question)}
                className="text-left p-2.5 rounded-xl border border-zinc-100 hover:border-zinc-200 hover:bg-zinc-50 transition-all">
                <p className="text-[10px] text-zinc-400 mb-0.5">{h.timestamp}</p>
                <p className="text-xs text-zinc-600 leading-snug line-clamp-2">{h.question}</p>
              </button>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center gap-3">
      <button onClick={() => onChange(!value)}
        className={`relative w-9 h-5 rounded-full transition-colors shrink-0 ${value ? "bg-emerald-600" : "bg-zinc-200"}`}>
        <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-all ${value ? "left-[18px]" : "left-0.5"}`} />
      </button>
      <span className="text-xs text-zinc-600">{label}</span>
    </div>
  );
}
