#!/usr/bin/env python3
"""
Promote reviewed thumbs-down feedback entries into the gold Q&A set.

This script:
1. Reads ``eval/continuous_feedback.json`` (the queue of thumbs-down responses)
2. Shows each entry with its question, answer, and faithfulness score
3. Lets the reviewer accept/reject/skip each entry
4. Appends accepted entries to ``eval/gold_qa.json``
5. Removes reviewed entries from the queue

Usage:
    python scripts/promote_feedback.py

To auto-promote all entries with faithfulness_score >= 0.8 without interactive review:
    python scripts/promote_feedback.py --auto

To see the current queue size without processing:
    python scripts/promote_feedback.py --status
"""

import argparse
import json
from datetime import datetime
from pathlib import Path


def get_eval_dir() -> Path:
    """Get the eval directory (project root / eval)."""
    # Assume this script is in scripts/
    return Path(__file__).resolve().parent.parent / "eval"


def load_json(path: Path) -> list[dict]:
    """Load a JSON file, returning an empty list if it doesn't exist or is invalid."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_json(path: Path, data: list[dict]) -> None:
    """Save data to a JSON file."""
    path.write_text(json.dumps(data, indent=2, default=str))


def status() -> None:
    """Print the current queue size without processing."""
    eval_dir = get_eval_dir()
    queue = load_json(eval_dir / "continuous_feedback.json")
    gold = load_json(eval_dir / "gold_qa.json")

    print(f"Feedback queue:      {len(queue)} entries")
    print(f"Gold Q&A set:        {len(gold)} entries")

    if queue:
        down_count = sum(1 for e in queue if e.get("feedback") == "down")
        print(f"  Thumbs-down:       {down_count}")
        print(
            f"  Avg faithfulness:  {sum(e.get('faithfulness_score', 0) or 0 for e in queue) / len(queue):.2f}"
        )


def auto_promote(threshold: float = 0.8) -> int:
    """Auto-promote all entries with faithfulness_score >= threshold."""
    eval_dir = get_eval_dir()
    queue = load_json(eval_dir / "continuous_feedback.json")
    gold = load_json(eval_dir / "gold_qa.json")

    promoted = 0
    remaining = []

    for entry in queue:
        score = entry.get("faithfulness_score", 0)
        if score is not None and score >= threshold:
            gold_entry = {
                "question": entry.get("question", ""),
                "answer": entry.get("answer", ""),
                "source": "continuous_feedback",
                "added_at": datetime.utcnow().isoformat(),
                "faithfulness_score": score,
                "unanswerable": False,
            }
            gold.append(gold_entry)
            promoted += 1
        else:
            remaining.append(entry)

    save_json(eval_dir / "gold_qa.json", gold)
    save_json(eval_dir / "continuous_feedback.json", remaining)

    print(f"Auto-promoted {promoted} entries (threshold >= {threshold})")
    print(f"Remaining in queue: {len(remaining)}")
    print(f"Gold set now: {len(gold)} entries")
    return promoted


def interactive_promote() -> int:
    """Interactively review and promote feedback entries."""
    eval_dir = get_eval_dir()
    queue = load_json(eval_dir / "continuous_feedback.json")
    gold = load_json(eval_dir / "gold_qa.json")

    if not queue:
        print("No entries in the feedback queue.")
        return 0

    promoted = 0
    remaining = []

    print(f"\n{'=' * 60}")
    print(f"Reviewing {len(queue)} feedback entries")
    print(f"{'=' * 60}\n")

    for i, entry in enumerate(queue):
        print(f"\n--- Entry {i + 1}/{len(queue)} ---")
        print(f"Question:    {entry.get('question', '?')[:200]}")
        print(f"Answer:      {entry.get('answer', '?')[:300]}")
        print(f"Faithfulness: {entry.get('faithfulness_score', 'N/A')}")
        print(f"Feedback:    {entry.get('feedback', '?')}")

        while True:
            action = input("\n[A]ccept [R]eject [S]kip [Q]uit: ").strip().lower()
            if action in ("a", "accept"):
                gold_entry = {
                    "question": entry.get("question", ""),
                    "answer": entry.get("answer", ""),
                    "source": "continuous_feedback",
                    "added_at": datetime.utcnow().isoformat(),
                    "faithfulness_score": entry.get("faithfulness_score"),
                    "unanswerable": False,
                }
                gold.append(gold_entry)
                promoted += 1
                print("  ✓ Promoted to gold set")
                break
            elif action in ("r", "reject"):
                print("  ✗ Rejected")
                break
            elif action in ("s", "skip"):
                remaining.append(entry)
                print("  → Skipped (kept in queue)")
                break
            elif action in ("q", "quit"):
                remaining.extend(queue[i:])
                save_json(eval_dir / "gold_qa.json", gold)
                save_json(eval_dir / "continuous_feedback.json", remaining)
                print(f"\nSaved. Promoted: {promoted}, Remaining: {len(remaining)}")
                return promoted
            else:
                print("  Please enter A, R, S, or Q")

    # Save results
    save_json(eval_dir / "gold_qa.json", gold)
    save_json(eval_dir / "continuous_feedback.json", remaining)

    print(f"\n{'=' * 60}")
    print(f"Promoted: {promoted}")
    print(f"Remaining in queue: {len(remaining)}")
    print(f"Gold set now: {len(gold)} entries")
    print(f"{'=' * 60}")
    return promoted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Promote feedback entries into the gold Q&A set."
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-promote all entries with faithfulness_score >= 0.8",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="Faithfulness threshold for auto-promotion (default: 0.8)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show queue status without processing",
    )

    args = parser.parse_args()

    if args.status:
        status()
    elif args.auto:
        auto_promote(threshold=args.threshold)
    else:
        interactive_promote()


if __name__ == "__main__":
    main()
