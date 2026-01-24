.PHONY: help install lint format typecheck test check run

help:		## Show this help
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

install:	## Install dependencies
	pip install -e ".[dev]"

lint:		## Run linter
	ruff check src tests

format:		## Format code
	ruff format src tests
	ruff check --fix src tests

typecheck:	## Run type checker
	basedpyright src

test:		## Run tests
 pytest -v

test-cov:	## Run tests with coverage
	pytest -v --cov=src --cov-report=html

check:		## Run all quality checks
	ruff check src tests
	basedpyright src
	pytest -v

run:		## Run the application
	python -m snapcast_mvp

clean:		## Clean build artifacts
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
