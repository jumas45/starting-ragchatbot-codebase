# RAG Chatbot with Code Quality Tools

This project includes essential code quality tools for maintaining consistent, high-quality Python code.

## Code Quality Tools

The following tools are configured and ready to use:

- **Black**: Code formatter for consistent style
- **isort**: Import sorter for organized imports  
- **Flake8**: Style guide enforcement and error detection
- **Mypy**: Static type checker

## Usage

### Quick Commands

Using the Makefile (recommended):

```bash
# Format code
make format

# Run linting checks  
make lint

# Run all quality checks
make quality-check

# Install dependencies
make install
```

### Direct Script Usage

```bash
# Format code with black and isort
uv run python scripts/format.py

# Run linting with flake8 and mypy
uv run python scripts/lint.py

# Run comprehensive quality checks
uv run python scripts/quality-check.py
```

### Individual Tool Usage

```bash
# Black formatting
uv run black src/

# Import sorting
uv run isort src/

# Flake8 linting
uv run flake8 src/

# Type checking
uv run mypy src/
```

## Development Setup

1. Install dependencies:
   ```bash
   uv sync --group dev
   ```

2. Run quality checks:
   ```bash
   make quality-check
   ```

## Pre-commit Hook

To automatically run quality checks before commits, you can set up the pre-commit hook:

```bash
# Copy the hook to your git hooks directory
cp scripts/pre-commit-hook.py .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Configuration

All tools are configured in `pyproject.toml`:

- **Black**: 88 character line length, Python 3.8+ target
- **isort**: Black-compatible profile
- **Flake8**: 88 character line length, ignore E203/W503
- **Mypy**: Standard configuration