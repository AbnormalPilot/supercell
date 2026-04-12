# ================================================================
# SUPERCELL — VABB Mumbai ATC Emergency Triage
# Matches the reference submission's Dockerfile architecture:
# pip install to SYSTEM Python so bare `python` can import everything.
# ================================================================

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install deps to SYSTEM Python (not a venv) so `python` and
# `docker exec ... python -c "from server.environment import ..."` work.
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir -r requirements.txt

# Copy everything
COPY . .

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start via uvicorn directly (not uv run) — system Python has all deps.
CMD ["sh", "-c", "uvicorn server.app:app --host 0.0.0.0 --port ${PORT:-7860}"]
