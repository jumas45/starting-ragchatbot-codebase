import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from unittest.mock import patch
from backend.app import app, SAMPLE_COURSES

@pytest.fixture
def client():
    """Create a test client for the FastAPI application"""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def mock_static_directory():
    """Create a temporary static directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('backend.app.static_dir', temp_dir):
            # Create the temp directory to simulate static files existing
            os.makedirs(temp_dir, exist_ok=True)
            yield temp_dir

@pytest.fixture
def sample_query_request():
    """Sample query request data for testing"""
    return {
        "query": "What is machine learning?",
        "context": "Educational content about ML"
    }

@pytest.fixture
def empty_query_request():
    """Empty query request for testing validation"""
    return {
        "query": "",
        "context": None
    }

@pytest.fixture
def sample_courses():
    """Sample courses data for testing"""
    return SAMPLE_COURSES

@pytest.fixture
def valid_course_id():
    """Valid course ID for testing"""
    return 1

@pytest.fixture
def invalid_course_id():
    """Invalid course ID for testing"""
    return 999

@pytest.fixture
def mock_rag_response():
    """Mock RAG system response"""
    return {
        "answer": "Machine learning is a subset of artificial intelligence...",
        "sources": ["ml_basics.pdf", "ai_overview.pdf"],
        "confidence": 0.92
    }

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment - runs before each test"""
    # Ensure we're in test mode
    os.environ["TESTING"] = "1"
    yield
    # Cleanup after test
    if "TESTING" in os.environ:
        del os.environ["TESTING"]

@pytest.fixture
def api_headers():
    """Standard API headers for testing"""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }