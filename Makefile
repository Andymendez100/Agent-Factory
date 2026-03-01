# Agent Factory — Development Commands
# =====================================

.PHONY: help setup up down restart logs test lint build clean

# Default target
help: ## Show this help message
	@echo "Agent Factory — available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── Setup ──────────────────────────────────────────────────

setup: ## First-time setup: copy .env and generate Fernet key
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example"; \
		FERNET_KEY=$$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "GENERATE_ME"); \
		sed -i.bak "s/your-fernet-key-here/$$FERNET_KEY/" .env && rm -f .env.bak; \
		echo "Generated FERNET_KEY in .env"; \
		echo ""; \
		echo "Next steps:"; \
		echo "  1. Add your OPENAI_API_KEY to .env"; \
		echo "  2. Run: make up"; \
	else \
		echo ".env already exists — skipping"; \
	fi

# ── Docker Compose ─────────────────────────────────────────

up: ## Start all services (docker-compose up)
	docker compose up -d --build
	@echo ""
	@echo "Services starting:"
	@echo "  Frontend:    http://localhost:3000"
	@echo "  Backend API: http://localhost:8000"
	@echo "  Swagger:     http://localhost:8000/docs"
	@echo "  Mock Portal: http://localhost:8001"
	@echo ""

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose restart

logs: ## Tail logs from all services
	docker compose logs -f

logs-backend: ## Tail backend logs only
	docker compose logs -f backend celery-worker

# ── Development ────────────────────────────────────────────

test: ## Run backend tests
	cd backend && python3 -m pytest tests/ -v

test-quick: ## Run backend tests (quiet output)
	cd backend && python3 -m pytest tests/ -q

frontend-dev: ## Start frontend dev server (without Docker)
	cd frontend && npm run dev

frontend-build: ## Build frontend for production
	cd frontend && npx vite build

frontend-check: ## TypeScript type-check
	cd frontend && npx tsc --noEmit

# ── Database ───────────────────────────────────────────────

db-migrate: ## Run Alembic migrations
	cd backend && alembic upgrade head

db-seed: ## Seed demo data
	cd backend && python3 -m app.db.seed

# ── Cleanup ────────────────────────────────────────────────

clean: ## Remove Docker volumes and build artifacts
	docker compose down -v
	rm -rf frontend/dist frontend/node_modules/.vite
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned up."
