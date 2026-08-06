# SecurityAndCompliance — Veridoc: Security & Compliance

| Field | Value |
| --- | --- |
| Version | v0.1 |
| Last Updated | 2026-08-06 |
| Owner | Security Engineer |
| Status | Approved |

---

## 1. Threat Model (STRIDE)

| Threat | Asset | Mitigation |
| --- | --- | --- |
| Spoofing | User identity | JWT (30min) + rotating refresh (7d), bcrypt hashing |
| Tampering | Documents/answers | Fernet encryption at rest; faithfulness gate; row isolation |
| Repudiation | Q&A history | Messages persist with conversation ownership |
| Info disclosure | Doc content (PII) | Encryption at rest, row-level isolation, log truncation |
| DoS | API | Rate limiting (5/min auth, 30/min general) |
| Elevation | Cross-user docs | user_id from JWT verified on every endpoint |
| Prompt injection | LLM output | `<retrieved_context>` boundaries + 8/8 red-team tests |
| XSS | Client | CSP headers + rehype-sanitize on LLM output |
| Secret leak | Env secrets | Startup fail-fast on empty/placeholder; Dependabot |

Full detail: `docs/security-notes.md` (8/8 red-team pass).

## 2. Auth & Authz

| Layer | Policy |
| --- | --- |
| Access token | JWT, 30 min, in-memory client storage |
| Refresh token | 7 days, bcrypt-hashed at rest, rotation per use, server-side logout |
| Row-level isolation | Every document/conversation endpoint checks `user_id` claim |
| Rate limiting | 5/min auth, 30/min general (slowapi) |
| Password policy | ≥ 8 chars, 2 of upper/digit/symbol |

## 3. Data Classification

| Class | Examples | Handling |
| --- | --- | --- |
| Credentials | password hashes, refresh hashes | bcrypt, never logged |
| PII | email, document contents | Encrypted at rest, masked logs |
| Secrets | JWT_SECRET, FILE_ENCRYPTION_KEY | Env only; fail-fast validation |
| Public | health status | No restriction |

## 4. Encryption Standards

- Files at rest: Fernet (AES-128-CBC + HMAC), key derived via SHA-256 from env secret.
- Transit: TLS 1.2+ at ingress (cloud deploys).
- Passwords: bcrypt.

## 5. Compliance Checklist

- [ ] 8/8 red-team tests (JWT tamper, expired JWT, cross-user, SQLi, 4 prompt injections)
- [ ] Row-level isolation on all user-scoped endpoints
- [ ] Startup secret validation (refuses placeholder/empty secrets)
- [ ] Dependabot vulnerability scanning in CI
- [ ] CSP + sanitization on all LLM-rendered content
- [ ] Local-first: no document data leaves the host by default (zero cloud)

## 6. Incident Response (Outline) — see docs/../reference/deployment-runbook.md

1. Detect: alert on metrics/health failures or security event.
2. Triage: auth vs data vs LLM-provider surface.
3. Mitigate: revoke refresh tokens, quarantine document, roll back.
4. Recover: re-index from encrypted store; verify faithfulness on sample.
5. Postmortem: update security-notes + Tracker changelog ≤ 48h.

## 7. Related Documents

| Document | Relationship |
| --- | --- |
| [API.md](API.md) | Auth endpoints |
| [Rules.md](../project/Rules.md) | Security baseline (Section 6) |
| [RiskRegister.md](../project/RiskRegister.md) | Security risks |
| [Schema.md](Schema.md) | Sensitive data map |
