.PHONY: format lint quality-check install dev-install

# Install dependencies
install:
	uv sync

# Install development dependencies
dev-install:
	uv sync --group dev

# Format code with black and isort
format:
	uv run python scripts/format.py

# Run linting checks
lint:
	uv run python scripts/lint.py

# Run comprehensive quality checks
quality-check:
	uv run python scripts/quality-check.py

# Quick format shortcut
fmt: format

# Quick lint shortcut  
l: lint

# Quick quality check shortcut
qc: quality-check