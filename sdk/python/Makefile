.PHONY: install test lint format check-format check-types clean

# Variables
PYTHON = python3
PIP = pip3
PYTEST = python -m pytest
BLACK = black
ISORT = isort
FLAKE8 = flake8
MYPY = mypy

# Install dependencies
install:
	$(PIP) install -e .
	$(PIP) install -r requirements-dev.txt

# Run tests
test:
	$(PYTEST) -v --cov=ticos_client --cov-report=term-missing

# Run linters
lint:
	$(FLAKE8) ticos_client tests
	$(MYPY) ticos_client

# Format code
format:
	$(BLACK) ticos_client tests
	$(ISORT) ticos_client tests

# Check code formatting
check-format:
	$(BLACK) --check ticos_client tests
	$(ISORT) --check-only ticos_client tests

# Run type checking
check-types:
	$(MYPY) ticos_client

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	rm -rf .coverage htmlcov build dist *.egg-info

# Default target
all: install test lint check-format check-types
