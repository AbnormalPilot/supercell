# ================================================================
# SUPERCELL — Hugging Face Spaces Dockerfile (Python-Only)
# Pure Python Gradio UI + FastAPI backend
# HF Spaces expects port 7860 by default
# ================================================================

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates git && \
    rm -rf /var/lib/apt/lists/*

# Install uv for fast Python dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy Python deps first (cache layer)
COPY pyproject.toml uv.lock* README.md ./
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Copy application code
COPY apps/api ./apps/api
COPY openenv.yaml ./
COPY app.py ./

# HF Spaces uses port 7860
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

CMD ["uv", "run", "python", "app.py"]
