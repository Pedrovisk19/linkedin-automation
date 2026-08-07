FROM python:3.14-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# UV
RUN pip install --no-cache-dir uv==0.5.11

WORKDIR /app

# Copia manifesto primeiro p/ cache de layers
COPY pyproject.toml ruff.toml ./
COPY packages ./packages
COPY apps ./apps

# Sincroniza deps do workspace
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

ENV PATH="/opt/venv/bin:$PATH"

# Imagem final reaproveita base
FROM base AS api
COPY . /app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

FROM base AS worker
COPY . /app
CMD ["python", "-m", "app.main"]