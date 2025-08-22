# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Package Management & Development Commands

- **ALWAYS use uv** to run the server and manage dependencies - do not use pip directly
- Use `uv sync` to install dependencies and `uv sync --group dev` for development dependencies
- The name to use for Github commits is jumas45 and the email to use is jumas45@gmail.com

### Essential Commands

**Server Management:**
```bash
# Run the main RAG application server
cd backend && uv run python rag_app.py

# Run the simple API server (testing/development)
cd backend && uv run python app.py
```

**Code Quality & Testing:**
```bash
# Format code (black + isort)
make format

# Run linting (flake8 + mypy)
make lint

# Run comprehensive quality checks
make quality-check

# Run tests
uv run pytest backend/tests/
```

**Dependency Management:**
```bash
# Install all dependencies
uv sync

# Install with development tools
uv sync --group dev

# Add new dependency
uv add package-name
```

## Architecture Overview

This is a **RAG (Retrieval-Augmented Generation) system** for course materials with a FastAPI backend and modern web frontend.

### Core Components

**RAG System Architecture:**
- `rag_system.py` - Main orchestrator that coordinates all components
- `vector_store.py` - ChromaDB-based semantic search and storage
- `ai_generator.py` - LLM integration (Anthropic Claude + Google Gemini support)
- `document_processor.py` - Processes course documents into searchable chunks
- `search_tools.py` - Tool-based search system with CourseSearchTool and CourseOutlineTool
- `session_manager.py` - Manages conversation context and history

**API Layer:**
- `rag_app.py` - Main production FastAPI application with full RAG functionality
- `app.py` - Simplified API for testing/development with mock responses

**Configuration:**
- `config.py` - Centralized configuration using environment variables and dataclasses
- Supports switching between Anthropic Claude and Google Gemini via `LLM_PROVIDER` env var

### Data Flow

1. **Document Processing**: Course documents → text chunks → vector embeddings → ChromaDB
2. **Query Processing**: User query → semantic search → relevant chunks → LLM generation → response
3. **Tool Integration**: AI can use CourseSearchTool and CourseOutlineTool for enhanced retrieval

### Frontend Integration

- Single-page application with HTML/CSS/JS in project root
- FastAPI serves static files and provides REST API endpoints
- Real-time course analytics, session logging, and sample questions

### Configuration Requirements

Set these environment variables in `.env`:
```bash
LLM_PROVIDER=anthropic  # or "gemini"
ANTHROPIC_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```

The system automatically loads course documents from `./docs/` on startup and maintains persistent vector storage in `backend/chroma_db/`.