# ================================================================
# SUPERCELL — Hugging Face Spaces Dockerfile
# Multi-stage: builds Next.js static UI, then runs FastAPI server
# HF Spaces expects port 7860 by default
# ================================================================

# ── Stage 1: Build Next.js static export ────────────────────────
FROM node:20-slim AS web-builder

WORKDIR /build

# Install pnpm
RUN npm install -g pnpm@9

# Copy workspace manifests (all packages needed for frozen install)
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY apps/web/package.json ./apps/web/
COPY apps/video/package.json ./apps/video/

# Install dependencies (frozen lockfile)
RUN pnpm install --frozen-lockfile

# Copy web source (only what's needed for the build)
COPY apps/web ./apps/web

# Build static export → apps/web/out/
# NODE_ENV=production activates output:"export" in next.config.ts
RUN pnpm --filter @supercell/web build

# ── Stage 2: Python FastAPI runtime ─────────────────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy Python deps first (cache layer)
COPY pyproject.toml uv.lock* README.md ./
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Copy application code
COPY apps/api ./apps/api
COPY openenv.yaml ./

# Copy built Next.js static output from previous stage
COPY --from=web-builder /build/apps/web/out ./apps/web/out

# HF Spaces uses port 7860; the server reads the PORT env var
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV ENABLE_WEB_INTERFACE=true

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

CMD ["uv", "run", "python", "apps/api/main.py"]
