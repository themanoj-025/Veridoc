# Veridoc — Next Steps

> Items deferred from the autonomous build that require human action, a Docker-equipped machine, cloud accounts, or are optional enhancements.

---

## 🔴 TIER 2 — Requires Docker Stack Running

These steps need `docker compose up -d` with the full Veridoc stack (Postgres, Chroma, Redis, Ollama, MinIO) running locally. Run them in order.

### 1. Execute the Evaluation Harness (real numbers)

```bash
# Prerequisites: Docker Desktop running, Veridoc stack up
docker compose up -d
# Wait for all services to become healthy (~30s)
curl http://localhost:8000/api/v1/health

# Run the full head-to-head comparison (23 questions, ~5 min)
python scripts/run_eval.py --compare

# View results
cat docs/evaluation-report.md
```

This replaces the current standalone pipeline estimates with real precision@k, recall@k, MRR, faithfulness, latency, and token cost numbers from the live Ollama model.

### 2. Execute Red-Team Tests Against Live Ollama

```bash
# With the stack running, run prompt-injection defense validation
# (These verify the LLM model actually respects the instruction boundaries)
docker compose up -d

# Run the red-team evaluation
python -c "
import json, asyncio
from pathlib import Path
from app.services.llm_provider import get_llm
from app.core.di import set_di_container, DIContainer

async def test_injections():
    tests = json.loads(Path('eval/red_team/prompt_injection.json').read_text())
    container = DIContainer()
    set_di_container(container)
    llm = get_llm()
    
    for t in tests:
        print(f\"Testing: {t['name']}\")
        resp = await llm.chat(system_prompt=t['context'], history=[], message=t['prompt'])
        passed = t['expected_fail_keyword'] not in resp.lower()
        print(f\"  Result: {'PASS' if passed else 'FAIL'}\")
        print(f\"  Output: {resp[:200]}\")

asyncio.run(test_injections())
"
```

### 3. Run the Load Test

```bash
# With the stack running, at 1/5/10/25 concurrent users
pip install locust
python scripts/run_load_test.py

# View the report
cat docs/load-test-report.md
```

---

## 🔴 TIER 3 — Requires Human Action (Cloud Accounts / Screen Recording)

### 4. Deploy a Live Demo

See the complete deployment runbook at [`docs/deployment-runbook.md`](docs/deployment-runbook.md). Three options:

| Option | Platform | Time | Cost |
|--------|----------|------|------|
| **A** (recommended) | Render | 30 min | $0/mo (free tier, cold-start ~30s) |
| **B** | Fly.io | 30 min | $0/mo (limited always-on hours) |
| **C** | Vercel + Railway | 45 min | $0/mo (if within free credits) |

Steps summary:
1. Push the repo to GitHub
2. Pick a platform from the runbook
3. Set production secrets from `.env.production.example`
4. Verify with `curl <url>/api/v1/health`
5. Add the live URL to `README.md`

### 5. Record Demo Walkthrough

A ready-to-use 90-second script is at [`docs/demo-script.md`](docs/demo-script.md).

Steps:
1. Start the local stack or use the live URL
2. Open screen recording tool (OBS, Loom, QuickTime)
3. Follow the timed script: landing → register → upload → ask → click citation → ask unanswerable → wrap up
4. Save as `veridoc-demo.mp4`
5. Replace the `[Demo]` link in `README.md` with the video file or embed URL

---

## 🟡 Optional Enhancements

### 6. Claude/GPT API Integration

Set environment variables to switch from local Ollama:
```bash
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=claude
```
Or:
```bash
OPENAI_API_KEY=sk-...
LLM_PROVIDER=openai
```

### 7. SSO / SAML

Implement SAML-based SSO for enterprise customers. Use `python3-saml` library.

### 8. Multi-tenant Orgs + RBAC

Add organization table, role-based access control (admin, editor, viewer).

### 9. Audit Log

Enable comprehensive audit logging for compliance (HIPAA, SOC2).

### 10. On-Prem / Private Cloud Guide

Provide Helm chart for Kubernetes deployment and air-gapped installation.

### 11. GitHub Dependabot

Enable Dependabot in `.github/dependabot.yml`:
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
```

---

## ✅ How to use this file
1. Complete Tier 2 items first (requires Docker Desktop running locally)
2. Complete Tier 3 items next (requires cloud accounts + screen recording)
3. Optional enhancements are nice-to-haves for portfolio polish
4. Remove each item from this file as you complete it
5. Update documentation with real numbers where applicable
