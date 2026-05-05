.PHONY: help sync dev-setup format lint type-check test check pre-commit clean

# Include local customizations (optional)
-include Makefile.local

help:
	@echo "twilio-agent-connect-aws Development Commands:"
	@echo "  make sync        - Install dependencies (uses uv)"
	@echo "  make dev-setup   - Complete dev environment setup"
	@echo "  make format      - Format code with ruff"
	@echo "  make lint        - Run linting checks only"
	@echo "  make type-check  - Run mypy type checking"
	@echo "  make test        - Run pytest"
	@echo "  make check       - Run all checks (lint + type-check + test)"
	@echo "  make pre-commit  - Run pre-commit hooks"
	@echo "  make clean       - Clean build artifacts"

sync:
	uv sync --all-extras --all-packages

dev-setup: sync
	@echo "Setting up development environment..."
	uv run pre-commit install || true
	@echo "Development environment ready!"

format:
	@echo "Formatting code with ruff..."
	uv run ruff format src/tac_aws getting_started
	uv run ruff check --fix src/tac_aws getting_started

lint:
	@echo "Running lint checks..."
	uv run ruff check src/tac_aws getting_started

type-check:
	@echo "Running mypy type checking..."
	MYPYPATH=src uv run mypy src/tac_aws getting_started

test:
	@echo "Running tests..."
	uv run pytest

check: lint type-check test
	@echo "All checks passed!"

pre-commit:
	uv run pre-commit run --all-files

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete!"
