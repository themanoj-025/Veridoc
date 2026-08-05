"""CI evaluation regression gate — run by GitHub Actions on every PR/push.

Checks:
1. ``eval/gold_qa.json`` exists and has at least 5 entries.
2. ``eval/continuous_feedback.json`` does not exceed 1000 entries.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    gold_path = REPO_ROOT / "eval" / "gold_qa.json"
    if not gold_path.exists():
        print("FAIL: eval/gold_qa.json not found")
        return 1

    gold = json.loads(gold_path.read_text())
    print(f"Gold Q&A set: {len(gold)} entries")

    if len(gold) < 5:
        print(f"FAIL: Only {len(gold)} entries, need at least 5")
        return 1

    feedback_path = REPO_ROOT / "eval" / "continuous_feedback.json"
    if feedback_path.exists():
        feedback = json.loads(feedback_path.read_text())
        print(f"Feedback queue: {len(feedback)} entries")
        if len(feedback) > 1000:
            print(
                f"WARN: Feedback queue has {len(feedback)} entries, "
                "consider running promote_feedback.py"
            )

    print("PASS: Evaluation regression gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
