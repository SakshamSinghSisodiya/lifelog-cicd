FROM python:3.12-slim

ARG APP_VERSION=dev
ARG GIT_COMMIT=dev
ARG BUILD_NUMBER=dev
ENV APP_VERSION=${APP_VERSION} \
    GIT_COMMIT=${GIT_COMMIT} \
    BUILD_NUMBER=${BUILD_NUMBER} \
    LIFELOG_DB=/app/data/lifelog.db \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY wsgi.py .

# Non-root user; only /app/data is writable (SQLite file lives there)
RUN useradd --create-home --uid 10001 lifelog \
    && mkdir -p /app/data \
    && chown -R lifelog:lifelog /app/data
USER lifelog

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2).status == 200 else 1)"

# One worker: SQLite is seeded at startup, threads give concurrency
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "wsgi:app"]
