# Evaluation Summary — Text2SQL Group 28
## CSE 573: Semantic Web Mining | Arizona State University

---

## Overview

This folder contains all evaluation results, metrics, and diagnostics for the
Text2SQL pipeline evaluated on Spider and CoSQL benchmark datasets.

---

## Datasets

| Dataset | Split | Examples | Notes |
|---------|-------|----------|-------|
| Spider  | Dev   | 1034     | Cross-domain, single-turn |
| CoSQL   | Dev   | 1007     | Conversational, with dialogue history |

---

## Systems Evaluated

| System | Description | Datasets |
|--------|-------------|----------|
| Seq2SQL | Classical baseline (WikiSQL-trained) | Spider only |
| Qwen2.5-Coder Zero-Shot | Direct generation, no retrieval | Spider + CoSQL |
| Qwen2.5-Coder + RAG | Schema linking + RAG + Steiner tree + repair | Spider + CoSQL |
| Qwen2.5-Coder + RAG + Repair + SV | Full pipeline + semantic validation + error memory | Spider + CoSQL |
| GPT-4o | Frontier reference upper bound | Spider only |

SV = Semantic Validation via back-translation.

---

## Spider Dev Set Results (1034 examples)

### Overall

| System | EM | EX |
|--------|----|----|
| Seq2SQL | 3.0% | 9.3% |
| Qwen Zero-Shot | 17.9% | 72.7% |
| Qwen + RAG | 38.7% | 74.5% |
| Qwen + RAG + Repair + SV | 32.7% | 74.9% |
| GPT-4o | 60.0% | 82.0% |

EM = Exact Match (normalized: lowercased, whitespace-stripped).
EX = Execution Accuracy (result rows compared against gold SQL output).

### Execution Accuracy by Hardness

| Hardness | n | Zero-Shot | RAG+Repair | RAG+Repair+SV | GPT-4o |
|----------|---|-----------|------------|----------------|--------|
| Easy | 333 | 88.0% | 87.4% | 88.9% | 92.0% |
| Medium | 355 | 71.8% | 76.6% | 76.9% | 81.0% |
| Hard | 187 | 54.0% | 63.6% | 63.6% | 75.0% |
| Extra Hard | 159 | 64.8% | 55.3% | 54.1% | 68.0% |

---

## CoSQL Dev Set Results (1007 turns, with dialogue history)

### Overall

| System | EX |
|--------|----|
| Qwen Zero-Shot | 52.9% |
| Qwen + RAG | 61.3% |
| Qwen + RAG + Repair + SV | 62.1% |

### Execution Accuracy by Hardness

| Hardness | n | Zero-Shot | RAG+Repair | RAG+Repair+SV |
|----------|---|-----------|------------|----------------|
| Easy | 657 | 67.3% | 70.9% | 71.8% |
| Medium | 385 | 47.3% | 59.2% | 60.1% |
| Hard | 191 | 30.4% | 43.5% | 44.5% |
| Extra Hard | 174 | 35.6% | 49.4% | 50.2% |

Note: Unlike Spider, RAG+Repair improves consistently across ALL CoSQL hardness
levels including extra hard. This is because CoSQL extra hard difficulty comes
from conversational context complexity, not nested SQL structure — RAG-retrieved
conversational examples help the model handle context references correctly.

---

## Result Files

| File | Contents |
|------|----------|
| comparison_full.json | Spider ZS + RAG results (1034 examples each) |
| v6_results.json | RAG+Repair+SV results (1034 examples) |
| cosql_history.json | CoSQL results (1007 turns) |
| error_memory.json | 60 categorized error patterns from V6 run |

### comparison_full.json structure
```
{
  "zeroshot": {
    "predictions": [...],   // generated SQL strings
    "em": 0,                // raw EM count (strict string match)
    "ex": 0.727,            // execution accuracy
    "by_hard": {            // EX per example by hardness
      "easy": [...],
      "medium": [...],
      "hard": [...],
      "extra hard": [...]
    },
    "errors": [...]
  },
  "rag_repair": { ... },    // same structure
  "references": [...],      // gold SQL strings
  "db_ids": [...]           // database ids per example
}
```

### v6_results.json structure (proposed pipeline)
```
{
  "predictions": [...],
  "em": int,
  "ex": int,
  "by_hard": { "easy": [], "medium": [], "hard": [], "extra hard": [] },
  "bt_stats": {
    "checks": 998,
    "mismatches": 60,
    "semantic_repairs": 131
  },
  "errors": [...],
  "n_completed": 1034
}
```

---

## Evaluation Metrics

### Exact Match (EM)
Normalized string comparison between predicted and gold SQL.
Normalization: lowercase, strip whitespace, remove trailing semicolons.
Two SQL queries that are logically equivalent but written differently
(e.g. different alias names, different column order in SELECT) will
count as a mismatch under EM.

### Execution Accuracy (EX)
Both predicted and gold SQL are executed against the Spider SQLite databases.
Result rows are sorted and compared. If they match, the example is correct.
This is the primary metric used in the Spider leaderboard and in this project.

---

## Reproducibility

All experiments were run on Google Colab with:
- GPU: NVIDIA A100 (96GB VRAM)
- Model: Qwen2.5-Coder-7B-Instruct (4-bit quantized via bitsandbytes)
- Embeddings: all-MiniLM-L6-v2 (sentence-transformers)
- FAISS: CPU index, flat L2

Full experiment code is in notebooks/Text2SQL_Evaluation.ipynb.
Pipeline code is in ../pipeline.py and ../utils_local.py.

---

## References

- Yu et al. (2018). Spider: A Large-Scale Human-Labeled Dataset for
  Complex and Cross-Domain Semantic Parsing and Text-to-SQL Task. EMNLP.
- Yu et al. (2019). CoSQL: A Conversational Text-to-SQL Challenge. EMNLP.
- Zhong et al. (2017). Seq2SQL: Generating Structured Queries from Natural
  Language using Reinforcement Learning. arXiv:1709.00103.
- Lewis et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive
  NLP Tasks. NeurIPS.
- Chen et al. (2023). Teaching Large Language Models to Self-Debug.
  arXiv:2304.05128.
- Qwen Team (2024). Qwen2.5-Coder Technical Report. arXiv:2409.12186.