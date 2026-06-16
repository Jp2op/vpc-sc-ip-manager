FROM python:3.12-slim AS base

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["gunicorn", "app.main:app", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "1", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--threads", "4", \
     "--timeout", "120", \
     "--access-logfile", "-"]
