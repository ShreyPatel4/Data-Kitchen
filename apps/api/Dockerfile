FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY apps/api/src/ ./apps/api/src/
COPY engines/ ./engines/
COPY apps/api/alembic/ ./apps/api/alembic/
COPY apps/api/alembic.ini ./apps/api/

ENV PYTHONPATH=/app/apps/api/src:/app
ENV PYTHONUNBUFFERED=1

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

CMD ["uvicorn", "nova_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
