.PHONY: help install db-up db-down migrate seed dev test lint fmt clean

help:
	@echo "Concierge dev targets:"
	@echo "  make install     - install Python deps into .venv"
	@echo "  make db-up       - start Postgres+Redis via docker compose"
	@echo "  make db-down     - stop local containers"
	@echo "  make migrate     - apply SQL migrations"
	@echo "  make seed        - seed demo tenant + skills"
	@echo "  make dev         - run all services locally (honcho)"
	@echo "  make test        - run pytest"

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -U pip && pip install -r requirements.txt

db-up:
	docker compose -f infra/docker-compose.dev.yml up -d

db-down:
	docker compose -f infra/docker-compose.dev.yml down

migrate:
	@for f in db/migrations/*.sql; do \
		echo "Applying $$f"; \
		psql $${DATABASE_URL_SYNC:-postgresql://concierge:concierge@localhost:5432/concierge} -f $$f; \
	done

seed:
	@for f in db/seeds/*.sql; do \
		echo "Seeding $$f"; \
		psql $${DATABASE_URL_SYNC:-postgresql://concierge:concierge@localhost:5432/concierge} -f $$f; \
	done

dev:
	honcho start -f infra/Procfile.dev

test:
	. .venv/bin/activate && pytest -q

lint:
	. .venv/bin/activate && ruff check .

fmt:
	. .venv/bin/activate && ruff format .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov dist build
