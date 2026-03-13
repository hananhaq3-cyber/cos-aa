# ═══════════════════════════════════════════════════════════════
# COS-AA Makefile — Common development and deployment commands
# ═══════════════════════════════════════════════════════════════

.PHONY: help dev test lint build deploy-staging deploy-prod migrate proto clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Development ───

dev: ## Start local development stack (docker-compose + uvicorn)
	docker compose -f docker-compose.dev.yml up -d
	sleep 3
	alembic upgrade head
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

dev-services: ## Start only infrastructure services (PostgreSQL, Redis, Chroma)
	docker compose -f docker-compose.dev.yml up -d postgres redis chromadb

dev-frontend: ## Start frontend dev server
	cd frontend && npm run dev

dev-worker: ## Start Celery worker
	celery -A src.messaging.broker:celery_app worker --loglevel=info --concurrency=2

dev-beat: ## Start Celery Beat scheduler
	celery -A src.messaging.broker:celery_app beat --loglevel=info

# ─── Database ───

migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="description")
	alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Rollback last migration
	alembic downgrade -1

# ─── Testing ───

test: ## Run all tests
	pytest tests/ -v

test-unit: ## Run unit tests only
	pytest tests/unit/ -v --cov=src --cov-report=term-missing

test-integration: ## Run integration tests
	pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests
	pytest tests/e2e/ -v

test-cov: ## Run tests with coverage report
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=90

# ─── Linting ───

lint: ## Run linter
	ruff check src/ tests/

lint-fix: ## Run linter with auto-fix
	ruff check --fix src/ tests/

format: ## Format code
	ruff format src/ tests/

type-check: ## Run type checker
	mypy src/ --ignore-missing-imports

# ─── Protobuf ───

proto: ## Regenerate gRPC Python stubs from .proto files
	python -m grpc_tools.protoc \
		-I protos/ \
		--python_out=protos/generated/ \
		--grpc_python_out=protos/generated/ \
		--pyi_out=protos/generated/ \
		protos/memory_service.proto \
		protos/agent_service.proto

# ─── Docker ───

build: ## Build all Docker images
	docker build -t cos-aa-api:latest -f infra/docker/Dockerfile.api .
	docker build -t cos-aa-hub:latest -f infra/docker/Dockerfile.hub .
	docker build -t cos-aa-agent-base:latest -f infra/docker/Dockerfile.agent-base .
	docker build -t cos-aa-worker:latest -f infra/docker/Dockerfile.worker .

build-api: ## Build API image only
	docker build -t cos-aa-api:latest -f infra/docker/Dockerfile.api .

# ─── Deployment ───

deploy-staging: ## Deploy to staging via Helm
	@for chart in api hub agents worker; do \
		helm upgrade --install cos-aa-$$chart infra/helm/cos-aa-$$chart/ \
			--namespace cos-aa-staging --create-namespace --wait; \
	done

deploy-prod: ## Deploy to production via Helm
	@for chart in api hub agents worker; do \
		helm upgrade --install cos-aa-$$chart infra/helm/cos-aa-$$chart/ \
			--namespace cos-aa-production --create-namespace --wait --timeout 600s; \
	done

infra-plan: ## Terraform plan
	cd infra/terraform && terraform plan

infra-apply: ## Terraform apply
	cd infra/terraform && terraform apply

# ─── Cleanup ───

clean: ## Stop dev services and clean build artifacts
	docker compose -f docker-compose.dev.yml down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .mypy_cache htmlcov .coverage dist build *.egg-info
