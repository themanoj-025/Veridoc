FROM python:3.12-slim

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
RUN pip install --no-cache-dir -r requirements.txt

# Install email-validator separately to avoid cache invalidation on requirements.txt changes
RUN pip install --no-cache-dir email-validator==2.2.0

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
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health'); exit(0)" 2>/dev/null || exit 1

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
