FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project --no-dev

COPY . /app

RUN uv sync --frozen --no-dev


FROM python:3.14-slim AS runner

RUN apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -m -g appuser appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app /app

RUN mkdir -p /app/uploads /app/meta.lmdb && \
    chown appuser:appuser /app /app/uploads /app/meta.lmdb

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 5000

VOLUME ["/app/uploads", "/app/meta.lmdb"]

CMD ["gunicorn", "-w", "4", "--preload", "-b", "0.0.0.0:5000", "main:app"]
