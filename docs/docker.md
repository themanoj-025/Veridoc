# Veridoc — Docker Guide

## Quick start

```bash
cp .env.example .env
docker compose up -d --build
```

Local-first stack (zero external accounts): PostgreSQL, MinIO (`:9000`),
Chroma vector DB, Redis, Ollama (local LLM), ARQ worker, FastAPI backend
(`:8000`), and Next.js frontend (`:3000`).

## Production

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Key differences: no source bind mounts, resource limits on every service,
tuned restart policies, production logging (json-file rotation), and an
optional Caddy reverse proxy block for TLS (requires `DOMAIN` + Caddyfile).

## Environment

See `.env.example` and `docker-compose.yml`. Notable vars: `POSTGRES_*`,
`MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`, `OLLAMA_MODEL`, `DOMAIN`,
`NEXT_PUBLIC_API_URL`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Ollama slow first start | Prod entrypoint pre-pulls `${OLLAMA_MODEL:-llama3.1:8b}`; allow `start_period: 120s` |
| Frontend can't reach API | Set `NEXT_PUBLIC_API_URL` |
| Backend 503 on chat | Ollama unavailable — backend degrades gracefully for non-chat endpoints |
