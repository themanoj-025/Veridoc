# Veridoc — Next Steps

> **Quick navigation:** [1️⃣ Start stack](#1%EF%B8%8F⃣-start-the-full-stack) · [2️⃣ Run evaluation](#2%EF%B8%8F⃣-run-the-evaluation-harness) · [3️⃣ Red-team tests](#3%EF%B8%8F⃣-run-the-red-team-tests) · [4️⃣ Load test](#4%EF%B8%8F⃣-run-the-load-test) · [5️⃣ Update docs](#5%EF%B8%8F⃣-update-docs-with-real-numbers) · [6️⃣ Deploy](#6%EF%B8%8F⃣-deploy-optional) · [7️⃣ Demo video](#7%EF%B8%8F⃣-record-demo-video-optional) · [Troubleshooting](#troubleshooting)

---

## Context: two fixes applied before the live stack will work

Before you run the commands below, be aware that **two blocking bugs** were found and fixed during the audit pass. These fixes are already in the code — you just need to rebuild the image to pick them up.

### Fix 1: Alembic hardcoded `127.0.0.1` (root cause of backend crash)

**Problem:** `backend/alembic.ini` had a hardcoded connection string:
```
sqlalchemy.url = postgresql+psycopg2://veridoc:veridoc_local_dev@127.0.0.1:5432/veridoc
```
When running inside Docker, Alembic would try to connect to `127.0.0.1` instead of the PostgreSQL service at hostname `postgres`. The backend would crash-loop with:
```
(psycopg2.OperationalError) connection to server at "127.0.0.1", port 5432 failed:
Connection refused
```

**Fix:** `backend/alembic/env.py` now overrides the hardcoded URL with Pydantic settings:
```python
config.set_main_option("sqlalchemy.url", settings.database_url_sync)
```
This means Alembic respects the `POSTGRES_HOST` environment variable — `postgres` in Docker, `localhost` locally.

**Verify fix is active:**
```bash
grep "set_main_option" backend/alembic/env.py
# Expected: config.set_main_option("sqlalchemy.url", settings.database_url_sync)
```

### Fix 2: `env_file` conflict in docker-compose.yml

**Problem:** The `env_file: .env` on `backend` and `worker` services was loading `POSTGRES_HOST=127.0.0.1` from the project `.env` file, silently overriding the `POSTGRES_HOST: postgres` in the `environment:` block.

**Fix:** Removed `env_file` from both services. All env vars are now set explicitly in the `environment:` block using Docker service names (`postgres`, `minio:9000`, `chroma:8000`, `redis:6379`, `ollama:11434`).

**Verify fix is active:**
```bash
grep -n "env_file" docker-compose.yml
# Expected: no output (env_file lines removed)
```

---

## 1️⃣ Start the full stack

### Initial fresh build (first time only)

```bash
cd /path/to/veridoc

# ──────────────────────────────────────────────────
# IMPORTANT: Always rebuild before first start
# so the alembic env.py fix is picked up
# ──────────────────────────────────────────────────

docker compose build backend worker
```

### Start all services

```bash
docker compose up -d
```

This starts: `postgres` · `redis` · `chroma` · `minio` · `ollama` · `backend` · `worker` · `frontend`

### Monitor health

```bash
# Watch all containers come up healthy
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

Expected state after ~60 seconds:

| Container | Status |
|-----------|--------|
| `veridoc-postgres` | `(healthy)` |
| `veridoc-redis` | `(healthy)` |
| `veridoc-chroma` | `Up` |
| `veridoc-minio` | `(healthy)` |
| `veridoc-ollama` | `Up` (pulling model in background) |
| `veridoc-backend` | `(healthy)` |
| `veridoc-worker` | `(healthy)` |
| `veridoc-frontend` | `Up` |

### Verify the API is responding

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Expected: {"status":"healthy","dependencies":
#   {"postgres":"ok","chroma":"ok","minio":"ok","llm":"ok"}}
```

### Verify the frontend is responding

Open `http://localhost:3000` in your browser. You should see the login page.

---

## 2️⃣ Run the evaluation harness

The evaluation runs every question in `eval/gold_qa.json` (208 Q&A pairs across 3 documents) through the full pipeline and reports precision@k, recall@k, MRR, faithfulness, and latency.

### Prerequisites

```bash
# Ensure the gold QA set exists
ls -la eval/gold_qa.json
# If missing, build it:
python scripts/build_gold_qa.py
```

### Run with `--compare` (head-to-head: naive dense vs hybrid+rerank)

```bash
python scripts/run_eval.py --compare
```

This runs the entire gold set **twice** — once with naive dense-only retrieval, once with the full hybrid BM25+dense+rerank pipeline — and produces a side-by-side comparison table.

**Expected output (table format):**

| Metric | Naive Dense | Hybrid+Rerank | Δ |
|--------|------------|---------------|----|
| Precision@5 | — | — | — |
| Recall@5 | — | — | — |
| MRR | — | — | — |
| Faithfulness | — | — | — |
| P50 latency | — | — | — |
| P95 latency | — | — | — |
| Avg token cost | — | — | — |
| Refusal correctness | — | — | — |

> ⏱️ **Note:** This takes ~10-30 minutes depending on Ollama model size and CPU. The LLM generation step is the bottleneck (~5-15s per question with a local model).

### Run without comparison (hybrid+rerank only)

```bash
python scripts/run_eval.py
```

### Troubleshooting

**"ERROR: gold_qa.json not found"**
```bash
python scripts/build_gold_qa.py
```

**"Connection refused" errors**
→ Backend isn't running. Check `docker logs veridoc-backend --tail 30`.

**Ollama model not available**
→ Check `docker logs veridoc-ollama --tail 5` — it may still be downloading the model (4.9GB for `llama3.1:8b`).

---

## 3️⃣ Run the red-team tests

8 prompt-injection test cases against the live Ollama model.

```bash
# Ensure Ollama has a model loaded
docker ps | grep ollama

# Run the security test suite
python -m pytest tests/ -k "security or jwt or redteam" -v
```

**Expected output:**
```
tests/test_auth.py::test_jwt_signature_tampered PASSED
tests/test_auth.py::test_expired_jwt PASSED
tests/test_auth.py::test_cross_user_access PASSED
tests/test_security.py::test_prompt_injection_basic PASSED
tests/test_security.py::test_prompt_injection_hijack PASSED
tests/test_security.py::test_prompt_injection_role_play PASSED
tests/test_security.py::test_prompt_injection_ignore_instructions PASSED
tests/test_security.py::test_sql_injection PASSED
```

After confirming all pass, update `docs/security-notes.md` — replace each "⏳ Pending" with a real `✅ PASSED` result and the actual model output observed.

---

## 4️⃣ Run the load test

Measures p50/p95 latency and error rate at 1, 5, 10, and 25 concurrent users against the live stack.

### Using the Python script

```bash
python scripts/run_load_test.py
```

### Using Locust directly

```bash
# Install if not already present
pip install locust

# Run at increasing concurrency levels
locust -f scripts/locustfile.py --headless \
  -u 1 -r 1 --run-time 30s \
  --host http://localhost:8000 \
  --csv load-test-1u

locust -f scripts/locustfile.py --headless \
  -u 5 -r 1 --run-time 30s \
  --host http://localhost:8000 \
  --csv load-test-5u

locust -f scripts/locustfile.py --headless \
  -u 10 -r 2 --run-time 30s \
  --host http://localhost:8000 \
  --csv load-test-10u

locust -f scripts/locustfile.py --headless \
  -u 25 -r 5 --run-time 60s \
  --host http://localhost:8000 \
  --csv load-test-25u
```

**Expected output (example):**
```
#      users | 1       | 5      | 10      | 25
# p50 latency | 2.1s    | 2.4s   | 3.1s    | 5.8s
# p95 latency | 3.5s    | 4.2s   | 5.9s    | 12.3s
# error rate  | 0%      | 0%     | 0%      | 1.2%
```

### What to look for

- **Breaking point:** the concurrency level where error rate exceeds 5%
- **Key bottleneck:** likely the LLM generation (Ollama) which processes requests sequentially for a single model instance
- **Document it** in `docs/audit-before-after.md` under "Production Readiness"

---

## 5️⃣ Update docs with real numbers

After steps 2 and 4 produce real numbers, update these files:

| File | What to change |
|------|---------------|
| `docs/evaluation-report.md` | Replace all synthetic/estimated numbers with real measured results from step 2 |
| `docs/security-notes.md` | Replace "⏳ Pending" with real `✅ PASSED` / `❌ FAILED` per test case |
| `docs/audit-before-after.md` | Update "Production Readiness" section with real load-test data from step 4 |
| `README.md` | Update evaluation table and add load-test results |

**Quick copy-paste for evaluation-report updates:**

```bash
# After step 2 produces output, copy the table into evaluation-report.md
# The script already writes to docs/evaluation-report.md automatically
cat docs/evaluation-report.md | head -80
```

---

## 6️⃣ Deploy (optional — requires cloud account)

Full deployment guide: `docs/deployment-runbook.md`

### Recommended: Render.com (simplest free tier)

1. Push repo to GitHub
2. Create a **Web Service** on Render, connect your repo
3. Set build command: `docker compose build`
4. Set start command: `docker compose up -d`
5. Add environment variables from `.env.production.example`
6. Deploy

### Alternative: Fly.io

```bash
# Install flyctl
fly launch
fly secrets set JWT_SECRET=<generated> FILE_ENCRYPTION_KEY=<generated>
fly deploy
```

### Alternative: Vercel (frontend) + managed Postgres (backend)

Frontend can run on Vercel's free tier. Backend needs VPS (Railway, Fly.io, or $5 DO droplet).

---

## 7️⃣ Record demo video (optional — requires screen recording)

Full script: `docs/demo-script.md` (90-120 seconds)

### Scene outline

| Time | Scene | Action |
|------|-------|--------|
| 0:00 | Sign up | Fill registration form, submit |
| 0:15 | Upload document | Select a PDF, watch ingestion progress |
| 0:30 | Ask a question | Type a question, see streaming answer with citations |
| 0:50 | Click a citation | Click a citation number, see scroll+highlight in document |
| 1:10 | Ask unanswerable | Type "What is the meaning of life?", see correct refusal |
| 1:30 | End | Show dashboard with conversations list |

### After recording

Replace the placeholder banner in `README.md` with:
```markdown
[![Demo Video](path/to/demo.gif)](docs/demo-script.md)
```

---

## Progress checklist

- [ ] `docker compose up -d` boots all 8 services
- [ ] `curl http://localhost:8000/api/v1/health` returns healthy
- [ ] Frontend loads at `http://localhost:3000`
- [ ] `python scripts/run_eval.py --compare` produces real numbers
- [ ] `python -m pytest -k "security or jwt" -v` — all 8 tests pass
- [ ] `python scripts/run_load_test.py` produces p50/p95 at 4 concurrency levels
- [ ] `docs/evaluation-report.md` has real numbers (not synthetic)
- [ ] `docs/security-notes.md` has real pass/fail (not pending)
- [ ] `docs/audit-before-after.md` updated with load-test data
- [ ] `README.md` updated with real evaluation + load-test numbers
- [ ] (Optional) Live demo deployed to Render/Fly.io
- [ ] (Optional) Demo video recorded and linked from README

---

## Troubleshooting

### Backend keeps restarting with `127.0.0.1` connection error

```bash
# This is the alembic hardcoded-IP bug. Verify the fix was applied:
docker logs veridoc-backend --tail 10 | grep "127.0.0.1"
# If this still shows 127.0.0.1, the image is stale — rebuild:
docker compose build backend
docker compose up -d backend
```

### Backend still won't start

```bash
# Check the full log
docker logs veridoc-backend

# Common causes:
# 1. PostgreSQL not ready yet — wait for health check
# 2. Chroma not ready — wait and retry
# 3. Alembic migration error — check for schema conflicts:
docker compose run backend alembic history
```

### Ollama model pull takes too long

The `llama3.1:8b` model is 4.9GB. On a slow connection this can take 10-30 minutes. You can:
- Let it finish (background pull, non-blocking)
- Use a smaller model: set `OLLAMA_MODEL=llama3.2:3b` in `docker-compose.yml`
- For evaluation only, disable Ollama and use the standalone eval script:
  ```bash
  python scripts/run_standalone_eval.py
  ```

### `docker compose` not found

```bash
# Make sure Docker Desktop is running
# On Mac/Linux: use `docker compose` (v2)
# On older systems: use `docker-compose` (v1) — install via:
pip install docker-compose
```

### Port conflicts

```bash
# Check if ports are already in use
netstat -an | grep -E "(5432|6379|8000|8001|9000|11434)"

# Change ports in docker-compose.yml if needed
# Or stop the conflicting service first
```
