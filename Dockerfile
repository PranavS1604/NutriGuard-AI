# ============================================================
# NutriGuard AI — Dockerfile
# Multi-stage build for Cloud Run deployment
# ============================================================

# --- Build Stage ---
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Runtime Stage ---
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ ./app/
COPY data/ ./data/
COPY frontend/ ./frontend/

# Cloud Run listens on PORT env var (default 8080)
ENV PORT=8080
ENV HOST=0.0.0.0
ENV WORKERS=1
ENV LOG_LEVEL=info
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

EXPOSE ${PORT}

# Run FastAPI with uvicorn
CMD uvicorn app.api.main:app \
    --host ${HOST} \
    --port ${PORT} \
    --workers ${WORKERS} \
    --log-level ${LOG_LEVEL} \
    --no-access-log
