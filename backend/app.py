from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
from datetime import datetime

app = FastAPI(title="RAG System API", version="1.0.0")

# Mount static files for CSS and JS
import os
parent_dir = os.path.dirname(os.path.dirname(__file__))
app.mount("/static", StaticFiles(directory=parent_dir), name="static")

class QueryRequest(BaseModel):
    query: str
    context: Optional[str] = None
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[str] = []
    confidence: float

class Course(BaseModel):
    id: int
    title: str
    description: str
    instructor: str
    lesson_count: Optional[int] = None

class LogEntry(BaseModel):
    timestamp: str
    message: str
    tokens: Optional[int] = None

class CourseAnalyticsResponse(BaseModel):
    courses: List[Course]

class LogsResponse(BaseModel):
    logs: List[LogEntry]

class SampleQuestion(BaseModel):
    question: str
    category: str

# Sample data for testing
SAMPLE_COURSES = [
    Course(id=1, title="Introduction to Python", description="Learn Python basics", instructor="John Doe", lesson_count=25),
    Course(id=2, title="Advanced Machine Learning", description="Deep dive into ML", instructor="Jane Smith", lesson_count=18),
    Course(id=3, title="Web Development", description="Full stack development", instructor="Bob Johnson", lesson_count=32),
    Course(id=4, title="Data Science Fundamentals", description="Statistics and data analysis", instructor="Dr. Alice Brown", lesson_count=22),
]

# Sample logs for testing
SAMPLE_LOGS = [
    LogEntry(timestamp="2025-08-21 10:30:00", message="Session started", tokens=0),
    LogEntry(timestamp="2025-08-21 10:35:00", message="Query: What is Python?", tokens=45),
    LogEntry(timestamp="2025-08-21 10:36:00", message="Query: How do I install packages?", tokens=38),
    LogEntry(timestamp="2025-08-21 10:40:00", message="Query: Explain machine learning basics", tokens=67),
]

# Sample questions
SAMPLE_QUESTIONS = [
    SampleQuestion(question="What is Python and why is it popular?", category="Programming"),
    SampleQuestion(question="How do I install Python packages?", category="Setup"),
    SampleQuestion(question="What are the basics of machine learning?", category="AI/ML"),
    SampleQuestion(question="How do I create a REST API with FastAPI?", category="Web Development"),
    SampleQuestion(question="What is the difference between supervised and unsupervised learning?", category="AI/ML"),
    SampleQuestion(question="How do I handle errors in Python?", category="Programming"),
]

@app.get("/")
async def root():
    """Serve the main HTML page"""
    import os
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html")
    return FileResponse(html_path)

@app.get("/styles.css")
async def get_styles():
    """Serve CSS file"""
    import os
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "styles.css")
    return FileResponse(css_path, media_type="text/css")

@app.get("/script.js")
async def get_script():
    """Serve JS file"""
    import os
    js_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "script.js")
    return FileResponse(js_path, media_type="application/javascript")

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

@app.get("/api/courses", response_model=CourseAnalyticsResponse)
async def get_courses():
    """Get all available courses with analytics"""
    return CourseAnalyticsResponse(courses=SAMPLE_COURSES)

@app.get("/api/courses/{course_id}", response_model=Course)
async def get_course(course_id: int):
    """Get a specific course by ID"""
    course = next((c for c in SAMPLE_COURSES if c.id == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@app.get("/api/logs", response_model=LogsResponse)
async def get_logs():
    """Get session logs"""
    return LogsResponse(logs=SAMPLE_LOGS)

@app.post("/api/logs/clear")
async def clear_logs():
    """Clear session logs"""
    global SAMPLE_LOGS
    SAMPLE_LOGS.clear()
    return {"message": "Logs cleared successfully"}

@app.get("/api/sample-questions", response_model=List[SampleQuestion])
async def get_sample_questions():
    """Get sample questions for the chatbot"""
    return SAMPLE_QUESTIONS

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)