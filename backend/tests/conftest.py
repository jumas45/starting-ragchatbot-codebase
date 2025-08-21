"""Test configuration and fixtures"""

import pytest
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import Config
from vector_store import VectorStore, SearchResults
from search_tools import CourseSearchTool, CourseOutlineTool
from ai_generator import AIGenerator
from rag_system import RAGSystem


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_config(temp_dir):
    """Create a mock config for testing"""
    config = Mock(spec=Config)
    config.CHROMA_PATH = os.path.join(temp_dir, "test_chroma")
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.MAX_RESULTS = 5
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_HISTORY = 10
    config.LLM_PROVIDER = "anthropic"
    config.ANTHROPIC_API_KEY = "test-key"
    config.ANTHROPIC_MODEL = "claude-3-sonnet-20240229"
    return config


@pytest.fixture
def mock_search_results():
    """Create mock search results for testing"""
    def create_results(documents=None, metadata=None, error=None):
        documents = documents or []
        metadata = metadata or []
        
        results = Mock(spec=SearchResults)
        results.documents = documents
        results.metadata = metadata
        results.distances = [0.5] * len(documents)
        results.error = error
        results.is_empty.return_value = len(documents) == 0
        return results
    
    return create_results


@pytest.fixture
def mock_vector_store(mock_search_results):
    """Create a mock vector store for testing"""
    store = Mock(spec=VectorStore)
    
    # Default search behavior - return some test results
    default_results = mock_search_results(
        documents=["This is test content about MCP"],
        metadata=[{
            'course_title': 'MCP: Build Rich-Context AI Apps with Anthropic',
            'lesson_number': 1,
            'lesson_title': 'Introduction to MCP'
        }]
    )
    store.search.return_value = default_results
    
    # Mock get_lesson_link method
    store.get_lesson_link.return_value = "https://example.com/lesson/1"
    
    # Mock get_all_courses_metadata
    store.get_all_courses_metadata.return_value = [
        {
            'title': 'MCP: Build Rich-Context AI Apps with Anthropic',
            'course_link': 'https://example.com/mcp',
            'instructor': 'Test Instructor',
            'lessons': [
                {'lesson_number': 0, 'lesson_title': 'Introduction'},
                {'lesson_number': 1, 'lesson_title': 'Getting Started'},
                {'lesson_number': 2, 'lesson_title': 'Advanced Topics'}
            ]
        }
    ]
    
    return store


@pytest.fixture
def course_search_tool(mock_vector_store):
    """Create a CourseSearchTool instance for testing"""
    return CourseSearchTool(mock_vector_store)


@pytest.fixture
def course_outline_tool(mock_vector_store):
    """Create a CourseOutlineTool instance for testing"""
    return CourseOutlineTool(mock_vector_store)


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client for testing"""
    client = Mock()
    
    # Mock response structure
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = "Test AI response"
    mock_response.stop_reason = "end_turn"
    mock_response.usage = Mock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    
    client.messages.create.return_value = mock_response
    
    return client


@pytest.fixture
def mock_ai_generator(mock_anthropic_client):
    """Create a mock AI generator for testing"""
    # Mock the anthropic import and client
    import anthropic
    with pytest.MonkeyPatch().context() as m:
        m.setattr(anthropic, 'Anthropic', lambda api_key: mock_anthropic_client)
        generator = AIGenerator("anthropic", "test-key", "claude-3-sonnet-20240229")
    
    return generator