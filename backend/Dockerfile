FROM python:3.14-slim

WORKDIR /app

# Install system dependencies for OCR + PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt

# Install email-validator separately to avoid cache invalidation on requirements.txt changes
RUN pip install --no-cache-dir --timeout 120 --retries 5 email-validator==2.2.0

# Copy application code
# NOTE: Increment BUILD_NUMBER below to force Docker cache invalidation for the COPY layer.
# Docker Desktop on Windows sometimes fails to detect file changes in the build context.
ARG BUILD_NUMBER=0
RUN test "$BUILD_NUMBER" -ge 0 && echo "Build $BUILD_NUMBER"
COPY . .

# Ensure alembic can find migrations
ENV PYTHONPATH=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import urllib.request, urllib.error\ntry:\n    urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=5)\nexcept urllib.error.HTTPError as e:\n    # 503 = degraded deps (e.g. LLM model not pulled yet) — server is alive\n    exit(0 if e.code == 503 else 1)\nexcept Exception:\n    exit(1)"]

STOPSIGNAL SIGTERM
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
