.PHONY: help dev down logs migrate test lint format typecheck clean shell-db

PYTHON ?= uv run
COMPOSE ?= docker compose -f infra/docker-compose.yml

help:
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*##"};{printf "  %-15s %s\n",$$1,$$2}'

dev:        ## sobe postgres+pgvector, redis, api, worker
	$(COMPOSE) up -d --build

down:       ## para os containers
	$(COMPOSE) down

logs:       ## logs em follow
	$(COMPOSE) logs -f --tail=200

migrate:    ## roda alembic upgrade head
	$(PYTHON) alembic upgrade head

migrate-new: ## cria migration: make migrate-new MSG=add_x
	$(PYTHON) alembic revision --autogenerate -m "$(MSG)"

test:       ## pytest com cobertura minima 90
	$(PYTHON) pytest -ra --cov=packages --cov=apps --cov-fail-under=90

test-unit:
	$(PYTHON) pytest -ra -m "not integration"

lint:       ## ruff check
	$(PYTHON) ruff check .

format:     ## ruff format + isort
	$(PYTHON) ruff format .
	$(PYTHON) ruff check --fix .

typecheck:  ## mypy strict em packages e apps
	$(PYTHON) mypy packages apps

clean:      ## limpa caches
	-$(PYTHON) ruff clean .
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage

shell-db:   ## psql no banco
	$(COMPOSE) exec postgres psql -U dba -d developer_brain