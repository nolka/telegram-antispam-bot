.PHONY: up down logs test test-cov lint flake8 migrate migrate-init migrate-gen shell

# Docker
up:
	docker-compose up -d
down:
	docker-compose down
logs:
	docker-compose logs -f bot-app
shell:
	docker-compose exec bot-app bash

# Tests
test:
	venv/bin/python -m pytest tests/ -v
test-cov:
	venv/bin/python -m pytest tests/ -v --cov=. --cov-report=term-missing

# Linting
PYLINT := venv/bin/python -m pylint
lint:
	$(PYLINT) --fail-under 7 --ignore-paths ./tests .
flake8:
	flake8 .

# Database
migrate:
	alembic upgrade head
migrate-init:
	alembic downgrade base && alembic upgrade head
migrate-gen:
	alembic revision --autogenerate -m "$(msg)"
