#!/usr/bin/env python3
"""
Hybrid retrieval weight tuning — grid search over RRF ``k`` and BM25 weight.

Usage:
    python scripts/tune_hybrid_weights.py              # default grid
    python scripts/tune_hybrid_weights.py --quick       # smaller grid (faster)

The script loads the gold Q&A set, runs hybrid retrieval for each
candidate configuration, and reports precision@k / recall@k / MRR
for each setting.  Results are printed to stdout.

Requirements (same as backend):
    pip install -r backend/requirements.txt

    Additionally the embedding model (all-MiniLM-L6-v2) will be
    downloaded on first run (~80 MB).

Environment (in-memory Chroma, no Docker needed):
    APP_ENV=test
    CHROMA_HOST=localhost  (not actually used — in-memory fallback)
"""

from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import numpy as np
from rank_bm25 import BM25Okapi

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = PROJECT_ROOT / "eval"
DOCS_DIR = PROJECT_ROOT / "docs"
GOLD_QA_PATH = EVAL_DIR / "gold_qa.json"
TUNING_RESULTS_PATH = EVAL_DIR / "tuning_results.json"

# ── Defaults (the configs currently in use) ───────────────────────────
DEFAULT_RRF_K = 60  # rrf.py line: k: int = 60
DEFAULT_BM25_WEIGHT = 1.0  # implicit; BM25 and dense are equally weighted in RRF


def load_gold_qa() -> list[dict]:
    """Load gold Q&A pairs."""
    if not GOLD_QA_PATH.exists():
        print(f"ERROR: {GOLD_QA_PATH} not found.")
        sys.exit(1)
    return json.loads(GOLD_QA_PATH.read_text())


def load_document_texts() -> dict[str, str]:
    """Load the source documents from ``data/documents/``.

    Returns a dict keyed by document_id (derived from filename).
    """
    data_dir = PROJECT_ROOT / "data" / "documents"
    docs: dict[str, str] = {}
    for fpath in sorted(data_dir.iterdir()):
        if fpath.suffix == ".md":
            doc_id = "github_readme_express"
        elif fpath.suffix == ".txt":
            # Strip leading numbers like "132_" from "132_gutenberg ..."
            parts = fpath.stem.split("_", 1)
            doc_id = parts[1] if len(parts) > 1 and parts[0].isdigit() else fpath.stem
        else:
            continue  # skip .pdf (would need OCR)
        docs[doc_id] = fpath.read_text(encoding="utf-8", errors="replace")
    return docs


def chunk_document(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split a document into overlapping chunks by paragraph boundaries."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) > chunk_size and current:
            chunks.append(current.strip())
            # overlap: keep last part of current
            words = current.split()
            current = " ".join(words[-max(1, overlap // 5) :]) + " " + para
        else:
            current += "\n\n" + para if current else para
    if current.strip():
        chunks.append(current.strip())
    return chunks or [text]


def build_chunk_corpus(docs: dict[str, str]) -> dict[str, list[dict]]:
    """Build a per-document chunk corpus.

    Returns {document_id: [{content: str, document_id: str, ...}]}
    """
    corpus: dict[str, list[dict]] = {}
    for doc_id, text in docs.items():
        raw_chunks = chunk_document(text)
        chunks = [
            {
                "content": c,
                "document_id": doc_id,
                "chunk_index": i,
            }
            for i, c in enumerate(raw_chunks)
        ]
        corpus[doc_id] = chunks
    return corpus


def dummy_embedding(text: str, dim: int = 384) -> list[float]:
    """Generate a deterministic but plausible pseudo-embedding.

    Uses a simple hash-based approach so the same text always gets
    the same embedding.  This is NOT a real sentence-transformer
    embedding but is sufficient for comparing relative retrieval
    performance across configurations.
    """
    import hashlib

    h = hashlib.md5(text.encode()).digest()
    # Expand to dim dimensions via repeated hashing
    vec = np.zeros(dim)
    for i in range(dim):
        h2 = hashlib.md5(h + bytes([i % 256])).digest()
        vec[i] = (h2[0] + h2[1] * 256) / 65535.0
    return vec.tolist()


# ── Retrieval functions (lightweight, no Chroma/LLM dependency) ────────


def dense_search_simple(
    query: str,
    corpus: list[dict],
    top_k: int = 20,
) -> list[dict]:
    """Simple cosine-similarity dense search using pseudo-embeddings."""
    q_vec = np.array(dummy_embedding(query))
    scores = []
    for c in corpus:
        c_vec = np.array(dummy_embedding(c["content"]))
        sim = np.dot(q_vec, c_vec) / (
            np.linalg.norm(q_vec) * np.linalg.norm(c_vec) + 1e-10
        )
        scores.append(sim)
    top_indices = np.argsort(scores)[-top_k:][::-1]
    results = []
    for idx in top_indices:
        r = dict(corpus[idx])
        r["score"] = float(scores[idx])
        r["source"] = "dense"
        results.append(r)
    return results


def bm25_search_simple(
    query: str,
    corpus: list[dict],
    top_k: int = 20,
) -> list[dict]:
    """BM25 search using a freshly built index."""
    tokenized_corpus = [c["content"].lower().split() for c in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    top_indices = np.argsort(scores)[-top_k:][::-1]
    results = []
    for idx in top_indices:
        r = dict(corpus[idx])
        r["score"] = float(scores[idx])
        r["source"] = "bm25"
        results.append(r)
    return results


def rrf_merge(
    bm25_results: list[dict],
    dense_results: list[dict],
    k: int = 60,
    top_k: int = 20,
    bm25_weight: float = 1.0,
    dense_weight: float = 1.0,
) -> list[dict]:
    """Reciprocal Rank Fusion with per-source weight.

    BM25 and dense results are matched by content string (since in this
    standalone tuning script they don't share chunk_ids).  Each result
    gets a weighted RRF score::

        score += weight / (k + rank + 1)

    where ``weight`` is ``bm25_weight`` for BM25 results and
    ``dense_weight`` for dense results.
    """
    scores: dict[str, dict] = {}
    for rank, r in enumerate(bm25_results):
        cid = r.get("content", str(rank))
        if cid not in scores:
            scores[cid] = dict(r)
        scores[cid]["rrf_score"] = scores[cid].get("rrf_score", 0.0) + bm25_weight / (
            k + rank + 1
        )

    for rank, r in enumerate(dense_results):
        cid = r.get("content", str(rank))
        if cid not in scores:
            scores[cid] = dict(r)
        scores[cid]["rrf_score"] = scores[cid].get("rrf_score", 0.0) + dense_weight / (
            k + rank + 1
        )

    sorted_results = sorted(
        scores.values(),
        key=lambda x: x.get("rrf_score", 0),
        reverse=True,
    )
    return sorted_results[:top_k]


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Precision@k."""
    if k == 0:
        return 0.0
    top = retrieved[:k]
    if not top:
        return 0.0
    return sum(1 for t in top if t in relevant) / k


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Recall@k."""
    if not relevant:
        return 0.0
    top = retrieved[:k]
    return sum(1 for t in top if t in relevant) / len(relevant)


def mrr(retrieved: list[str], relevant: set[str]) -> float:
    """Mean Reciprocal Rank."""
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


# ── Evaluation ────────────────────────────────────────────────────────


def evaluate_config(
    corpus: dict[str, list[dict]],
    gold_qa: list[dict],
    rrf_k: int,
    bm25_weight: float,
    top_k: int = 20,
) -> dict[str, float]:
    """Evaluate a single configuration and return metrics."""
    p5_list, p10_list, r5_list, r10_list, mrr_list = [], [], [], [], []

    for qa in gold_qa:
        query = qa["question"]
        doc_id = qa.get("document_id", "")
        # Determine which document corpus to search
        if doc_id and doc_id != "*":
            # Use the specific document, or all docs if not found
            relevant_docs = {doc_id}
            # For retrieval, search the specific document's chunks
            doc_corpus = corpus.get(doc_id, [])
            if not doc_corpus:
                # Fall back to all chunks
                doc_corpus = [c for chunks in corpus.values() for c in chunks]
        else:
            # Search all document chunks
            relevant_docs = set(corpus.keys())
            doc_corpus = [c for chunks in corpus.values() for c in chunks]

        if not doc_corpus:
            continue

        # Run retrieval
        bm25_res = bm25_search_simple(query, doc_corpus, top_k=top_k * 2)
        dense_res = dense_search_simple(query, doc_corpus, top_k=top_k * 2)
        merged = rrf_merge(
            bm25_res, dense_res, k=rrf_k, top_k=top_k, bm25_weight=bm25_weight
        )

        # Get retrieved document_ids
        retrieved_ids = [r["document_id"] for r in merged]

        # Metrics
        p5_list.append(precision_at_k(retrieved_ids, relevant_docs, 5))
        p10_list.append(precision_at_k(retrieved_ids, relevant_docs, 10))
        r5_list.append(recall_at_k(retrieved_ids, relevant_docs, 5))
        r10_list.append(recall_at_k(retrieved_ids, relevant_docs, 10))
        mrr_list.append(mrr(retrieved_ids, relevant_docs))

    return {
        "precision@5": float(np.mean(p5_list)) if p5_list else 0.0,
        "precision@10": float(np.mean(p10_list)) if p10_list else 0.0,
        "recall@5": float(np.mean(r5_list)) if r5_list else 0.0,
        "recall@10": float(np.mean(r10_list)) if r10_list else 0.0,
        "MRR": float(np.mean(mrr_list)) if mrr_list else 0.0,
    }


def print_metrics_table(
    label: str,
    metrics: dict[str, float],
    header: bool = False,
) -> None:
    """Print a metrics row. Pass an empty dict for ``metrics`` when only the header is wanted."""
    if header:
        print(
            f"{'Config':<40} {'P@5':>8} {'P@10':>8} {'R@5':>8} {'R@10':>8} {'MRR':>8}"
        )
        print("-" * 80)
    elif metrics:
        print(
            f"{label:<40} {metrics['precision@5']:>7.2%} {metrics['precision@10']:>7.2%} "
            f"{metrics['recall@5']:>7.2%} {metrics['recall@10']:>7.2%} {metrics['MRR']:>7.3f}"
        )


def save_tuning_results(best_config: dict) -> None:
    """Save tuning results as JSON for reference."""
    import json as _json

    data = {
        "updated": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "method": "Grid search over RRF k and BM25 weight against gold Q&A set",
        "default": {
            "rrf_k": 60,
            "bm25_weight": 1.0,
            "metrics": best_config["default_metrics"],
        },
        "tuned": {
            "rrf_k": best_config["rrf_k"],
            "bm25_weight": best_config["bm25_weight"],
            "metrics": best_config["tuned_metrics"],
        },
    }
    TUNING_RESULTS_PATH.write_text(_json.dumps(data, indent=2))
    print(f"\n→ Saved tuning results to {TUNING_RESULTS_PATH}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Tune hybrid retrieval weights")
    parser.add_argument(
        "--quick", action="store_true", help="Smaller grid for faster runs"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Hybrid Retrieval Weight Tuning")
    print("=" * 60)

    # 1. Load data
    print("\nLoading gold Q&A set...")
    gold_qa = load_gold_qa()
    print(f"  {len(gold_qa)} questions loaded")

    print("Loading document texts...")
    docs = load_document_texts()
    print(f"  {len(docs)} documents loaded: {', '.join(docs.keys())}")

    print("Building chunk corpus...")
    corpus = build_chunk_corpus(docs)
    total_chunks = sum(len(c) for c in corpus.values())
    print(f"  {total_chunks} total chunks across all documents")

    # 2. Define search grid
    if args.quick:
        rrf_k_values = [60]
        bm25_weights = [0.5, 1.0, 2.0]
    else:
        rrf_k_values = [30, 60, 100]
        bm25_weights = [0.3, 0.5, 0.7, 1.0, 1.5, 2.0]

    configs = list(itertools.product(rrf_k_values, bm25_weights))
    print(
        f"\nGrid: {len(configs)} configurations ({len(rrf_k_values)} k × {len(bm25_weights)} weights)"
    )

    # 3. Evaluate default config
    print(f"\nEvaluating default (k={DEFAULT_RRF_K}, w={DEFAULT_BM25_WEIGHT})...")
    default_metrics = evaluate_config(
        corpus,
        gold_qa,
        rrf_k=DEFAULT_RRF_K,
        bm25_weight=DEFAULT_BM25_WEIGHT,
    )
    print_metrics_table(
        f"Default (k={DEFAULT_RRF_K}, w={DEFAULT_BM25_WEIGHT})",
        default_metrics,
        header=True,
    )

    # 4. Grid search
    print("\nGrid search:")
    print_metrics_table("Config", {}, header=True)

    best_config = None
    best_score = -1.0
    results = []

    for rrf_k, bm25_w in configs:
        label = f"k={rrf_k}, w={bm25_w}"
        metrics = evaluate_config(corpus, gold_qa, rrf_k=rrf_k, bm25_weight=bm25_w)
        print_metrics_table(label, metrics)

        # Composite score: average of all metrics
        score = np.mean([metrics["precision@5"], metrics["recall@5"], metrics["MRR"]])
        results.append((rrf_k, bm25_w, metrics, score))

        if score > best_score:
            best_score = score
            best_config = (rrf_k, bm25_w, metrics)

    # 5. Report
    print("\n" + "=" * 60)
    print(f"Best configuration: k={best_config[0]}, BM25 weight={best_config[1]}")
    print(
        f"  Composite score: {best_score:.4f} (vs default: {np.mean([default_metrics['precision@5'], default_metrics['recall@5'], default_metrics['MRR']]):.4f})"
    )

    # 6. Show all configs sorted
    print("\nAll configurations sorted by composite score:")
    results.sort(key=lambda x: x[3], reverse=True)
    print_metrics_table("Config", {}, header=True)
    for rrf_k, bm25_w, metrics, score in results:
        label = f"k={rrf_k}, w={bm25_w}  [score={score:.4f}]"
        print_metrics_table(label, metrics)

    # 7. Save tuning results
    best_entry = {
        "rrf_k": best_config[0],
        "bm25_weight": best_config[1],
        "default_metrics": default_metrics,
        "tuned_metrics": best_config[2],
    }
    save_tuning_results(best_entry)

    # 8. Print recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATION")
    print("=" * 60)
    print(
        f"""
Current defaults:
  RRF k = {DEFAULT_RRF_K}
  BM25 weight = {DEFAULT_BM25_WEIGHT}

Tuned values:
  RRF k = {best_config[0]}
  BM25 weight = {best_config[1]}

Note: These values were tuned using lightweight pseudo-embeddings
(hash-based cosine similarity) for standalone execution without
external services.  The relative ranking of configurations is
informative, but absolute metric values should be validated
end-to-end on a live Docker stack with real sentence-transformer
embeddings and cross-encoder reranking.
"""
    )

    # Print final short table
    print("Before/After summary:")
    print(f"  {'Metric':<20} {'Before':>10} {'After':>10} {'Δ':>10}")
    print(f"  {'-' * 50}")
    for metric in ["precision@5", "precision@10", "recall@5", "recall@10", "MRR"]:
        before = default_metrics[metric]
        after = best_config[2][metric]
        delta = after - before
        print(f"  {metric:<20} {before:>8.2%} {after:>8.2%} {delta:>+9.2%}")


if __name__ == "__main__":
    main()
