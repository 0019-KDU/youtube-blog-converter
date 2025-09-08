# YouTube Blog Converter Makefile
.PHONY: help install test test-unit test-integration test-e2e test-all test-coverage lint format clean dev

# Default target
help: ## Show this help message
	@echo "YouTube Blog Converter - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install dependencies
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-mock pytest-timeout selenium webdriver-manager

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-mock pytest-timeout selenium webdriver-manager
	pip install black flake8 isort bandit safety

# Testing
test-unit: ## Run unit tests only
	@echo "🧪 Running unit tests..."
	pytest tests/unit/ \
		--cov=app \
		--cov=auth \
		--cov=src \
		--cov-report=xml:coverage-unit.xml \
		--cov-report=html:htmlcov-unit \
		--cov-report=term-missing \
		-v \
		-m "not slow" \
		--tb=short \
		--timeout=300

test-integration: ## Run integration tests only
	@echo "🔗 Running integration tests..."
	pytest tests/integration/ \
		--cov=app \
		--cov=auth \
		--cov=src \
		--cov-report=xml:coverage-integration.xml \
		--cov-report=html:htmlcov-integration \
		--cov-report=term-missing \
		-v \
		-m "integration" \
		--tb=short \
		--timeout=600 \
		--run-integration

test-e2e: ## Run end-to-end tests only
	@echo "🚀 Running E2E tests..."
	pytest tests/e2e/ \
		-v \
		-m "e2e" \
		--tb=short \
		--timeout=900 \
		--run-e2e

test-unit-fast: ## Run unit tests (excluding slow tests)
	@echo "⚡ Running fast unit tests..."
	pytest tests/unit/ \
		-v \
		-m "not slow" \
		--tb=short \
		--timeout=60

test-slow: ## Run slow tests only
	@echo "🐌 Running slow tests..."
	pytest tests/ \
		-v \
		-m "slow" \
		--tb=short \
		--timeout=900

test-auth: ## Run authentication tests only
	@echo "🔐 Running authentication tests..."
	pytest tests/ \
		-v \
		-m "auth" \
		--tb=short

test-database: ## Run database tests only
	@echo "🗄️ Running database tests..."
	pytest tests/ \
		-v \
		-m "database" \
		--tb=short

test-api: ## Run API tests only
	@echo "🌐 Running API tests..."
	pytest tests/ \
		-v \
		-m "api" \
		--tb=short

test-workflow: ## Run workflow tests only
	@echo "🔄 Running workflow tests..."
	pytest tests/ \
		-v \
		-m "workflow" \
		--tb=short

test: test-unit ## Default test command (runs unit tests)

test-all: ## Run all tests (unit, integration, e2e)
	@echo "🧪🔗🚀 Running all tests..."
	pytest tests/ \
		--cov=app \
		--cov=auth \
		--cov=src \
		--cov-report=xml:coverage-all.xml \
		--cov-report=html:htmlcov-all \
		--cov-report=term-missing \
		-v \
		--tb=short \
		--timeout=900 \
		--run-integration \
		--run-e2e

test-coverage: ## Run tests with detailed coverage report
	@echo "📊 Running tests with coverage analysis..."
	pytest tests/unit/ tests/integration/ \
		--cov=app \
		--cov=auth \
		--cov=src \
		--cov-report=xml:coverage.xml \
		--cov-report=html:htmlcov \
		--cov-report=term-missing \
		--cov-fail-under=80 \
		-v \
		--run-integration

# Code Quality
lint: ## Run linting checks
	@echo "🔍 Running linting checks..."
	flake8 app/ auth/ src/ tests/ --max-line-length=100 --ignore=E203,W503
	black --check app/ auth/ src/ tests/
	isort --check-only app/ auth/ src/ tests/

format: ## Format code
	@echo "✨ Formatting code..."
	black app/ auth/ src/ tests/
	isort app/ auth/ src/ tests/

security: ## Run security checks
	@echo "🔒 Running security checks..."
	bandit -r app/ auth/ src/ -f json -o bandit-report.json
	safety check --json --output safety-report.json

# Development
dev: ## Start development server
	@echo "🚀 Starting development server..."
	python run.py

dev-debug: ## Start development server with debug enabled
	@echo "🐛 Starting development server with debug..."
	FLASK_DEBUG=1 python run.py

# Database
db-init: ## Initialize database
	@echo "🗄️ Initializing database..."
	python -c "from app import init_db; init_db()"

db-reset: ## Reset database (WARNING: This will delete all data)
	@echo "⚠️ Resetting database..."
	python -c "from app import reset_db; reset_db()"

# Cleanup
clean: ## Clean up generated files
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.coverage" -delete 2>/dev/null || true
	rm -rf htmlcov* coverage*.xml .coverage* 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info/ 2>/dev/null || true
	rm -rf bandit-report.json safety-report.json 2>/dev/null || true

clean-logs: ## Clean log files
	@echo "📝 Cleaning log files..."
	rm -rf logs/*.log logs/*.json 2>/dev/null || true

# Docker
docker-build: ## Build Docker production image
	@echo "🐳 Building production Docker image..."
	./scripts/docker-build.sh --target production

docker-build-dev: ## Build Docker development image
	@echo "🐳 Building development Docker image..."
	./scripts/docker-build.sh --target development --no-tests

docker-build-test: ## Build Docker test runner image
	@echo "🐳 Building test runner Docker image..."
	./scripts/docker-build.sh --target test-runner --no-tests

docker-test: ## Run tests in Docker container
	@echo "🐳🧪 Running tests in Docker container..."
	docker-compose --profile test up test --build

docker-test-unit: ## Run unit tests in Docker
	@echo "🐳🧪 Running unit tests in Docker..."
	docker build --target unit-test -t youtube-blog-converter:unit-test .
	docker run --rm youtube-blog-converter:unit-test

docker-test-integration: ## Run integration tests in Docker
	@echo "🐳🧪 Running integration tests in Docker..."
	docker-compose --profile test up test-integration --build

docker-run: ## Run Docker container (production)
	@echo "🐳 Running production Docker container..."
	docker-compose up app --build

docker-run-dev: ## Run Docker container (development)
	@echo "🐳 Running development Docker container..."
	docker-compose --profile dev up app-dev --build

docker-run-full: ## Run full Docker stack (app + MongoDB + Redis)
	@echo "🐳 Running full Docker stack..."
	docker-compose up --build

docker-run-monitoring: ## Run with monitoring stack
	@echo "🐳📊 Running with monitoring stack..."
	docker-compose --profile monitoring up --build

docker-stop: ## Stop Docker containers
	@echo "🐳 Stopping Docker containers..."
	docker-compose down

docker-clean: ## Clean Docker containers and images
	@echo "🧹 Cleaning Docker containers and images..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	docker volume prune -f

docker-clean-all: ## Clean all Docker data (WARNING: removes all containers, images, volumes)
	@echo "🧹 WARNING: Cleaning ALL Docker data..."
	@read -p "Are you sure? This will remove ALL Docker containers, images, and volumes [y/N]: " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker system prune -a -f --volumes; \
		echo "✅ All Docker data cleaned"; \
	else \
		echo "❌ Cancelled"; \
	fi

docker-logs: ## Show Docker container logs
	@echo "📋 Showing Docker logs..."
	docker-compose logs -f app

docker-logs-test: ## Show Docker test logs
	@echo "📋 Showing Docker test logs..."
	docker-compose --profile test logs -f test

docker-shell: ## Open shell in running Docker container
	@echo "🐚 Opening shell in Docker container..."
	docker-compose exec app /bin/bash

docker-shell-dev: ## Open shell in development Docker container
	@echo "🐚 Opening shell in development Docker container..."
	docker-compose --profile dev exec app-dev /bin/bash

docker-push: ## Push Docker image to registry
	@echo "🚀 Pushing Docker image to registry..."
	./scripts/docker-build.sh --push

docker-security-scan: ## Run security scan on Docker image
	@echo "🔍 Running security scan..."
	docker scan youtube-blog-converter:latest || echo "Security scan completed with warnings"

# CI/CD Helpers
ci-unit: ## CI unit tests (optimized for CI environment)
	pytest tests/unit/ \
		--cov=app --cov=auth --cov=src \
		--cov-report=xml:coverage-unit.xml \
		--cov-report=term \
		-v -x --tb=short --timeout=300

ci-integration: ## CI integration tests (optimized for CI environment)
	pytest tests/integration/ \
		--cov=app --cov=auth --cov=src \
		--cov-report=xml:coverage-integration.xml \
		--cov-report=term \
		-v -x --tb=short --timeout=600 \
		--run-integration

ci-e2e: ## CI E2E tests (optimized for CI environment)
	pytest tests/e2e/ \
		-v -x --tb=short --timeout=900 \
		--run-e2e

# Health Checks
health-check: ## Check application health
	@echo "🏥 Checking application health..."
	curl -f http://localhost:5000/health || echo "❌ Health check failed"

ping: ## Ping application
	@echo "🏓 Pinging application..."
	curl -I http://localhost:5000/ || echo "❌ Application not responding"

# Utilities
logs: ## Show application logs
	@echo "📋 Showing recent logs..."
	tail -f logs/app.json

requirements: ## Update requirements.txt
	@echo "📝 Updating requirements.txt..."
	pip freeze > requirements.txt

info: ## Show project information
	@echo "📊 Project Information:"
	@echo "Python version: $$(python --version)"
	@echo "Pip version: $$(pip --version)"
	@echo "Project structure:"
	@tree -I 'env|__pycache__|.git|node_modules' -L 2 || ls -la