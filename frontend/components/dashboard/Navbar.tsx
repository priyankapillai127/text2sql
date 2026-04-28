"use client";

import { Model, MODEL_LABELS } from "@/lib/mockData";

export default function Navbar({ model }: { model: Model }) {
  const info = MODEL_LABELS[model];
  return (
    <header className="h-13 bg-white border-b border-zinc-100 flex items-center px-5 gap-4 shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-emerald-700 flex items-center justify-center">
          <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M4 7h16M4 12h10M4 17h13" strokeLinecap="round" />
          </svg>
        </div>
        <span className="text-sm font-bold text-zinc-900 tracking-tight">Text2SQL</span>
        <span className="text-[10px] font-semibold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full tracking-wide">
          RAG
        </span>
      </div>

      <div className="flex-1" />

      {/* Active model pill */}
      <div className="flex items-center gap-2 text-xs text-zinc-500 bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-1.5">
        <span className="w-2 h-2 rounded-full bg-emerald-500" />
        {info.name} · {info.tag}
      </div>

      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-sky-100 text-sky-700 text-xs font-semibold flex items-center justify-center cursor-pointer">
        PP
      </div>
    </header>
  );
}
