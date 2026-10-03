.PHONY: run test lint fmt

run:
	.venv/bin/uvicorn app.main:app --reload

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check .

fmt:
	.venv/bin/ruff format . && .venv/bin/ruff check --fix .

.PHONY: up down logs

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f app
