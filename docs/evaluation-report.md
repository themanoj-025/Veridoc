# Veridoc -- Evaluation Report

*Generated: 2026-07-28 15:31:48 UTC*
*Environment: Python 3.14.5, Standalone pipeline logic test*
*Full end-to-end metrics require live Docker stack (Postgres, Chroma, Ollama). See Reproduction section below.*

---

## 1. Pipeline Logic Test Results

### Faithfulness Check (3 test cases)

| Query | Faithfulness Score |
|-------|-------------------|
| What is the annual subscription fee? | 50.00% |
| How many servers can be installed? | 50.00% |
| What is the CEO's phone number? | 50.00% |

### Metrics Computation (5-sample gold set)

- **Total questions**: 5
- **Answer accuracy**: 100.0%
- **Refusal accuracy**: 100.0%
- **Mean faithfulness**: 87.6%
- **P50 latency**: 1100ms
- **P95 latency**: 1500ms

### Query Rewrite Logic

- **long_no_demonstrative**: None (no rewrite or LLM unavailable)
- **short_with_demonstrative**: None (no rewrite or LLM unavailable)
- **short_no_demonstrative**: None (no rewrite or LLM unavailable)
- **no_history**: None (no rewrite or LLM unavailable)

### Retrieval Module Integrity

- All retrieval module imports resolve correctly (bm25_search, RRF, HybridRetriever, rewrite_query)
- RRF fusion verified: 2 items merged from 2 lists, rrf_score present
- HybridRetriever interface verified: `retrieve()`, `rerank()` with `batch_size` parameter
- Rerank fallback works when cross-encoder model is not loaded

---

## 2. System Information

| Metric | Value |
|--------|-------|
| Python | 3.14.5 |
| Test cases (faithfulness) | 3 |
| Metrics sample | 5 |
| Backend tests passing | 73/73 |

---

## 3. Reproduction (Full End-to-End)

```bash
# Requires: Docker, Ollama, 8GB+ RAM
docker compose up -d
python scripts/run_eval.py --compare
```

*Veridoc standalone evaluation harness report. Full head-to-head comparison (naive dense vs. hybrid+rerank) requires the live stack.*
