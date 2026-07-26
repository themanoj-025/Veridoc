# Veridoc — Next Steps

> Items deferred from the autonomous build that require human action, cloud accounts, or are optional enhancements.

---

## 🔴 Blocking (require human with account)

### 1. OAuth App Registration (Google/GitHub)
To enable OAuth-based login, register OAuth apps:
- **Google Cloud Console**: Create OAuth 2.0 credentials → set redirect URI to `http://localhost:8000/api/auth/google/callback`
- **GitHub Developer Settings**: Create OAuth App → set callback URL to `http://localhost:8000/api/auth/github/callback`
- Add `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` to `.env`

### 2. Cloud Deployment
The stack is ready for cloud deployment. Choose a platform:

#### Option A: Render
```yaml
# render.yaml (provided in repo root)
services:
  - type: web
    name: veridoc-backend
    env: docker
    dockerfilePath: ./backend/Dockerfile
  - type: web
    name: veridoc-frontend
    env: docker
    dockerfilePath: ./frontend/Dockerfile
```

#### Option B: Fly.io
```bash
fly launch
fly secrets set JWT_SECRET=... ANTHROPIC_API_KEY=...
fly deploy
```

#### Option C: AWS ECS
Use `docker compose -f docker-compose.yml -f docker-compose.prod.yml up`

### 3. Custom Domain
- Buy a domain
- Set DNS records pointing to your deployment
- Configure TLS termination

### 4. Production Secrets
Generate strong secrets:
```bash
python -c "import secrets; print(secrets.token_hex(32))"  # JWT_SECRET
python -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"  # FILE_ENCRYPTION_KEY
```

---

## 🟡 Optional Enhancements

### 5. Claude/GPT API Integration
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

### 6. SSO / SAML
Implement SAML-based SSO for enterprise customers. Use `python3-saml` library.

### 7. Multi-tenant Orgs + RBAC
Add organization table, role-based access control (admin, editor, viewer).

### 8. Audit Log
Enable comprehensive audit logging for compliance (HIPAA, SOC2).

### 9. On-Prem / Private Cloud Guide
Provide Helm chart for Kubernetes deployment and air-gapped installation.

### 10. Demo GIF Recording
Record a terminal-based demo GIF:
```bash
# Using terminalizer or asciinema
asciinema rec veridoc-demo.cast
# Then convert to GIF
agg veridoc-demo.cast veridoc-demo.gif
```

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

### 12. Load Testing
```bash
# Using locust
pip install locust
locust -f tests/load_test.py --host=http://localhost:8000
```

---

## ✅ How to use this file
1. Pick any item from the list
2. Complete the required human steps (create account, register app, buy domain)
3. Uncomment relevant code paths
4. Remove the item from this file
5. Update documentation
