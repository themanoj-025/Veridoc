# AppFlow — Veridoc: Application Flow

|Field|Value|
|---|---|
|Version|v0.1|
|Last Updated|2026-08-06|
|Owner|Product Designer|
|Status|Approved|

---

## 1. Screen Inventory

|ID|Screen|Purpose|Entry|Exit|Auth|
|---|---|---|---|---|---|
|SCR-001|Register|Create account|/register|Login|N|
|SCR-002|Login|Authenticate|/login|Dashboard|N|
|SCR-003|Dashboard|Document library|/|Upload, chat|Y|
|SCR-004|Upload / Ingestion|Upload + progress|dashboard|Library|Y|
|SCR-005|Chat|Ask + stream + citations|dashboard|New chat / upload|Y|
|SCR-006|Document Detail|Content + metadata|library|Chat, manage|Y|
|SCR-007|Error / Health Degraded|Dependency down notice|app-wide|Retry|N|

## 2. Navigation Map

```mermaid
graph LR
    SCR-001 -->|register| SCR-002
    SCR-002 -->|login| SCR-003
    SCR-003 -->|upload| SCR-004
    SCR-003 -->|open doc| SCR-006
    SCR-003 -->|chat| SCR-005
    SCR-004 -->|done| SCR-003
    SCR-006 -->|chat about doc| SCR-005
    SCR-006 -->|manage| SCR-003
    SCR-005 -->|new chat| SCR-005
    SCR-007 -->|retry| SCR-003
```

## 3. Detailed Flow per Journey

### 3.1 Onboarding

```mermaid
stateDiagram-v2
    [*] --> Register
    Register --> Login: account created
    Login --> Dashboard: JWT cookie set
    Login --> Error: invalid creds / rate-limited
    Error --> Login: retry
```

### 3.2 Ingestion

```mermaid
stateDiagram-v2
    [*] --> Upload
    Upload --> Queued: file accepted
    Queued --> Parsing: job starts
    Parsing --> Chunking: parsed
    Chunking --> Embedding: chunks ready
    Embedding --> Indexed: vectors stored
    Indexed --> Library: ready to query
    Parsing --> Failed: OCR/parse error
    Failed --> Upload: retry
```

### 3.3 Chat with Citations

```mermaid
stateDiagram-v2
    [*] --> Composing
    Composing --> Rewriting: submit question
    Rewriting --> Retrieving: standalone query
    Retrieving --> Reranking: top-20 candidates
    Reranking --> Generating: top-5 passages
    Generating --> Checking: candidate answer
    Checking --> Streaming: faithful
    Checking --> Regenerating: unfaithful
    Regenerating --> Generating: retry
    Streaming --> Composing: done
```

## 4. Empty / Loading / Error States

|Screen|Empty|Loading|Error|
|---|---|---|---|
|SCR-003|"Upload your first document" CTA|Skeleton cards|Banner + retry|
|SCR-004|N/A|Progress per stage (parse→chunk→embed→index)|Stage-level failure with retry|
|SCR-005|Empty chat hint|Streaming indicator (typing)|Faithfulness refusal + suggestion|
|SCR-006|"No content"|Skeleton|Banner|
|SCR-007|N/A|Dependency spinner|Which dependency failed, retry|

## 5. Edge Cases & Branching Logic

|IF|THEN|
|---|---|
|Upload > 50MB|Accept but note streaming ingestion (scale item)|
|Unsupported format|Reject with allowed list (PDF/DOCX/TXT)|
|Scanned PDF|OCR fallback path|
|Query with no doc selected|Ask user to pick a document|
|Answer fails faithfulness|Refuse gracefully + regenerate|
|Provider (Ollama) down|Health degraded; UI notice|
|Cross-user document id|403 row-level isolation|

## 6. Notifications & Re-engagement

- In-app: ingestion-complete toast; ingestion-failed toast with retry.
- No email/push in v1.

## 7. Cross-Platform Deltas

- Responsive web only (Next.js). API is platform-agnostic.
- Mobile: chat full-screen; citations open in document panel.

## 8. Related Documents

|Document|Relationship|
|---|---|
|[PRD.md](../product/PRD.md)|Journeys to user stories|
|[Design.md](Design.md)|Components per screen|
|[API.md](../technical/API.md)|Endpoints behind flows|
|[Schema.md](../technical/Schema.md)|Data objects|
