# syntax=docker/dockerfile:1

# ---- Build stage: compile wheels so the runtime image needs no toolchain --
FROM python:3.13-slim AS builder

WORKDIR /build

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt gunicorn==23.0.0


# ---- Runtime stage -------------------------------------------------------
FROM python:3.13-slim

# PYTHONDONTWRITEBYTECODE: no .pyc in the image (they were committed to the
# repo at one point, so this is doubly deliberate).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* \
 && rm -rf /wheels

# Run as a non-root user.
RUN useradd --create-home --shell /bin/bash appuser

COPY --chown=appuser:appuser . .

# SQLite file and uploads must be writable, and should be mounted as volumes
# so they survive a container rebuild.
RUN mkdir -p /app/data /app/uploads/articles \
 && chown -R appuser:appuser /app/data /app/uploads

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"

CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
