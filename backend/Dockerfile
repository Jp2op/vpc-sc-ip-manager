# ---- Build stage: install deps in a throwaway layer ----
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---- Runtime stage: lean final image ----
FROM python:3.12-slim

# Don't buffer stdout/stderr (logs appear instantly in kubectl logs)
ENV PYTHONUNBUFFERED=1
# Don't write .pyc files (smaller image, no stale bytecode)
ENV PYTHONDONTWRITEBYTECODE=1

# Non-root user
RUN groupadd -r appuser && useradd -r -g appuser -s /usr/sbin/nologin appuser

WORKDIR /app

# Copy only installed packages from builder (no build tools in final image)
COPY --from=builder /install /usr/local

# Copy app code with correct ownership
COPY --chown=appuser:appuser app/ ./app/

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["gunicorn", "app.main:app", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--threads", "4", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]