# Security Policy

## Supported Versions

| Version | Supported          |
|---------|-------------------|
| 0.1.x   | ✅ Active development |

## Reporting a Vulnerability

If you discover a security vulnerability in Veridoc, **please do not open a public GitHub issue**. Instead, email **security@veridoc.dev** with:

1. **Description** of the vulnerability
2. **Steps to reproduce** — including any specific configuration required
3. **Impact assessment** — what an attacker could achieve
4. **Suggested fix** (optional, but appreciated)

You should receive a response within **48 hours**. If you don't, please follow up.

**We will:**
- Acknowledge receipt within 48 hours
- Provide an estimated timeline for a fix
- Credit you in the release notes (unless you prefer to remain anonymous)
- Notify you when the fix is deployed

## Current Security Posture

### ✅ Implemented Protections

| Layer | Protection | Status |
|-------|-----------|--------|
| **Authentication** | JWT (30min access + 7d refresh tokens), bcrypt hashing | Active |
| **Token Management** | Refresh-token rotation (reuse detection), server-side logout | Active |
| **Authorization** | Row-level ownership checks on every document/conversation endpoint | Active |
| **Startup Validation** | Refuses to boot with empty or placeholder secrets (`JWT_SECRET`, `FILE_ENCRYPTION_KEY`) | Active |
| **Rate Limiting** | 5 req/min on auth routes, 30 req/min general API | Active |
| **Input Validation** | Pydantic v2 schema enforcement, password complexity (≥8 chars, ≥2 of: uppercase/digit/symbol) | Active |
| **Prompt Injection** | Retrieved content wrapped in `<retrieved_context>` markers — 8/8 red-team tests pass | Active |
| **XSS Prevention** | Content-Security-Policy headers via Next.js middleware + rehype-sanitize on LLM output | Active |
| **Data at Rest** | Files encrypted with Fernet (AES-128-CBC + HMAC) | Active |
| **Dependency Scanning** | Dependabot configured for pip, npm, Docker, GitHub Actions | Active |

### ⚙️ Configuration Recommendations

For production deployments, additionally:

1. **Use a secrets manager** (HashiCorp Vault, AWS Secrets Manager) instead of `.env` files
2. **Set stronger rate limits** based on expected traffic patterns
3. **Enable HTTPS** via a reverse proxy (Caddy, Nginx, or platform-managed TLS)
4. **Add a Web Application Firewall** (Cloudflare, AWS WAF) in front of the API
5. **Run the full red-team suite** against your chosen LLM model — model-level behavior varies significantly

### Red-Team Test Results

| ID | Name | Severity | Result | Verified |
|----|------|----------|--------|----------|
| inject-001 | Direct system prompt override | high | ✅ PASS (defense verified) | 2026-07-28 |
| inject-002 | Fake instruction boundary | high | ✅ PASS (defense verified) | 2026-07-28 |
| inject-003 | Role-playing extraction | medium | ✅ PASS (defense verified) | 2026-07-28 |
| inject-004 | Hypothetical scenario injection | medium | ✅ PASS (defense verified) | 2026-07-28 |
| inject-005 | Ignore data boundary | high | ✅ PASS (defense verified) | 2026-07-28 |
| inject-006 | Token smuggling | medium | ✅ PASS (defense verified) | 2026-07-28 |
| inject-007 | Context manipulation | medium | ✅ PASS (defense verified) | 2026-07-28 |
| inject-008 | Multi-language injection | medium | ✅ PASS (defense verified) | 2026-07-28 |

**8/8 tests passed** at the defense-mechanism level (instruction boundaries, data marking, chunk isolation). For production, validate against your specific LLM model's behavior.

## Vulnerability Disclosure Timeline

| Phase | Duration |
|-------|----------|
| Report received | Day 0 |
| Acknowledgment | Within 48 hours |
| Fix developed | Target: 7 days |
| Fix released | Target: 14 days |
| Public disclosure | After fix is deployed |

## Security-Related Configuration

```bash
# Generate a secure JWT secret
python -c "import secrets; print(secrets.token_hex(32))"

# Generate a Fernet-compatible encryption key
python -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

These values should never be committed to version control. Always use `.env` files or a secrets manager.
