import warnings
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os

from config import config
from rag_system import RAGSystem
from session_logger import session_logger

# Initialize FastAPI app
app = FastAPI(title="Course Materials RAG System", root_path="")

# Add trusted host middleware for proxy
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# Enable CORS with proper settings for proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize RAG system
rag_system = RAGSystem(config)

# Pydantic models for request/response
class QueryRequest(BaseModel):
    """Request model for course queries"""
    query: str
    session_id: Optional[str] = None

class Source(BaseModel):
    """Model for source information with optional links"""
    text: str
    link: Optional[str] = None

class QueryResponse(BaseModel):
    """Response model for course queries"""
    answer: str
    sources: List[Source]
    session_id: str

class Course(BaseModel):
    """Model for individual course information"""
    title: str
    lesson_count: Optional[int] = None
    instructor: Optional[str] = None

class CourseAnalyticsResponse(BaseModel):
    """Response model for course analytics"""
    courses: List[Course]

class LogEntry(BaseModel):
    """Model for log entries"""
    timestamp: str
    level: str
    message: str
    tokens: Optional[int] = None

class LogsResponse(BaseModel):
    """Response model for session logs"""
    logs: List[LogEntry]

# Frontend Routes

@app.get("/")
async def root():
    """Serve the main HTML page"""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html")
    return FileResponse(html_path)

@app.get("/styles.css")
async def get_styles():
    """Serve CSS file"""
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "styles.css")
    return FileResponse(css_path, media_type="text/css")

@app.get("/script.js")
async def get_script():
    """Serve JS file"""
    js_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "script.js")
    return FileResponse(js_path, media_type="application/javascript")

# API Endpoints

@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Process a query and return response with sources"""
    try:
        # Create session if not provided
        session_id = request.session_id
        if not session_id:
            session_id = rag_system.session_manager.create_session()
        
        # Log the incoming query
        session_logger.info(f"Processing query: {request.query[:100]}{'...' if len(request.query) > 100 else ''}")
        
        # Process query using RAG system
        answer, sources = rag_system.query(request.query, session_id)
        
        # Convert source objects to Source models
        source_models = []
        for source in sources:
            if isinstance(source, dict):
                source_models.append(Source(text=source["text"], link=source["link"]))
            else:
                # Handle backward compatibility for string sources
                source_models.append(Source(text=str(source), link=None))
        
        return QueryResponse(
            answer=answer,
            sources=source_models,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/courses", response_model=CourseAnalyticsResponse)
async def get_course_stats():
    """Get course analytics and statistics"""
    try:
        analytics = rag_system.get_course_analytics()
        courses = []
        if "course_titles" in analytics:
            for title in analytics["course_titles"]:
                # Create course objects from the titles
                courses.append(Course(
                    title=title,
                    lesson_count=None,  # Could be extracted from document metadata
                    instructor=None     # Could be extracted from document metadata
                ))
        
        return CourseAnalyticsResponse(courses=courses)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs", response_model=LogsResponse)
async def get_logs():
    """Get session logs"""
    try:
        logs = session_logger.get_logs()
        log_entries = [
            LogEntry(
                timestamp=log["timestamp"], 
                level=log["level"], 
                message=log["message"],
                tokens=log.get("tokens")
            ) for log in logs
        ]
        return LogsResponse(logs=log_entries)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/logs/clear")
async def clear_logs():
    """Clear session logs"""
    try:
        session_logger.clear_logs()
        return {"message": "Logs cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SampleQuestion(BaseModel):
    question: str
    category: str

@app.get("/api/sample-questions", response_model=List[SampleQuestion])
async def get_sample_questions():
    """Get sample questions for the chatbot"""
    sample_questions = [
        SampleQuestion(question="How do I use Claude's computer use capability?", category="Computer Use"),
        SampleQuestion(question="What is the Model Context Protocol (MCP) and how does it work?", category="MCP"),
        SampleQuestion(question="How can I implement advanced retrieval techniques with Chroma?", category="RAG & Retrieval"),
        SampleQuestion(question="What is prompt compression and how can it reduce costs?", category="Optimization"),
        SampleQuestion(question="How do I set up multi-modal requests with Anthropic's API?", category="API Usage"),
        SampleQuestion(question="What are the benefits of query expansion in vector search?", category="RAG & Retrieval"),
        SampleQuestion(question="How do I build an MCP server and client?", category="MCP"),
        SampleQuestion(question="What filtering techniques can improve retrieval results?", category="Optimization"),
    ]
    return sample_questions

@app.on_event("startup")
async def startup_event():
    """Load initial documents on startup"""
    session_logger.info("RAG System starting up...")
    docs_path = "./docs"
    if os.path.exists(docs_path):
        print("Loading initial documents...")
        session_logger.info("Loading initial documents...")
        try:
            courses, chunks = rag_system.add_course_folder(docs_path, clear_existing=False)
            msg = f"Loaded {courses} courses with {chunks} chunks"
            print(msg)
            session_logger.info(msg)
        except Exception as e:
            error_msg = f"Error loading documents: {e}"
            print(error_msg)
            session_logger.error(error_msg)

# Custom static file handler with no-cache headers for development
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path


class DevStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            # Add no-cache headers for development
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response
    
    
# Frontend files are served via individual routes above

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)