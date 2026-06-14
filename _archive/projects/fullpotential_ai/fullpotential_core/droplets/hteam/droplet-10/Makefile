.PHONY: help install setup test test-cov run dev docker-build docker-up docker-down clean lint format

# Default target
.DEFAULT_GOAL := help

# ============================================================================
# HELP
# ============================================================================
help:
	@echo "Orchestrator - Development Commands"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install        Install Python dependencies"
	@echo "  make setup          Complete setup (install + database)"
	@echo "  make db-create      Create database"
	@echo "  make db-migrate     Run database migrations"
	@echo ""
	@echo "Development Commands:"
	@echo "  make run            Run application (production mode)"
	@echo "  make dev            Run application (development mode with reload)"
	@echo "  make test           Run all tests"
	@echo "  make test-cov       Run tests with coverage report"
	@echo "  make lint           Run code linting"
	@echo "  make format         Format code with black"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-build   Build Docker image"
	@echo "  make docker-up      Start all services"
	@echo "  make docker-down    Stop all services"
	@echo "  make docker-logs    View logs"
	@echo "  make docker-test    Run tests in Docker"
	@echo ""
	@echo "Cleanup Commands:"
	@echo "  make clean          Remove generated files"
	@echo "  make clean-docker   Remove Docker volumes"

# ============================================================================
# SETUP
# ============================================================================
install:
	pip install -r requirements.txt

setup: install db-create db-migrate
	@echo "Setup complete! Run 'make dev' to start the application."

db-create:
	createdb orchestrator_db || echo "Database already exists"
	createdb orchestrator_test_db || echo "Test database already exists"

db-migrate:
	psql -U postgres -d orchestrator_db -f schema.sql
	psql -U postgres -d orchestrator_test_db -f schema.sql

# ============================================================================
# DEVELOPMENT
# ============================================================================
run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn app.main:app --reload --port 8000 --log-level debug

# ============================================================================
# TESTING
# ============================================================================
test:
	pytest -v

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

test-watch:
	pytest-watch

# ============================================================================
# CODE QUALITY
# ============================================================================
lint:
	flake8 app/ tests/
	mypy app/

format:
	black app/ tests/
	isort app/ tests/

format-check:
	black --check app/ tests/
	isort --check app/ tests/

# ============================================================================
# DOCKER
# ============================================================================
docker-build:
	docker build -t orchestrator:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f orchestrator

docker-test:
	docker-compose --profile test up -d test-db
	docker-compose run --rm orchestrator pytest
	docker-compose --profile test down

docker-restart:
	docker-compose restart orchestrator

# ============================================================================
# DATABASE MANAGEMENT
# ============================================================================
db-shell:
	psql -U postgres -d orchestrator_db

db-reset:
	dropdb orchestrator_db --if-exists
	createdb orchestrator_db
	psql -U postgres -d orchestrator_db -f schema.sql

# ============================================================================
# CLEANUP
# ============================================================================
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build

clean-docker:
	docker-compose down -v
	docker volume prune -f

# ============================================================================
# MONITORING
# ============================================================================
logs:
	tail -f logs/orchestrator.log

health:
	curl http://localhost:8000/health

metrics:
	curl http://localhost:8000/metrics/summary