"use client";

import { useState } from "react";
import { SCHEMAS } from "@/lib/mockData";

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
  const [expandedSchema, setExpandedSchema] = useState<string | null>("concert_singer");

  return (
    <aside className="w-[220px] shrink-0 bg-white border-r border-zinc-100 flex flex-col overflow-y-auto">
      {/* Datasets */}
      <div className="px-3 pt-4">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 px-2 mb-1">Datasets</p>
        {["Spider", "CoSQL"].map((ds) => {
          const id = ds.toLowerCase();
          const active = activeDataset === id;
          return (
            <button
              key={ds}
              onClick={() => setActiveDataset(id)}
              className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm mb-0.5 transition-colors ${
                active ? "bg-zinc-100 text-zinc-900 font-medium" : "text-zinc-500 hover:bg-zinc-50"
              }`}
            >
              <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                <ellipse cx="12" cy="7" rx="9" ry="3.5" />
                <path d="M3 7v10c0 1.933 4.03 3.5 9 3.5s9-1.567 9-3.5V7" />
                <path d="M3 12c0 1.933 4.03 3.5 9 3.5s9-1.567 9-3.5" />
              </svg>
              {ds}
              <span className="ml-auto text-[10px] bg-zinc-100 text-zinc-400 px-1.5 py-0.5 rounded">
                {ds === "Spider" ? "200 DBs" : "conv."}
              </span>
            </button>
          );
        })}
      </div>

      {/* Schema browser */}
      <div className="px-3 pt-4">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 px-2 mb-1">Schema</p>
        {Object.entries(SCHEMAS).map(([schema, tables]) => {
          const isExpanded = expandedSchema === schema;
          const isActive = activeSchema === schema;
          return (
            <div key={schema}>
              <button
                onClick={() => {
                  setActiveSchema(schema);
                  setExpandedSchema(isExpanded ? null : schema);
                }}
                className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm mb-0.5 transition-colors ${
                  isActive ? "bg-zinc-100 text-zinc-900 font-medium" : "text-zinc-500 hover:bg-zinc-50"
                }`}
              >
                <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <path d="M3 9h18M9 9v12" />
                </svg>
                <span className="truncate">{schema}</span>
                <svg
                  className={`w-3 h-3 ml-auto shrink-0 transition-transform ${isExpanded ? "rotate-90" : ""}`}
                  viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}
                >
                  <path d="M9 18l6-6-6-6" />
                </svg>
              </button>
              {isExpanded && (
                <div className="ml-4 pl-2 border-l border-zinc-100 mb-1">
                  {tables.map((t) => (
                    <div key={t} className="flex items-center gap-2 py-1 text-xs text-zinc-400 hover:text-zinc-600 cursor-pointer">
                      <span className="w-1.5 h-1.5 rounded-full bg-zinc-200 shrink-0" />
                      {t}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mx-3 my-3 border-t border-zinc-100" />

      {/* Navigation */}
      <div className="px-3 pb-4">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400 px-2 mb-1">Navigation</p>
        {NAV.map(({ id, label, icon }) => {
          const active = activeNav === id;
          return (
            <button
              key={id}
              onClick={() => setActiveNav(id)}
              className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm mb-0.5 transition-colors ${
                active ? "bg-emerald-50 text-emerald-800 font-medium" : "text-zinc-500 hover:bg-zinc-50"
              }`}
            >
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
