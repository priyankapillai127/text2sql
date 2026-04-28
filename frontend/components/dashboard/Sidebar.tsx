"use client";

import { useState, useEffect } from "react";
import { listDatabases, getSchema, SchemaTable } from "@/lib/api";

const NAV = [
  { id: "query",      label: "Query",      icon: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" },
  { id: "evaluation", label: "Evaluation", icon: "M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" },
  { id: "failures",   label: "Failures",   icon: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" },
  { id: "compare",    label: "Compare",    icon: "M4 6h16M4 10h16M4 14h16M4 18h16" },
];

interface SidebarProps {
  activeDataset: string;
  setActiveDataset: (d: string) => void;
  activeSchema: string;
  setActiveSchema: (s: string) => void;
  activeNav: string;
  setActiveNav: (n: string) => void;
}

export default function Sidebar({
  activeDataset, setActiveDataset,
  activeSchema, setActiveSchema,
  activeNav, setActiveNav,
}: SidebarProps) {
  const [databases, setDatabases]         = useState<string[]>([]);
  const [tables, setTables]               = useState<SchemaTable[]>([]);
  const [expandedDb, setExpandedDb]       = useState<string | null>(null);
  const [loadingDbs, setLoadingDbs]       = useState(true);
  const [loadingSchema, setLoadingSchema] = useState(false);

  useEffect(() => {
    listDatabases()
      .then((dbs) => {
        setDatabases(dbs);
        if (dbs.length > 0) { setActiveSchema(dbs[0]); setExpandedDb(dbs[0]); }
      })
      .catch(() => setDatabases([]))
      .finally(() => setLoadingDbs(false));
  }, []);

  useEffect(() => {
    if (!expandedDb) return;
    setLoadingSchema(true);
    getSchema(expandedDb)
      .then((s) => setTables(s.tables))
      .catch(() => setTables([]))
      .finally(() => setLoadingSchema(false));
  }, [expandedDb]);

  return (
    <aside className="w-[220px] shrink-0 bg-white border-r border-zinc-100 flex flex-col overflow-y-auto">
      <div className="px-3 pt-4">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 px-2 mb-1">Datasets</p>
        {["spider", "cosql"].map((ds) => {
          const active = activeDataset === ds;
          return (
            <button key={ds} onClick={() => setActiveDataset(ds)}
              className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm mb-0.5 transition-colors ${active ? "bg-zinc-100 text-zinc-900 font-medium" : "text-zinc-500 hover:bg-zinc-50"}`}>
              <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                <ellipse cx="12" cy="7" rx="9" ry="3.5" />
                <path d="M3 7v10c0 1.933 4.03 3.5 9 3.5s9-1.567 9-3.5V7" />
                <path d="M3 12c0 1.933 4.03 3.5 9 3.5s9-1.567 9-3.5" />
              </svg>
              {ds === "spider" ? "Spider" : "CoSQL"}
              <span className="ml-auto text-[10px] bg-zinc-100 text-zinc-400 px-1.5 py-0.5 rounded">
                {ds === "spider" ? "200 DBs" : "conv."}
              </span>
            </button>
          );
        })}
      </div>

      <div className="px-3 pt-4">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 px-2 mb-1">Schema</p>
        {loadingDbs && (
          <div className="flex items-center gap-2 px-2 py-2 text-xs text-zinc-400">
            <span className="w-3 h-3 border-2 border-zinc-200 border-t-zinc-400 rounded-full animate-spin" />
            Loading databases…
          </div>
        )}
        {!loadingDbs && databases.length === 0 && (
          <p className="text-xs text-zinc-400 px-2 py-1">No databases found</p>
        )}
        {databases.map((db) => {
          const isExpanded = expandedDb === db;
          const isActive   = activeSchema === db;
          return (
            <div key={db}>
              <button
                onClick={() => { setActiveSchema(db); setExpandedDb(isExpanded ? null : db); }}
                className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm mb-0.5 transition-colors ${isActive ? "bg-zinc-100 text-zinc-900 font-medium" : "text-zinc-500 hover:bg-zinc-50"}`}>
                <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                  <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 9v12" />
                </svg>
                <span className="truncate">{db}</span>
                <svg className={`w-3 h-3 ml-auto shrink-0 transition-transform ${isExpanded ? "rotate-90" : ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path d="M9 18l6-6-6-6" />
                </svg>
              </button>
              {isExpanded && (
                <div className="ml-4 pl-2 border-l border-zinc-100 mb-1">
                  {loadingSchema ? (
                    <div className="flex items-center gap-2 py-1.5 text-xs text-zinc-400">
                      <span className="w-2.5 h-2.5 border-2 border-zinc-200 border-t-zinc-400 rounded-full animate-spin" /> Loading…
                    </div>
                  ) : tables.map((t) => (
                    <div key={t.name} className="flex items-center gap-2 py-1 text-xs text-zinc-400 hover:text-zinc-600 cursor-pointer">
                      <span className="w-1.5 h-1.5 rounded-full bg-zinc-200 shrink-0" />
                      {t.name}
                      <span className="ml-auto text-[9px] text-zinc-300">{t.columns.length} cols</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mx-3 my-3 border-t border-zinc-100" />

      <div className="px-3 pb-4">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 px-2 mb-1">Navigation</p>
        {NAV.map(({ id, label, icon }) => {
          const active = activeNav === id;
          return (
            <button key={id} onClick={() => setActiveNav(id)}
              className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm mb-0.5 transition-colors ${active ? "bg-emerald-50 text-emerald-800 font-medium" : "text-zinc-500 hover:bg-zinc-50"}`}>
              <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
              </svg>
              {label}
            </button>
          );
        })}
      </div>
    </aside>
  );
}
