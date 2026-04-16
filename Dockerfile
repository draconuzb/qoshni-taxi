FROM python:3.12.7-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends         gcc libpq-dev     && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12.7-slim

ENV PYTHONUNBUFFERED=1     PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends         libpq5 curl gosu     && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

WORKDIR /app
COPY . .

RUN useradd -m -u 1000 app     && mkdir -p /app/data     && chown -R app:app /app     && chmod +x /app/docker-entrypoint.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3     CMD curl -fsS http://localhost:8080/health || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "main.py"]
