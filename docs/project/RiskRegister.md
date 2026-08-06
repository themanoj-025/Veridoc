# RiskRegister — Veridoc: Known Risks & Mitigations

|Field|Value|
|---|---|
|Version|v0.1|
|Last Updated|2026-08-06|
|Owner|Program Manager|
|Status|Approved|

|ID|Risk|Likelihood|Impact|Score|Mitigation|Owner|Status|
|---|---|---|---|---|---|---|---|
|R-01|Eval numbers are 5-sample estimates, not live 23-question run|High|High|9|Complete OQ-01 live eval; relabel metrics|Owner|Open|
|R-02|ChromaDB doesn't scale horizontally|Medium|High|8|Documented Qdrant/Pinecone path|Owner|Open|
|R-03|Local env dep gap (`asyncpg`) blocks test import|High|Medium|8|Add to requirements; CI unaffected|Owner|Open (Tracker R-01)|
|R-04|Prompt-injection variant bypasses markers|Medium|High|8|8/8 red-team suite + ongoing adversarial review|Sec|Mitigated|
|R-05|LLM hallucination slips past faithfulness gate|Medium|High|8|Judge thresholds + refusal path + eval monitoring|Eng|Open|
|R-06|XSS via unsanitized LLM output|Low|High|6|rehype-sanitize + CSP|Sec|Mitigated|
|R-07|Document data exfiltration via cross-user id|Low|High|6|Row-level isolation + tests|Sec|Mitigated|
|R-08|BM25 warmup rebuild (~500ms first query)|Medium|Low|3|Persistent index (OQ-03)|Eng|Open|
|R-09|High P95 latency at scale|Medium|Medium|6|Rerank batching, Redis query cache, vLLM path|Eng|Open|
|R-10|No live demo/video limits portfolio impact|High|Medium|6|OQ-02 demo deliverable|Owner|Open|

## Risk Matrix

```mermaid
quadrantChart
    title Risk Prioritization
    x-axis Low Likelihood --> High Likelihood
    y-axis Low Impact --> High Impact
    quadrant-1 Watch: R-08
    quadrant-2 Manage: R-09, R-10
    quadrant-3 Avoid: R-06, R-07
    quadrant-4 Critical: R-01, R-02, R-03, R-04, R-05
```

## Top 3 Focus Risks

1. **R-01 Live eval pending** — gates all published accuracy claims; resolve via OQ-01.
2. **R-03 asyncpg gap** — blocks local dev tests; fix first.
3. **R-05 Faithfulness gate** — the core trust mechanism; monitor rejection rates.

## Related Documents

|Document|Relationship|
|---|---|
|[PRD.md](../product/PRD.md)|Top risk summary|
|[SecurityAndCompliance.md](../technical/SecurityAndCompliance.md)|Security risks|
|[Tracker.md](Tracker.md)|R-01 blocker + OQ status|
