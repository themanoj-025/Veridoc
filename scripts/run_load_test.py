#!/usr/bin/env python3
"""
Veridoc — Locust Load Test Runner

Orchestrates headless Locust runs at increasing concurrency levels
(1, 5, 10, 25 users) against the local Veridoc stack, collects
p50/p95 latency and error-rate results, and writes a summary report.

Usage::

    # Prerequisites: the full Veridoc stack must be running
    docker compose up -d
    python scripts/run_load_test.py

    # Optionally specify a different host and concurrency levels:
    python scripts/run_load_test.py \\
        --host http://localhost:8000 \\
        --concurrency 1 5 10 25 \\
        --run-time 30s

Requires: locust >= 2.30, installed in the current Python environment.
Requires: Veridoc API stack running at HOST.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from pathlib import Path


# ══════════════════════════════════════════════════════════════════
# Pre-flight check
# ══════════════════════════════════════════════════════════════════


def _check_api(host: str) -> bool:
    """Quickly verify the API is reachable before spending time on load tests."""
    import urllib.request
    import urllib.error

    url = f"{host.rstrip('/')}/api/v1/health"
    try:
        resp = urllib.request.urlopen(url, timeout=5)
        return resp.status == 200
    except (urllib.error.URLError, OSError, Exception):
        return False


# ══════════════════════════════════════════════════════════════════
# Locust runner
# ══════════════════════════════════════════════════════════════════


def run_locust(
    host: str,
    users: int,
    spawn_rate: int,
    run_time: str,
    csv_prefix: Path,
) -> dict:
    """Run Locust in headless mode and return parsed stats.

    Returns a dict with keys: ``users``, ``rps``, ``p50_ms``, ``p95_ms``,
    ``avg_ms``, ``fail_percent``, ``total_requests``.
    """
    csv_prefix.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        str(Path(__file__).resolve().parent / "locustfile.py"),
        "--headless",
        "--users",
        str(users),
        "--spawn-rate",
        str(spawn_rate),
        "--run-time",
        run_time,
        "--host",
        host,
        "--csv",
        str(csv_prefix),
        "--only-summary",
        "--stop-timeout",
        "5",
    ]

    print(f"\n{'=' * 60}")
    print(f"  Load test: {users} concurrent users")
    print(f"  Spawn rate: {spawn_rate}/s,  Run time: {run_time}")
    print(f"{'=' * 60}")

    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    elapsed = time.time() - start

    # ── Parse the CSV stats file (most reliable) ────────────────
    stats: dict = {
        "users": users,
        "rps": 0.0,
        "p50_ms": 0.0,
        "p95_ms": 0.0,
        "avg_ms": 0.0,
        "fail_percent": 0.0,
        "total_requests": 0,
        "elapsed_s": round(elapsed, 1),
    }

    stats_path = csv_prefix.with_suffix("_stats.csv")
    if stats_path.exists():
        try:
            with stats_path.open(newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("Name", "") == "Aggregated":
                        stats["rps"] = float(row.get("Requests/s", 0))
                        stats["fail_percent"] = float(row.get("Failure Percentage", 0))
                        stats["total_requests"] = int(row.get("Request Count", 0))
                        stats["avg_ms"] = float(
                            row.get("Average Response Time (ms)", 0)
                        )
                        stats["p50_ms"] = float(row.get("50% (ms)", 0))
                        stats["p95_ms"] = float(row.get("95% (ms)", 0))
            print(f"  Parsed stats from CSV: {stats_path.name}")
        except (ValueError, KeyError, OSError) as e:
            print(f"  Warning: Could not parse CSV ({e}), falling back to stdout")

    # ── Fallback: parse stdout summary line ─────────────────────
    if stats["total_requests"] == 0 and result.stdout:
        for line in result.stdout.splitlines():
            if "Aggregated" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    val = part.rstrip("ms,")
                    try:
                        float(val)
                    except ValueError:
                        continue
                    if stats["p50_ms"] == 0:
                        stats["p50_ms"] = float(val)
                        if i + 1 < len(parts):
                            nxt = parts[i + 1].rstrip("ms,")
                            try:
                                stats["p95_ms"] = float(nxt)
                            except ValueError:
                                pass

    print(f"\n  Results for {users} users ({elapsed:.1f}s):")
    print(f"    Total requests: {stats['total_requests']}")
    print(f"    RPS:           {stats['rps']:.1f}")
    print(f"    Avg latency:   {stats['avg_ms']:.0f} ms")
    print(f"    P50 latency:   {stats['p50_ms']:.0f} ms")
    print(f"    P95 latency:   {stats['p95_ms']:.0f} ms")
    print(f"    Error rate:    {stats['fail_percent']:.1f}%")

    if result.returncode != 0 and result.stderr:
        if "ConnectionError" not in result.stderr:
            sys.stderr.write(f"  Stderr: {result.stderr[:300]}\n")

    return stats


# ══════════════════════════════════════════════════════════════════
# Report
# ══════════════════════════════════════════════════════════════════


def write_report(results: list[dict], host: str, run_time: str):
    """Write a load test summary report to ``docs/load-test-report.md``."""
    now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    docs_dir = Path(__file__).resolve().parent.parent / "docs"

    lines = [
        "# Veridoc — Load Test Report",
        "",
        f"*Generated: {now}*",
        f"*Target: {host}*",
        f"*Run time per scenario: {run_time}*",
        "",
        "## Results Summary",
        "",
        "| Users | Requests | RPS | Avg (ms) | P50 (ms) | P95 (ms) | Error % |",
        "|-------|----------|-----|----------|----------|----------|---------|",
    ]

    for r in results:
        lines.append(
            f"| {r['users']} | {r['total_requests']} | "
            f"{r['rps']:.1f} | {r['avg_ms']:.0f} | {r['p50_ms']:.0f} | "
            f"{r['p95_ms']:.0f} | {r['fail_percent']:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Observations",
            "",
            "*This section should be filled in after reviewing the actual results.*",
            "",
            "### Bottleneck Analysis",
            "",
            "1. **At 1 user**: Baseline latency for unauthenticated endpoints.",
            "2. **At 5 users**: First sign of auth bottleneck (JWT signing + DB session overhead).",
            "3. **At 10 users**: Postgres connection pool contention may appear.",
            "4. **At 25 users**: ChromaDB query latency becomes significant.",
            "",
            "### Recommendations",
            "",
            "1. Increase Postgres pool size in `database.py` for higher concurrency.",
            "2. Add Redis-backed session caching for JWT validation.",
            "3. Consider read replicas for document listing queries.",
            "4. Add CDN caching for health endpoint (extreme load only).",
            "",
            "## Reproduction",
            "",
            "```bash",
            "docker compose up -d",
            "pip install locust",
            f"python scripts/run_load_test.py --host {host} --run-time {run_time}",
            "```",
            "",
            "*Veridoc load test report. Results reflect the local Docker Compose stack.*",
        ]
    )

    report_path = docs_dir / "load-test-report.md"
    report_path.write_text("\n".join(lines) + "\n")
    print(f"\n[OK] Load test report: {report_path}")


# ══════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="Run Veridoc load tests at multiple concurrency levels"
    )
    parser.add_argument(
        "--host",
        default="http://localhost:8000",
        help="Base URL of the Veridoc API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--concurrency",
        nargs="+",
        type=int,
        default=[1, 5, 10, 25],
        help="Concurrency levels to test (default: 1 5 10 25)",
    )
    parser.add_argument(
        "--run-time",
        default="45s",
        help="Duration per test scenario (default: 45s)",
    )
    parser.add_argument(
        "--spawn-rate",
        type=int,
        default=2,
        help="Users spawned per second (default: 2)",
    )
    parser.add_argument(
        "--csv-dir",
        default="loadtest_results",
        help="Directory for CSV output (default: loadtest_results)",
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="Skip the pre-flight API health check",
    )
    args = parser.parse_args()

    # ── Pre-flight check ────────────────────────────────────────
    if not args.skip_check:
        print("Checking API availability...", end=" ", flush=True)
        if not _check_api(args.host):
            print("UNREACHABLE")
            print(f"  Could not reach {args.host}/api/v1/health")
            print("  Start the Veridoc stack:  docker compose up -d")
            print("  Or use --skip-check to run anyway.")
            sys.exit(1)
        print("OK")

    csv_dir = Path(args.csv_dir)
    results: list[dict] = []

    print("Veridoc Load Test Runner")
    print(f"  Host:      {args.host}")
    print(f"  Users:     {args.concurrency}")
    print(f"  Run time:  {args.run_time}")
    print(f"  CSV dir:   {csv_dir}")

    for users in args.concurrency:
        csv_prefix = csv_dir / f"loadtest_{users}u"
        stats = run_locust(
            host=args.host,
            users=users,
            spawn_rate=min(args.spawn_rate, users),
            run_time=args.run_time,
            csv_prefix=csv_prefix,
        )
        results.append(stats)

    write_report(results, args.host, args.run_time)

    print(f"\n{'=' * 60}")
    print("  Load test complete!")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
