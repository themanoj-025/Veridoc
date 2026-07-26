#!/usr/bin/env python3
"""
Download SQuAD 2.0 dev split for additional standardized benchmarking.

Usage: python scripts/download_squad.py
"""

import json
from pathlib import Path
import httpx

EVAL_DIR = Path(__file__).resolve().parent.parent / "eval"
EVAL_DIR.mkdir(parents=True, exist_ok=True)

SQUAD_URL = "https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json"
SQUAD_PATH = EVAL_DIR / "squad_dev_v2.0.json"
METRICS_PATH = EVAL_DIR / "squad_metrics.json"


def download_squad():
    """Download SQuAD 2.0 dev split and compute summary metrics."""
    print(f"Downloading SQuAD 2.0 dev from {SQUAD_URL}...")

    response = httpx.get(SQUAD_URL, timeout=60, follow_redirects=True)
    response.raise_for_status()

    data = response.json()

    # Compute summary metrics
    total_questions = 0
    unanswerable_count = 0
    topics = set()

    for article in data.get("data", []):
        for paragraph in article.get("paragraphs", []):
            for qa in paragraph.get("qas", []):
                total_questions += 1
                if qa.get("is_impossible", False):
                    unanswerable_count += 1
                topics.add(article.get("title", "Unknown"))

    metrics = {
        "total_questions": total_questions,
        "answerable_questions": total_questions - unanswerable_count,
        "unanswerable_questions": unanswerable_count,
        "unique_topics": len(topics),
        "source": "SQuAD 2.0 Dev Split",
        "url": SQUAD_URL,
    }

    # Save raw data (gitignored)
    SQUAD_PATH.write_text(json.dumps(data, indent=2))

    # Save metrics only
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))

    print(f"\n  Total questions: {total_questions}")
    print(f"  Answerable: {total_questions - unanswerable_count}")
    print(f"  Unanswerable: {unanswerable_count}")
    print(f"  Unique topics: {len(topics)}")
    print(f"\nRaw data saved to: {SQUAD_PATH}")
    print(f"Metrics saved to: {METRICS_PATH}")


def main():
    print("=" * 60)
    print("Veridoc — Download SQuAD 2.0")
    print("=" * 60)
    download_squad()
    print("=" * 60)


if __name__ == "__main__":
    main()
