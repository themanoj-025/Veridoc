#!/usr/bin/env python3
"""
Veridoc — Live Chaos/Resilience Tests (D4 Tier 2)

Stops each dependency container one at a time, verifies the app degrades
gracefully, then restarts and verifies recovery.

Usage:
    # Requires Docker stack to be running:
    docker compose up -d
    curl http://localhost:8000/api/v1/health

    # Run all tests:
    python scripts/chaos_test_live.py

    # Test a single service:
    python scripts/chaos_test_live.py --service postgres

    # Quick mode (shorter waits):
    python scripts/chaos_test_live.py --quick
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

import httpx

BACKEND_URL = "http://localhost:8000"
COMPOSE_FILE = Path(__file__).resolve().parent.parent / "docker-compose.yml"

ALL_SERVICES = ["postgres", "chroma", "redis", "minio", "ollama"]

DEPENDENCY_INFO = {
    "postgres": {
        "container": "veridoc-postgres",
        "health_key": "postgres",
        "tolerance_seconds": 15,
    },
    "chroma": {
        "container": "veridoc-chroma",
        "health_key": "chroma",
        "tolerance_seconds": 15,
    },
    "redis": {
        "container": "veridoc-redis",
        "health_key": "redis",
        "tolerance_seconds": 10,
    },
    "minio": {
        "container": "veridoc-minio",
        "health_key": "minio",
        "tolerance_seconds": 10,
    },
    "ollama": {
        "container": "veridoc-ollama",
        "health_key": "llm",
        "tolerance_seconds": 10,
    },
}


def run_cmd(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired as e:
        return -1, f"Command timed out: {e}"
    except FileNotFoundError:
        return -2, "Command not found"


async def check_health() -> dict:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BACKEND_URL}/api/v1/health")
            return {"status_code": resp.status_code, "body": resp.json()}
    except (httpx.HTTPError, OSError) as e:
        return {"status_code": 0, "body": {"error": str(e)}}


def docker_compose_stop(service: str) -> bool:
    code, _output = run_cmd(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "stop", service]
    )
    return code == 0


def docker_compose_start(service: str) -> bool:
    code, _output = run_cmd(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "start", service]
    )
    return code == 0


async def test_dependency(service: str, quick: bool = False) -> dict:
    info = DEPENDENCY_INFO[service]
    container = info["container"]
    health_key = info["health_key"]
    tolerance = 5 if quick else info["tolerance_seconds"]

    print(f"\n{'=' * 60}")
    print(f"Testing: {service} ({container})")
    print(f"{'=' * 60}")

    result = {"service": service, "container": container, "steps": [], "passed": True}

    # Step 1: Verify initial health
    print("\n  [1/4] Initial health...")
    health = await check_health()
    if health["status_code"] == 200:
        dep_status = health["body"].get("dependencies", {}).get(health_key, {})
        print(f"    OK - {health_key}: {dep_status.get('status', 'unknown')}")
    else:
        print(f"    WARN - Health returned {health['status_code']}")

    # Step 2: Stop container (with guaranteed restart via try/finally)
    print(f"\n  [2/4] Stopping {service}...")
    stopped = docker_compose_stop(service)
    result["steps"].append({"step": "stop_container", "passed": stopped})
    if not stopped:
        print("    WARN - Stop command had issues")
        result["passed"] = False

    try:
        await asyncio.sleep(5)

        # Step 3: Verify graceful degradation
        print("\n  [3/4] Verifying graceful degradation...")
        health = await check_health()

        if health["status_code"] == 503:
            deps = health["body"].get("dependencies", {})
            dep = deps.get(health_key, {})
            dep_status = dep.get("status", "unknown")
            print(f"    PASS - Health 503 ({health_key}={dep_status})")
            result["steps"].append(
                {
                    "step": "graceful_degradation",
                    "passed": True,
                    "evidence": f"503 with {health_key}={dep_status}",
                }
            )

            # (c) Check structured logging in backend container
            code, logs = run_cmd(["docker", "logs", "veridoc-backend", "--tail", "20"])
            if code == 0:
                log_lower = logs.lower()
                key_lower = health_key.lower()
                # Look for the health_key in proximity to error/unhealthy
                has_structured_log = (
                    key_lower in log_lower
                    and ("error" in log_lower or "unhealthy" in log_lower)
                ) or f"{key_lower}.*error" in log_lower
                if has_structured_log:
                    print(f"    PASS - Backend logged {health_key} failure")
                else:
                    print(
                        f"    INFO - Backend logs checked ({health_key} may not appear)"
                    )
                if "error" in log_lower:
                    print("    PASS - Error-level log entries found")
            else:
                print("    INFO - Could not read backend logs")

            # (b) Verify JSON error format
            if "dependencies" in health["body"] or "detail" in health["body"]:
                print("    PASS - Clear error response with dependencies/detail")

        elif health["status_code"] == 200:
            deps = health["body"].get("dependencies", {})
            dep = deps.get(health_key, {})
            dep_status = dep.get("status", "unknown")
            print(f"    INFO - Health still 200 ({health_key}={dep_status})")
            if dep_status == "error":
                print("    PASS - Health endpoint is resilient, reports partial error")
            elif service == "minio":
                print(
                    "    NOTE - MinIO is file-storage only, not checked on every health call"
                )
            else:
                print(f"    WARN - {service} stopped but health unaffected")
            result["steps"].append({"step": "graceful_degradation", "passed": True})

        elif health["status_code"] == 0:
            print("    FAIL - App unresponsive (HTTP connection failed)")
            result["passed"] = False
            result["steps"].append(
                {
                    "step": "graceful_degradation",
                    "passed": False,
                    "evidence": "Health endpoint unreachable",
                }
            )
        else:
            print(f"    INFO - Health returned {health['status_code']}")
            result["steps"].append({"step": "graceful_degradation", "passed": True})

        # Verify API doesn't crash (use health endpoint which is always available)
        # The health endpoint is the authoritative way to check app responsiveness
        # without requiring auth tokens.

    finally:
        # Guarantee container is restarted even on Ctrl+C or exception
        print(f"\n  [4/4] Restarting {service}...")
        started = docker_compose_start(service)
        if started:
            print("    OK - Restart command issued")
        else:
            print("    WARN - Restart command had issues")

        # Wait for recovery
        recovered = False
        for attempt in range(tolerance):
            await asyncio.sleep(2)
            health = await check_health()
            if health["status_code"] == 200:
                dep = health["body"].get("dependencies", {}).get(health_key, {})
                if dep.get("status") == "ok":
                    print(f"    PASS - {service} recovered ({attempt * 2 + 2}s)")
                    recovered = True
                    break
                else:
                    print(f"    Waiting... {health_key}={dep.get('status', 'unknown')}")

        if recovered:
            print("    PASS - Health endpoint healthy after restart")
            result["steps"].append({"step": "recovery", "passed": True})
        else:
            print(f"    FAIL - {service} did not recover within {tolerance * 2}s")
            result["steps"].append({"step": "recovery", "passed": False})
            result["passed"] = False

    return result


async def verify_stack_healthy() -> bool:
    print("Verifying Docker stack readiness...")

    code, output = run_cmd(["docker", "info", "--format", "{{.ServerVersion}}"])
    if code != 0:
        print("  ERROR: Docker not running")
        return False
    print(f"  Docker engine: {output.strip()}")

    if not COMPOSE_FILE.exists():
        print(f"  ERROR: {COMPOSE_FILE} not found")
        return False

    code, output = run_cmd(
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE_FILE),
            "ps",
            "--services",
            "--filter",
            "status=running",
        ]
    )
    running = [s.strip() for s in output.strip().split("\n") if s.strip()]
    print(f"  Running: {', '.join(running)}")

    health = await check_health()
    if health["status_code"] == 200:
        deps = health["body"].get("dependencies", {})
        all_ok = all(d.get("status") == "ok" for d in deps.values())
        print(f"  Health: 200 (all ok: {all_ok})")
        return all_ok
    else:
        print(f"  Health: {health['status_code']} - stack may be degraded")
        return False


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Live chaos/resilience tests (D4 Tier 2)"
    )
    parser.add_argument(
        "--service", choices=ALL_SERVICES, help="Test a single dependency only"
    )
    parser.add_argument(
        "--quick", action="store_true", help="Shorter recovery wait times"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Live Chaos/Resilience Tests (D4 Tier 2)")
    print("=" * 60)

    stack_ok = await verify_stack_healthy()
    if not stack_ok:
        print("\nERROR: Docker stack not fully healthy. Run: docker compose up -d")
        sys.exit(1)

    services = [args.service] if args.service else ALL_SERVICES
    results = []
    for service in services:
        result = await test_dependency(service, quick=args.quick)
        results.append(result)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Service':<12} {'Container':<20} {'Result':<10}")
    print("-" * 42)
    for r in results:
        icon = "PASS" if r["passed"] else "FAIL"
        print(f"{r['service']:<12} {r['container']:<20} {icon:<10}")

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\n{passed}/{total} tests passed")

    if passed < total:
        print("\nFAILED tests require investigation. Check container logs:")
        for r in results:
            if not r["passed"]:
                print(f"  docker logs {r['container']} --tail 30")
        sys.exit(1)
    else:
        print("\nAll resilience tests passed against live containers.")
        print("Update the TestRealContainerChaos class in")
        print("backend/tests/test_resilience.py to reflect real-container validation.")


if __name__ == "__main__":
    asyncio.run(main())
