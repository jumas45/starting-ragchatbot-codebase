# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Setup

**Prerequisites:**
- Python 3.13+ and uv package manager
- Anthropic API key in `.env` file: `ANTHROPIC_API_KEY=your_key_here`
- For Windows users: Use Git Bash for shell commands

**Installation:**
```bash
uv sync
```

**Running the application:**
```bash
# Quick start
chmod +x run.sh && ./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

**Application URLs:**
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Architecture Overview

This is a RAG (Retrieval-Augmented Generation) chatbot system with a tool-based architecture where Claude autonomously decides when to search course materials.

### Core Components Flow

**Frontend → Backend → RAG System → AI Generator → Tool Manager → Vector Store**

1. **Frontend** (`frontend/`): Simple HTML/JS interface that sends queries to `/api/query`
2. **FastAPI App** (`backend/app.py`): Main server with two endpoints - `/api/query` for chat and `/api/courses` for stats
3. **RAG System** (`backend/rag_system.py`): Orchestrates the entire query process and manages components
4. **AI Generator** (`backend/ai_generator.py`): Handles Claude API calls with tool execution capability
5. **Tool Manager & Search Tools** (`backend/search_tools.py`): Manages the search tool that Claude can call
6. **Vector Store** (`backend/vector_store.py`): ChromaDB-based semantic search with metadata filtering

### Document Processing Pipeline

Documents in `/docs` follow a structured format and are processed on startup:

1. **Document Processor** (`backend/document_processor.py`): Parses course metadata and lesson structure
2. **Text Chunking**: Sentence-based chunking with configurable overlap (800 chars, 100 overlap)
3. **Vector Storage**: Chunks stored in ChromaDB with course/lesson metadata for filtering

### Key Architectural Patterns

**Tool-Based Search**: Claude decides autonomously whether to search course content or use general knowledge. The search tool supports:
- Semantic search across all content
- Course name filtering (partial matches work)
- Lesson number filtering
- Source tracking for UI display

**Session Management**: Conversation history is maintained per session with configurable message limits.

**Configuration**: All settings centralized in `backend/config.py` with environment variable support.

## Document Format

Course documents should follow this structure:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [instructor]

Lesson 0: Introduction
Lesson Link: [lesson_url]
[lesson content...]

Lesson 1: Next Topic
[content...]
```

## Key Files to Understand

- `backend/rag_system.py`: Entry point for all query processing
- `backend/ai_generator.py`: Claude API integration with tool execution
- `backend/search_tools.py`: Tool interface and search implementation
- `backend/document_processor.py`: Document parsing and chunking logic
- `backend/config.py`: Configuration management
- `frontend/script.js`: Client-side query handling and UI updates

## Development Notes

**Adding New Tools**: Implement the `Tool` interface in `search_tools.py` and register with `ToolManager`

**Vector Store Operations**: The system automatically loads documents from `/docs` on startup and avoids re-processing existing courses

**API Response Format**: All queries return `{answer, sources, session_id}` where sources show which courses/lessons informed the response

**Error Handling**: Each component has graceful error handling with fallbacks to prevent system crashes