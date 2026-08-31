# ── Veridoc — Multi-stage Docker Build ──────────────────────────────────────
# Targets:
#   backend  — FastAPI + Uvicorn (Python 3.12-slim)
#   frontend — Next.js production server (Node 20-alpine)
#
# Usage:
#   docker compose up               # builds both services
#   docker build --target backend .  # backend only
#   docker build --target frontend . # frontend only
# ────────────────────────────────────────────────────────────────────────────

# ════════════════════════════════════════════════════════════════════════════
# BACKEND — Python FastAPI
# ════════════════════════════════════════════════════════════════════════════
FROM python:3.14-slim AS backend

WORKDIR /app

# System deps for OCR + PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (cached layer)
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --timeout 120 --retries 5 -r /tmp/requirements.txt

# Application code
COPY backend/ /app/
ENV PYTHONPATH=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import urllib.request, urllib.error\ntry:\n    urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=5)\nexcept urllib.error.HTTPError as e:\n    exit(0 if e.code == 503 else 1)\nexcept Exception:\n    exit(1)"]

STOPSIGNAL SIGTERM
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

# ════════════════════════════════════════════════════════════════════════════
# FRONTEND — Next.js
# ════════════════════════════════════════════════════════════════════════════
FROM node:20-alpine AS frontend-build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund --legacy-peer-deps

COPY frontend/ .
RUN mkdir -p /app/public && npm run build

# Production runner
FROM node:20-alpine AS frontend

WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=frontend-build /app/public ./public
COPY --from=frontend-build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=frontend-build --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

STOPSIGNAL SIGTERM
CMD ["node", "server.js"]
