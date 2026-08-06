# Veridoc — Next Steps

> Generated 2026-07-31 during Perpetual Loop closeout pass.
> Items below require Docker, a cloud account, or human action.

---

## Tier 2 — Requires Local Docker Stack

### 26. F4 (verify) — Live email flow
```bash
# 1. Start the stack with MailHog
docker compose up -d mailhog postgres backend

# 2. Register a new user and request verification
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPass123!"}'

# 3. Get the verification token from backend logs
docker compose logs backend | grep "verification_token"

# 4. Verify email
curl -X POST "http://localhost:8000/api/v1/auth/verify-email?token=<TOKEN>"

# 5. Test password reset
curl -X POST "http://localhost:8000/api/v1/auth/request-password-reset?email=test@example.com"
docker compose logs backend | grep "reset_token"
curl -X POST "http://localhost:8000/api/v1/auth/reset-password?token=<TOKEN>&new_password=NewPass123!"
```

### 27. F7 (verify) — Virus scan with EICAR test file
```bash
# 1. Upload a real EICAR test file
echo -n 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > /tmp/eicar.txt
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!"}' | jq -r '.access_token')

curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/eicar.txt" \
  -F "title=EICAR Test"

# Expected: file is rejected or flagged (depends on V irusScanner implementation)
```

### 28. F9 (verify) — Index effectiveness with EXPLAIN ANALYZE
```bash
# Run against a populated database
docker compose exec postgres psql -U veridoc -c "
EXPLAIN ANALYZE SELECT * FROM documents WHERE user_id = '<some-uuid>' AND status = 'indexed';
EXPLAIN ANALYZE SELECT * FROM conversations WHERE user_id = '<some-uuid>' AND is_active = true;
"

# Compare with the same queries before the indexes
# Expected: Seq Scan → Index Scan improvement
```

### 29. F19 (verify) — Document preview against real ingested PDFs
```bash
# 1. Upload the sample Gutenberg text
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@data/documents/gutenberg_132.txt"

# 2. Wait for indexing
# 3. Open http://localhost:3000/dashboard -> select document
# 4. Verify document preview renders and citation highlighting works
```

### 30. G5 — Demo/playground mode
```bash
# 1. Set DEMO_MODE=true in .env, restart stack
# 2. Verify: no registration page, no delete-account button
# 3. Verify: sample documents are pre-seeded
```

### 31. G7 — Public status page
```bash
# 1. Navigate to http://localhost:3000/status
# 2. Verify all 5 dependencies show green
# 3. Simulate a dependency outage and verify degraded status
```

### 32. G10 — Cost-budget alerting
```bash
# 1. Set monthly_token_budget in .env
# 2. Generate queries until budget is exceeded
# 3. Verify warning log and optional local-model fallback
```

---

## Tier 3 — Requires Human/Cloud Action

### 33. A1 — Full evaluation harness

**Prep already done (2026-07-31):**
1. `scripts/run_eval.py` had a latent bug — gold-set `document_id` slugs
   (`gutenberg_132`, `arxiv_*`, …) were passed verbatim to the retriever,
   which filters by real DB document UUIDs, so every filtered question would
   have retrieved nothing. Fixed: `resolve_document_ids()` now lives in
   `app/services/evaluation.py` and resolves slugs → UUIDs (fuzzy
   filename/title match) with wildcard/DB-error fallback to search-all.
2. `use_hybrid=False` was a **no-op** — the `--compare` naive run used the
   identical hybrid pipeline, making the head-to-head table meaningless.
   Fixed: the naive path now runs dense-only retrieval (no BM25/RRF/rerank).
3. Unit tests: `backend/tests/test_eval_harness.py` (15 tests: matching,
   wildcards, resolution, fallbacks, resolver wiring, naive-path wiring).

```bash
# 1. Start the full stack (Postgres, Chroma, Ollama, backend, frontend)
docker compose up -d
# Wait for health: docker compose ps should show all healthy

# 2. Seed documents into the DB + Chroma so retrieval has a corpus.
#    Upload the sample corpus via the API (this is what populates Chroma):
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
for f in data/documents/*.txt data/documents/*.md data/documents/*.pdf; do
  curl -X POST http://localhost:8000/api/v1/documents/upload \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$f" -F "title=$(basename $f)"
done
# NOTE: if a seed user doesn't exist, register one first:
#   curl -X POST http://localhost:8000/api/v1/auth/register -H "Content-Type: application/json" \
#     -d '{"email":"test@example.com","password":"TestPass123!","full_name":"Eval User"}'

# 3. Wait for indexing to finish, then run the full evaluation
sleep 30
python scripts/run_eval.py --compare

# 4. Verify the real measured report was written
tail -40 eval/evaluation-report.md
```

**Deliverable:** `eval/evaluation-report.md` generated fresh with real
measured numbers (answer/refusal accuracy, mean faithfulness, P50/P95
latency). Note: the report does not exist in the repo yet, so the first real
run creates it — there are no stale estimated numbers to hunt down. Then
update the scorecard in `docs/audit-before-after.md` from the measured
results.

### 34. A2 — Red-team tests
```bash
python -m pytest tests/ -k "security or jwt or redteam" -v
python scripts/run_redteam_live.py
```

### 35. A3 — Real load test
```bash
locust -f scripts/locustfile.py --headless -u 5 -r 1 --run-time 30s
locust -f scripts/locustfile.py --headless -u 10 -r 2 --run-time 60s
locust -f scripts/locustfile.py --headless -u 25 -r 5 --run-time 120s
```

### 36. A4 — Deploy public demo
```bash
# Follow docs/deployment-runbook.md
# Use DEMO_MODE=true for the public deployment
```

### 37. A5 — Record demo walkthrough
```bash
# Follow docs/demo-script.md
# Capture 90-120 second screen recording
```
