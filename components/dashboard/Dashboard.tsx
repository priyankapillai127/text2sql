"use client";

import { useState } from "react";
import { Model, QueryRecord } from "@/lib/mockData";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";
import QueryPanel from "./QueryPanel";
import DetailPanel from "./DetailPanel";

export default function Dashboard() {
  const [activeDataset, setActiveDataset] = useState("spider");
  const [activeSchema, setActiveSchema]   = useState("concert_singer");
  const [activeNav, setActiveNav]         = useState("query");
  const [model, setModel]                 = useState<Model>("qwen");
  const [selected, setSelected]           = useState<QueryRecord | null>(null);

  return (
    <div className="h-screen flex flex-col bg-zinc-50 overflow-hidden">
      <Navbar model={model} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          activeDataset={activeDataset}
          setActiveDataset={setActiveDataset}
          activeSchema={activeSchema}
          setActiveSchema={setActiveSchema}
          activeNav={activeNav}
          setActiveNav={setActiveNav}
        />
        <main className="flex-1 overflow-y-auto p-5">
          {activeNav === "query" && (
            <QueryPanel selected={selected} setSelected={setSelected} />
          )}
          {activeNav === "evaluation" && (
            <Placeholder title="Evaluation" description="Exec Accuracy & Exact Match charts across models and datasets will appear here." />
          )}
          {activeNav === "failures" && (
            <Placeholder title="Failure Analysis" description="Categorized failure modes (schema linking, join errors, aggregation, etc.) will appear here." />
          )}
          {activeNav === "compare" && (
            <Placeholder title="Model Comparison" description="Side-by-side SQL output from Seq2SQL, Qwen2.5-Coder, and GPT-4o will appear here." />
          )}
        </main>
        <DetailPanel
          model={model}
          setModel={setModel}
          selected={selected}
          setSelected={setSelected}
        />
      </div>
    </div>
  );
}

function Placeholder({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex items-center justify-center h-full min-h-[400px]">
      <div className="text-center max-w-sm">
        <div className="w-12 h-12 rounded-2xl bg-zinc-100 flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6 text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
            <path d="M12 6v6m0 0v6m0-6h6m-6 0H6" strokeLinecap="round" />
          </svg>
        </div>
        <h2 className="text-base font-semibold text-zinc-800 mb-1">{title}</h2>
        <p className="text-sm text-zinc-400">{description}</p>
      </div>
    </div>
  );
}
