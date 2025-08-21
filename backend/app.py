from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(title="RAG System API", version="1.0.0")

# Mount static files only if the directory exists
static_dir = "static"
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

class QueryRequest(BaseModel):
    query: str
    context: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[str] = []
    confidence: float

class Course(BaseModel):
    id: int
    title: str
    description: str
    instructor: str

# Sample data for testing
SAMPLE_COURSES = [
    Course(id=1, title="Introduction to Python", description="Learn Python basics", instructor="John Doe"),
    Course(id=2, title="Advanced Machine Learning", description="Deep dive into ML", instructor="Jane Smith"),
    Course(id=3, title="Web Development", description="Full stack development", instructor="Bob Johnson"),
]

@app.get("/")
async def root():
    """Root endpoint returning API information"""
    return {
        "message": "RAG System API",
        "version": "1.0.0",
        "endpoints": ["/api/query", "/api/courses", "/"]
    }

@app.post("/api/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """Process a RAG query and return response"""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Mock RAG processing
    answer = f"Based on your query '{request.query}', here is the relevant information."
    sources = ["document1.pdf", "document2.pdf"]
    confidence = 0.85
    
    return QueryResponse(
        answer=answer,
        sources=sources,
        confidence=confidence
    )

@app.get("/api/courses", response_model=List[Course])
async def get_courses():
    """Get all available courses"""
    return SAMPLE_COURSES

@app.get("/api/courses/{course_id}", response_model=Course)
async def get_course(course_id: int):
    """Get a specific course by ID"""
    course = next((c for c in SAMPLE_COURSES if c.id == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)