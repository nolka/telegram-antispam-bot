.PHONY: up down logs test lint migrate migrate-init shell

# Docker
up:          docker-compose up -d
down:        docker-compose down
logs:        docker-compose logs -f bot-app
shell:       docker-compose exec bot-app bash

# Tests
test:        python -m pytest tests/ -v
test-cov:    python -m pytest tests/ -v --cov=. --cov-report=term-missing

# Linting
lint:        flake8 .
format:      isort . && black .

# Database
migrate:     alembic upgrade head
migrate-init: alembic downgrade base && alembic upgrade head
migrate-gen: alembic revision --autogenerate -m "$(msg)"
