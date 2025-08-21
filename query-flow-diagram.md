# RAG Chatbot Query Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                  FRONTEND                                       │
│                               (script.js)                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ User types query
                                      │ POST /api/query, /api/courses, /api/logs
                                      │ { query, session_id }
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               FASTAPI ENDPOINTS                               │
│                                 (app.py)                                       │
│                                                                                 │
│  @app.post("/api/query") - Main chat endpoint                                 │
│  @app.get("/api/courses") - Course analytics                                  │
│  @app.get("/api/logs") - Session logs                                         │
│  @app.post("/api/logs/clear") - Clear logs                                    │
│  ├─ Create session if needed                                                   │
│  ├─ Call rag_system.query(query, session_id)                                  │
│  └─ Return QueryResponse(answer, sources with links, session_id)              │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               RAG SYSTEM                                       │
│                            (rag_system.py)                                     │
│                                                                                 │
│  query() method:                                                               │
│  ├─ Get conversation history from session_manager                             │
│  ├─ Call LLM provider.generate_response() (Anthropic/Gemini)                  │
│  ├─ Get sources from tool_manager                                             │
│  └─ Update session history                                                    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          LLM PROVIDER ABSTRACTION                             │
│                            (llm_providers.py)                                  │
│                                                                                 │
│  AnthropicProvider / GeminiProvider:                                           │
│  ├─ Build system prompt + conversation history                                │
│  ├─ Call LLM API (Claude/Gemini) with tools available                         │
│  ├─ If LLM wants to use tools → handle_tool_execution()                       │
│  ├─ Log token usage via session_logger                                        │
│  └─ Return final response                                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ LLM decides to search/get outline
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              TOOL MANAGER                                      │
│                            (search_tools.py)                                   │
│                                                                                 │
│  execute_tool("search_course_content" | "get_course_outline"):                │
│  ├─ Route to CourseSearchTool or CourseOutlineTool                            │
│  ├─ Execute with appropriate parameters                                        │
│  ├─ Track sources with links for UI                                           │
│  └─ Return formatted results                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      COURSE TOOLS (search_tools.py)                           │
│                                                                                 │
│  CourseSearchTool:                    CourseOutlineTool:                       │
│  ├─ Call vector_store.search()       ├─ Get course metadata                   │
│  ├─ Format with course/lesson info   ├─ Format complete outline               │
│  ├─ Store sources with lesson links  ├─ Include all lesson titles            │
│  └─ Return formatted results         └─ Return course structure               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              VECTOR STORE                                      │
│                            (vector_store.py)                                   │
│                                                                                 │
│  search():                            get_all_courses_metadata():              │
│  ├─ Encode query using transformers   ├─ Return complete course info          │
│  ├─ Search ChromaDB similarity        ├─ Include lesson structures            │
│  ├─ Apply filters                     └─ Support outline generation           │
│  ├─ Return chunks with metadata                                               │
│  └─ SearchResults(docs, meta, error)                                          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Search results / Course outlines
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              RESULT FLOW                                       │
│                                                                                 │
│  Search Results / Course Outline                                              │
│        │                                                                       │
│        ▼                                                                       │
│  Tool.format_results() - Format with course/lesson context                    │
│        │                                                                       │
│        ▼                                                                       │
│  ToolManager.execute_tool() returns formatted results                         │
│        │                                                                       │
│        ▼                                                                       │
│  LLM Provider sends results back to LLM (Claude/Gemini)                       │
│        │                                                                       │
│        ▼                                                                       │
│  LLM synthesizes final answer                                                 │
│        │                                                                       │
│        ▼                                                                       │
│  RAGSystem.query() returns (answer, sources with links)                       │
│        │                                                                       │
│        ▼                                                                       │
│  FastAPI returns QueryResponse with enhanced source objects                   │
│        │                                                                       │
│        ▼                                                                       │
│  Frontend displays answer + clickable source links                            │
│                                                                                 │
│  PARALLEL: session_logger tracks tokens and system events                     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW EXAMPLES                                │
│                                                                                 │
│  EXAMPLE 1: Content Search                                                    │
│  User Query: "What is computer use in Anthropic course?"                      │
│                                                                                 │
│  LLM Tool Call:                                                                │
│  search_course_content(                                                       │
│    query="computer use",                                                      │
│    course_name="Anthropic"                                                    │
│  )                                                                             │
│                                                                                 │
│  Vector Search Result:                                                         │
│  "[Building Towards Computer Use with Anthropic - Lesson 0]                   │
│   Anthropic made a recent breakthrough and released a model                   │
│   that could use a computer. That is, it can look at the screen..."           │
│                                                                                 │
│  LLM Final Answer:                                                             │
│  "Computer use in Anthropic refers to their breakthrough model                │
│   capability that allows AI to interact with computers by taking              │
│   screenshots and generating mouse clicks or keystrokes..."                   │
│                                                                                 │
│  Sources: [{"text": "Building Towards Computer Use - Lesson 0",               │
│            "link": "https://lesson-url"}]                                     │
│                                                                                 │
│  EXAMPLE 2: Course Outline Request                                            │
│  User Query: "Show me the structure of the MCP course"                        │
│                                                                                 │
│  LLM Tool Call:                                                                │
│  get_course_outline(course_title="MCP")                                       │
│                                                                                 │
│  Tool Result:                                                                  │
│  "**Course Title:** Introduction to Model Context Protocol                     │
│   **Course Link:** https://course-link                                        │
│   **Instructor:** Course Author                                               │
│   **Lessons:**                                                                 │
│   Lesson 0: Introduction                                                      │
│   Lesson 1: Basic Concepts                                                    │
│   ..."                                                                         │
│                                                                                 │
│  LLM Final Answer: [Returns complete formatted outline]                       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Key Components:

1. **Frontend**: User interface, sends HTTP requests to multiple endpoints
2. **FastAPI**: Web server with multiple endpoints (/api/query, /api/courses, /api/logs)
3. **RAG System**: Orchestrates the entire query process and provider selection
4. **LLM Provider Abstraction**: Supports multiple providers (Anthropic Claude, Google Gemini)
5. **Tool Manager**: Routes tool calls to appropriate handlers with enhanced source tracking
6. **Course Tools**: CourseSearchTool for content search, CourseOutlineTool for structure
7. **Vector Store**: Performs semantic search and provides course metadata
8. **Session Logger**: Tracks token usage, system events, and debugging information

## Flow Characteristics:

- **Multi-Provider**: Supports both Anthropic Claude and Google Gemini LLMs
- **Enhanced Tool System**: Two specialized tools for different query types
- **Bidirectional**: Results flow back up the chain with rich metadata
- **Tool-based**: LLM autonomously decides when to search, get outlines, or use general knowledge
- **Session-aware**: Maintains conversation context with comprehensive logging
- **Source-enhanced**: UI shows clickable source links with lesson-level granularity
- **Error-resilient**: Graceful handling at each level with comprehensive logging
- **Token-tracked**: Comprehensive token usage monitoring across providers