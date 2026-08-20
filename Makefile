.PHONY: up down test lint typecheck migrate seed
up:
	docker compose up --build
down:
	docker compose down
test:
	cd backend && python -m pytest
	cd frontend && npm test -- --run
lint:
	cd backend && ruff check app tests
	cd frontend && npm run lint
typecheck:
	cd backend && mypy app
	cd frontend && npm run typecheck
migrate:
	cd backend && alembic upgrade head
seed:
	cd backend && python -m app.seed

