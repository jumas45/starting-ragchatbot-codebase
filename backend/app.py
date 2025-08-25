import warnings
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
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

class CourseInfo(BaseModel):
    """Individual course information"""
    title: str
    instructor: str
    lesson_count: int
    link: Optional[str] = None

class CourseStats(BaseModel):
    """Response model for course statistics"""
    total_courses: int
    course_titles: List[str]
    courses: List[CourseInfo]

class LogEntry(BaseModel):
    """Model for log entries"""
    timestamp: str
    level: str
    message: str

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

@app.get("/api/courses", response_model=CourseStats)
async def get_course_stats():
    """Get course analytics and statistics"""
    try:
        analytics = rag_system.get_course_analytics()
        course_infos = [CourseInfo(**course) for course in analytics["courses"]]
        return CourseStats(
            total_courses=analytics["total_courses"],
            course_titles=analytics["course_titles"],
            courses=course_infos
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs", response_model=List[LogEntry])
async def get_logs():
    """Get session logs"""
    try:
        logs = session_logger.get_logs()
        return [LogEntry(timestamp=log["timestamp"], level=log["level"], message=log["message"]) for log in logs]
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

@app.get("/api/sample-questions")
async def get_sample_questions():
    """Get sample questions for the UI"""
    sample_questions = [
        {
            "question": "What are the main topics covered in the courses?",
            "category": "General"
        },
        {
            "question": "How do I implement retrieval-augmented generation?",
            "category": "Technical"
        },
        {
            "question": "What tools are mentioned for building AI applications?",
            "category": "Tools"
        },
        {
            "question": "Who are the instructors for these courses?",
            "category": "General"
        },
        {
            "question": "How can I optimize my prompts for better results?",
            "category": "Technical"
        }
    ]
    return sample_questions

@app.on_event("startup")
async def startup_event():
    """Load initial documents on startup"""
    session_logger.info("RAG System starting up...")
    docs_path = "../docs"
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
    
    
# Serve static files for the frontend
import pathlib
frontend_dir = pathlib.Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="static")
else:
    # For testing environments where frontend may not be available
    from fastapi.responses import JSONResponse
    @app.get("/")
    async def root_fallback():
        return JSONResponse({"message": "Frontend not available in test environment"})