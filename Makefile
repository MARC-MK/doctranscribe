.PHONY: dev test lint

dev:
	docker compose up --build

test:
	poetry run pytest -q

lint:
	ruff backend/app 