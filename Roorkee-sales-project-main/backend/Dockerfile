# Multi-stage build with two runtime targets — `dev` (hot-reload, source
# mounted as a volume by docker-compose.yml) and `production` (immutable
# image, no reload, non-root user, multiple workers). Both share the same
# dependency-install layer so there's only one place that installs packages.

FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# A dedicated, unprivileged user — the container never needs root once
# dependencies are installed (defense in depth: a compromised app process
# can't touch anything outside its own working directory).
RUN useradd --create-home --uid 1000 appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# --- Development target: source mounted at runtime, auto-reload on save ---
FROM base AS dev
COPY . .
RUN chown -R appuser:appuser /app
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# --- Production target: source baked into the image, no reload, multiple workers ---
FROM base AS production
COPY . .
RUN chown -R appuser:appuser /app
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
