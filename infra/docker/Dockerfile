FROM python:3.14-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# UV
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copia manifesto primeiro p/ cache de layers
COPY pyproject.toml ruff.toml uv.lock ./
COPY packages ./packages
COPY apps ./apps

# Sincroniza deps do workspace (inclui members editaveis)
RUN uv sync --no-dev --all-packages

ENV PATH="/opt/venv/bin:$PATH"

# Imagem final reaproveita base
FROM base AS api
ENV PYTHONPATH="/app/apps/api"
COPY . /app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

FROM base AS worker
ENV PYTHONPATH="/app/apps/worker"
COPY . /app
CMD ["python", "-m", "arq", "app.main.WorkerSettings"]