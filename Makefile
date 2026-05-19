.PHONY: help up down logs test coverage migrate shell clean

help:
	@echo "Available commands:"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make logs        - View logs"
	@echo "  make test        - Run tests"
	@echo "  make coverage    - Run tests with coverage"
	@echo "  make migrate     - Run database migrations"
	@echo "  make shell       - Open shell in web container"
	@echo "  make clean       - Clean Docker volumes and cache"

up:
	docker-compose up -d --build
	@echo "Services started. API available at http://localhost:8000"

down:
	docker-compose down

logs:
	docker-compose logs -f web

test:
	docker-compose exec web pytest tests/ -v

coverage:
	docker-compose exec web pytest tests/ -v --cov=app --cov-report=term-missing

migrate:
	docker-compose exec web alembic upgrade head

shell:
	docker-compose exec web bash

clean:
	docker-compose down -v
	rm -rf logs/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
