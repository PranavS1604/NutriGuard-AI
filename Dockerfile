# --- Build Stage ---
FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Runtime Stage ---
FROM python:3.12-slim AS runtime
WORKDIR /app

# IMPORTANT: Install curl so the HEALTHCHECK command works
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY app/ ./app/
COPY data/ ./data/
COPY frontend/ ./frontend/

ENV PORT=8080
ENV HOST=0.0.0.0
ENV WORKERS=1
ENV LOG_LEVEL=info
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# The HEALTHCHECK will now work because curl is installed
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

EXPOSE ${PORT}

CMD uvicorn app.api.main:app \
    --host ${HOST} \
    --port ${PORT} \
    --workers ${WORKERS} \
    --log-level ${LOG_LEVEL}