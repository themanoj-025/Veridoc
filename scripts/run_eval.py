#!/usr/bin/env python3
"""
Run the full evaluation harness against the gold Q&A set.

Usage: python scripts/run_eval.py
       python scripts/run_eval.py --compare  (runs naive vs hybrid comparison)
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.evaluation import (
    compute_metrics,
    resolve_document_ids,
    run_single_eval,
)

EVAL_DIR = Path(__file__).resolve().parent.parent / "eval"
GOLD_QA_PATH = EVAL_DIR / "gold_qa.json"
REPORT_PATH = EVAL_DIR / "evaluation-report.md"


def load_gold_qa() -> list[dict]:
    """Load gold Q&A pairs."""
    if not GOLD_QA_PATH.exists():
        print(f"ERROR: {GOLD_QA_PATH} not found. Run scripts/build_gold_qa.py first.")
        sys.exit(1)
    return json.loads(GOLD_QA_PATH.read_text())


async def run_evaluation(
    gold_qa: list[dict],
    use_hybrid: bool = True,
) -> tuple[list[dict], dict]:
    """Run evaluation on all gold Q&A pairs."""
    print(
        f"\nRunning evaluation with {'hybrid+rerank' if use_hybrid else 'naive dense'} retrieval..."
    )
    print(f"  Total questions: {len(gold_qa)}")
    print()

    results = []
    unanswerable_indices = set()

    for i, qa in enumerate(gold_qa):
        print(f"  [{i + 1}/{len(gold_qa)}] {qa['question'][:60]}...")

        if qa["type"] == "unanswerable":
            unanswerable_indices.add(i)

        # Determine document IDs to search — resolve gold-set slugs to real
        # DB document UUIDs (falls back to "search all" when unresolvable)
        doc_id = qa.get("document_id", "")
        document_ids = await resolve_document_ids(doc_id)

        try:
            result = await run_single_eval(
                question=qa["question"],
                gold_answer=qa["gold_answer"],
                document_ids=document_ids,
                use_hybrid=use_hybrid,
            )
            result["id"] = qa["id"]
            result["type"] = qa["type"]
            results.append(result)
        except Exception as e:
            print(f"    ERROR: {e}")
            results.append(
                {
                    "id": qa["id"],
                    "question": qa["question"],
                    "generated_answer": "",
                    "gold_answer": qa["gold_answer"],
                    "faithfulness_score": 0.0,
                    "latency_ms": 0,
                    "type": qa["type"],
                    "error": str(e),
                }
            )

    metrics = compute_metrics(results, unanswerable_indices)
    return results, metrics


def format_table_row(cells: list[str], widths: list[int]) -> str:
    """Format a markdown table row."""
    parts = []
    for cell, width in zip(cells, widths):
        parts.append(cell.ljust(width))
    return "| " + " | ".join(parts) + " |"


def write_report(
    hybrid_results: list[dict],
    hybrid_metrics: dict,
    naive_results: list[dict] | None = None,
    naive_metrics: dict | None = None,
):
    """Write evaluation report to eval/evaluation-report.md."""
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Veridoc — Evaluation Report",
        "",
        f"*Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}*",
        "",
        "## Summary",
        "",
        "This report presents evaluation results for the Veridoc RAG pipeline.",
        "",
        "### Head-to-Head: Naive Dense vs Hybrid+Re-rank",
        "",
        "| Metric | Naive Dense | Hybrid+Re-rank | Improvement |",
        "|--------|-------------|----------------|-------------|",
    ]

    if hybrid_metrics and naive_metrics:
        metrics_list = [
            (
                "Answer Accuracy",
                f"{naive_metrics.get('answer_accuracy', 0) * 100:.1f}%",
                f"{hybrid_metrics.get('answer_accuracy', 0) * 100:.1f}%",
            ),
            (
                "Refusal Accuracy",
                f"{naive_metrics.get('refusal_accuracy', 0) * 100:.1f}%",
                f"{hybrid_metrics.get('refusal_accuracy', 0) * 100:.1f}%",
            ),
            (
                "Mean Faithfulness",
                f"{naive_metrics.get('mean_faithfulness', 0) * 100:.1f}%",
                f"{hybrid_metrics.get('mean_faithfulness', 0) * 100:.1f}%",
            ),
            (
                "P50 Latency",
                f"{naive_metrics.get('p50_latency_ms', 0):.0f}ms",
                f"{hybrid_metrics.get('p50_latency_ms', 0):.0f}ms",
            ),
            (
                "P95 Latency",
                f"{naive_metrics.get('p95_latency_ms', 0):.0f}ms",
                f"{hybrid_metrics.get('p95_latency_ms', 0):.0f}ms",
            ),
        ]
        for name, naive_val, hybrid_val in metrics_list:
            improvement = ""
            if "%" in naive_val and "%" in hybrid_val:
                imp = float(hybrid_val.strip("%")) - float(naive_val.strip("%"))
                improvement = f"+{imp:.1f}%" if imp > 0 else f"{imp:.1f}%"
            elif "ms" in naive_val and "ms" in hybrid_val:
                imp = float(naive_val.strip("ms")) - float(hybrid_val.strip("ms"))
                improvement = (
                    f"-{imp:.0f}ms faster" if imp > 0 else f"+{abs(imp):.0f}ms slower"
                )
            lines.append(f"| {name} | {naive_val} | {hybrid_val} | {improvement} |")
    else:
        lines.append(
            f"| Answer Accuracy | N/A | {hybrid_metrics.get('answer_accuracy', 0) * 100:.1f}% | — |"
        )
        lines.append(
            f"| Refusal Accuracy | N/A | {hybrid_metrics.get('refusal_accuracy', 0) * 100:.1f}% | — |"
        )
        lines.append(
            f"| Mean Faithfulness | N/A | {hybrid_metrics.get('mean_faithfulness', 0) * 100:.1f}% | — |"
        )
        lines.append(
            f"| P50 Latency | N/A | {hybrid_metrics.get('p50_latency_ms', 0):.0f}ms | — |"
        )
        lines.append(
            f"| P95 Latency | N/A | {hybrid_metrics.get('p95_latency_ms', 0):.0f}ms | — |"
        )

    lines.extend(
        [
            "",
            "## Detailed Results",
            "",
            "| # | Question | Type | Faithfulness | Latency | Status |",
            "|---|----------|------|-------------|---------|--------|",
        ]
    )

    for i, r in enumerate(hybrid_results):
        q = r.get("question", "")[:50]
        t = r.get("type", "")
        f = r.get("faithfulness_score", 0)
        lat = r.get("latency_ms", 0)
        status = "✅" if f >= 0.7 else "⚠️" if f >= 0.4 else "❌"
        lines.append(
            f"| {i + 1} | {q}... | {t} | {f * 100:.0f}% | {lat:.0f}ms | {status} |"
        )

    lines.extend(
        [
            "",
            "## Faithfulness Distribution",
            "",
            f"- **Mean**: {hybrid_metrics.get('mean_faithfulness', 0) * 100:.1f}%",
            "",
            "## Latency Distribution",
            "",
            f"- **P50**: {hybrid_metrics.get('p50_latency_ms', 0):.0f}ms",
            f"- **P95**: {hybrid_metrics.get('p95_latency_ms', 0):.0f}ms",
            f"- **Mean**: {hybrid_metrics.get('mean_latency_ms', 0):.0f}ms",
            "",
            "## Test Set Composition",
            "",
            f"- Total questions: {hybrid_metrics.get('total_questions', 0)}",
            f"- Unanswerable: {sum(1 for r in hybrid_results if r.get('type') == 'unanswerable')}",
            "",
            "---",
            "",
            "*Veridoc evaluation harness report.*",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"\nReport written to: {REPORT_PATH}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run Veridoc evaluation")
    parser.add_argument(
        "--compare", action="store_true", help="Run naive vs hybrid comparison"
    )
    args = parser.parse_args()

    gold_qa = load_gold_qa()

    # Run hybrid+rerank evaluation
    print("=" * 60)
    hybrid_results, hybrid_metrics = await run_evaluation(gold_qa, use_hybrid=True)
    print("\nHybrid+Re-rank Results:")
    print(f"  Answer Accuracy: {hybrid_metrics.get('answer_accuracy', 0) * 100:.1f}%")
    print(f"  Refusal Accuracy: {hybrid_metrics.get('refusal_accuracy', 0) * 100:.1f}%")
    print(
        f"  Mean Faithfulness: {hybrid_metrics.get('mean_faithfulness', 0) * 100:.1f}%"
    )
    print(f"  P50 Latency: {hybrid_metrics.get('p50_latency_ms', 0):.0f}ms")

    naive_results = None
    naive_metrics = None

    if args.compare:
        print("\n" + "=" * 60)
        naive_results, naive_metrics = await run_evaluation(gold_qa, use_hybrid=False)
        print("\nNaive Dense Results:")
        print(
            f"  Answer Accuracy: {naive_metrics.get('answer_accuracy', 0) * 100:.1f}%"
        )
        print(
            f"  Refusal Accuracy: {naive_metrics.get('refusal_accuracy', 0) * 100:.1f}%"
        )
        print(
            f"  Mean Faithfulness: {naive_metrics.get('mean_faithfulness', 0) * 100:.1f}%"
        )
        print(f"  P50 Latency: {naive_metrics.get('p50_latency_ms', 0):.0f}ms")

    write_report(hybrid_results, hybrid_metrics, naive_results, naive_metrics)
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
