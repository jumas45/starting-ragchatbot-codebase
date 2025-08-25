"""Integration tests for end-to-end RAG system workflows"""

import pytest
import tempfile
import shutil
import os
from unittest.mock import Mock, patch, MagicMock
from rag_system import RAGSystem
from config import Config
from models import Course, Lesson, CourseChunk
from vector_store import VectorStore
from document_processor import DocumentProcessor
from session_manager import SessionManager
from search_tools import ToolManager, CourseSearchTool, CourseOutlineTool
from llm_providers import AnthropicProvider, GeminiProvider


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_config(temp_dir):
    """Create test configuration"""
    config = Config()
    config.CHROMA_PATH = os.path.join(temp_dir, "test_chroma")
    config.CHUNK_SIZE = 100
    config.CHUNK_OVERLAP = 20
    config.MAX_RESULTS = 3
    config.MAX_HISTORY = 2
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    return config


@pytest.fixture
def sample_course_file(temp_dir):
    """Create sample course file for testing"""
    course_content = """Course Title: Introduction to Python
Course Link: https://example.com/python
Course Instructor: Jane Smith

Lesson 1: Getting Started
Lesson Link: https://example.com/lesson1
Python is a powerful programming language. It's easy to learn and widely used.
Variables in Python are used to store data. You can create variables like: name = "Alice"

Lesson 2: Data Types
Lesson Link: https://example.com/lesson2
Python has several built-in data types. The most common are strings, integers, and lists.
Strings are text data enclosed in quotes. Integers are whole numbers. Lists store multiple items.

Lesson 3: Control Flow
Python uses if statements for conditional logic. For loops iterate over sequences.
While loops repeat code while a condition is true. These control structures are fundamental.
"""
    
    file_path = os.path.join(temp_dir, "python_course.txt")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(course_content)
    
    return file_path


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider"""
    provider = Mock()
    provider.generate_response.return_value = "This is a test AI response based on the course content."
    return provider


class TestDocumentProcessingIntegration:
    """Test document processing pipeline integration"""
    
    def test_document_to_chunks_pipeline(self, sample_course_file, test_config):
        """Test complete pipeline from document to chunks"""
        processor = DocumentProcessor(test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP)
        
        # Process document
        course, chunks = processor.process_course_document(sample_course_file)
        
        # Verify course metadata
        assert course.title == "Introduction to Python"
        assert course.course_link == "https://example.com/python"
        assert course.instructor == "Jane Smith"
        assert len(course.lessons) == 3
        
        # Verify lessons
        assert course.lessons[0].lesson_number == 1
        assert course.lessons[0].title == "Getting Started"
        assert course.lessons[0].lesson_link == "https://example.com/lesson1"
        
        # Verify chunks
        assert len(chunks) > 0
        assert all(isinstance(chunk, CourseChunk) for chunk in chunks)
        assert all(chunk.course_title == "Introduction to Python" for chunk in chunks)
        
        # Verify lesson numbers are assigned
        lesson_numbers = {chunk.lesson_number for chunk in chunks if chunk.lesson_number is not None}
        assert lesson_numbers == {1, 2, 3}
    
    def test_vector_store_integration(self, sample_course_file, test_config):
        """Test vector store integration with processed documents"""
        processor = DocumentProcessor(test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP)
        vector_store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS
        )
        
        # Process and store document
        course, chunks = processor.process_course_document(sample_course_file)
        vector_store.add_course_metadata(course)
        vector_store.add_course_content(chunks)
        
        # Test search functionality
        results = vector_store.search("Python variables")
        assert not results.is_empty()
        assert any("variable" in doc.lower() for doc in results.documents)
        
        # Test course resolution
        results = vector_store.search("data types", course_name="Python")
        assert not results.is_empty()
        assert any("data type" in doc.lower() for doc in results.documents)
        
        # Test lesson filtering
        results = vector_store.search("control flow", lesson_number=3)
        assert not results.is_empty()
        assert all(meta.get("lesson_number") == 3 for meta in results.metadata)


class TestSearchToolsIntegration:
    """Test search tools integration with vector store"""
    
    def test_course_search_tool_integration(self, sample_course_file, test_config):
        """Test CourseSearchTool with real vector store"""
        # Setup components
        processor = DocumentProcessor(test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP)
        vector_store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS
        )
        
        # Process and store document
        course, chunks = processor.process_course_document(sample_course_file)
        vector_store.add_course_metadata(course)
        vector_store.add_course_content(chunks)
        
        # Create and test search tool
        search_tool = CourseSearchTool(vector_store)
        
        # Test search
        result = search_tool.execute("Python variables")
        assert "Introduction to Python" in result
        assert "variable" in result.lower()
        
        # Test with filters
        result = search_tool.execute("data types", course_name="Python")
        assert "data type" in result.lower()
        
        # Verify sources are tracked
        assert len(search_tool.last_sources) > 0
        assert search_tool.last_sources[0]["text"].startswith("Introduction to Python")
    
    def test_course_outline_tool_integration(self, sample_course_file, test_config):
        """Test CourseOutlineTool with real vector store"""
        # Setup components
        processor = DocumentProcessor(test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP)
        vector_store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS
        )
        
        # Process and store document
        course, chunks = processor.process_course_document(sample_course_file)
        vector_store.add_course_metadata(course)
        vector_store.add_course_content(chunks)
        
        # Create and test outline tool
        outline_tool = CourseOutlineTool(vector_store)
        
        # Test outline retrieval
        result = outline_tool.execute("Python")
        
        assert "**Course Title:** Introduction to Python" in result
        assert "**Instructor:** Jane Smith" in result
        assert "**Lessons:**" in result
        assert "Lesson 1: Getting Started" in result
        assert "Lesson 2: Data Types" in result
        assert "Lesson 3: Control Flow" in result
    
    def test_tool_manager_integration(self, sample_course_file, test_config):
        """Test ToolManager with multiple tools"""
        # Setup components
        processor = DocumentProcessor(test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP)
        vector_store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS
        )
        
        # Process and store document
        course, chunks = processor.process_course_document(sample_course_file)
        vector_store.add_course_metadata(course)
        vector_store.add_course_content(chunks)
        
        # Setup tool manager
        tool_manager = ToolManager()
        tool_manager.register_tool(CourseSearchTool(vector_store))
        tool_manager.register_tool(CourseOutlineTool(vector_store))
        
        # Test search through tool manager
        search_result = tool_manager.execute_tool("search_course_content", query="variables")
        assert "variable" in search_result.lower()
        
        # Test outline through tool manager
        outline_result = tool_manager.execute_tool("get_course_outline", course_title="Python")
        assert "Getting Started" in outline_result
        
        # Test tool definitions
        definitions = tool_manager.get_tool_definitions()
        assert len(definitions) == 2
        tool_names = {defn["name"] for defn in definitions}
        assert tool_names == {"search_course_content", "get_course_outline"}


class TestSessionManagementIntegration:
    """Test session management integration"""
    
    def test_session_manager_with_conversation_flow(self):
        """Test session manager with realistic conversation flow"""
        session_manager = SessionManager(max_history=3)
        
        # Create session and simulate conversation
        session_id = session_manager.create_session()
        
        session_manager.add_exchange(
            session_id,
            "What are Python variables?",
            "Variables in Python are used to store data. You can create them like: name = 'Alice'"
        )
        
        session_manager.add_exchange(
            session_id,
            "How do I create a list?",
            "You can create a list in Python using square brackets: items = [1, 2, 3]"
        )
        
        # Get conversation history
        history = session_manager.get_conversation_history(session_id)
        
        assert "Python variables" in history
        assert "create a list" in history
        assert "Variables in Python" in history
        assert "square brackets" in history
        
        # Test history formatting
        lines = history.split('\n')
        assert len(lines) == 4  # 2 exchanges = 4 messages
        assert lines[0].startswith("User:")
        assert lines[1].startswith("Assistant:")
    
    def test_session_logger_integration(self):
        """Test session logger with realistic logging scenarios"""
        from session_logger import SessionLogger
        
        logger = SessionLogger(max_logs=50)
        
        # Simulate RAG system logging
        logger.info("Starting document processing", document="python_course.txt")
        logger.info("Course processed successfully", course_title="Introduction to Python", lessons=3)
        logger.token("LLM API call", provider="anthropic", input_tokens=150, output_tokens=75)
        logger.info("Search executed", query="Python variables", results_found=2)
        logger.token("LLM API call", provider="anthropic", input_tokens=200, output_tokens=100)
        
        # Retrieve and verify logs
        logs = logger.get_logs()
        assert len(logs) == 5
        
        # Verify log structure and content
        assert logs[0]["level"] == "info"
        assert logs[0]["document"] == "python_course.txt"
        assert logs[2]["level"] == "token"
        assert logs[2]["provider"] == "anthropic"
        assert logs[3]["query"] == "Python variables"
        
        # Test log ordering (chronological)
        timestamps = [log["timestamp"] for log in logs]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1]


class TestLLMIntegration:
    """Test LLM provider integration (with mocking for actual API calls)"""
    
    @patch('llm_providers.anthropic.Anthropic')
    def test_anthropic_provider_with_tools(self, mock_anthropic, sample_course_file, test_config):
        """Test Anthropic provider integration with tools"""
        # Setup mock responses
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Based on the course content, Python variables store data.", type="text")]
        mock_response.stop_reason = "end_turn"
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        # Setup components
        processor = DocumentProcessor(test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP)
        vector_store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS
        )
        
        course, chunks = processor.process_course_document(sample_course_file)
        vector_store.add_course_metadata(course)
        vector_store.add_course_content(chunks)
        
        # Setup tools
        tool_manager = ToolManager()
        tool_manager.register_tool(CourseSearchTool(vector_store))
        
        # Create provider and test
        provider = AnthropicProvider("test_key", "test_model")
        response = provider.generate_response(
            "What are Python variables?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )
        
        assert "Python variables store data" in response
        mock_client.messages.create.assert_called()
    
    @patch('llm_providers.genai.configure')
    @patch('llm_providers.genai.GenerativeModel')
    def test_gemini_provider_with_tools(self, mock_model_class, mock_configure, sample_course_file, test_config):
        """Test Gemini provider integration with tools"""
        # Setup mock responses
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Python variables are containers that store data values."
        mock_response.usage_metadata = Mock(prompt_token_count=100, candidates_token_count=50)
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        # Setup components (minimal for this test)
        vector_store = Mock()
        tool_manager = ToolManager()
        tool_manager.register_tool(CourseSearchTool(vector_store))
        
        # Create provider and test
        provider = GeminiProvider("test_key", "test_model")
        response = provider.generate_response(
            "What are Python variables?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )
        
        # Should fall back to simple generation since tools are mocked
        assert "Python variables" in response


class TestFullRAGSystemIntegration:
    """Test complete RAG system integration"""
    
    @patch('rag_system.create_llm_provider')
    def test_rag_system_initialization(self, mock_create_provider, sample_course_file, test_config):
        """Test RAG system initialization with all components"""
        # Setup mock provider
        mock_provider = Mock()
        mock_provider.generate_response.return_value = "Test response"
        mock_create_provider.return_value = mock_provider
        
        # Create documents directory and copy sample file
        docs_dir = os.path.join(os.path.dirname(sample_course_file), "docs")
        os.makedirs(docs_dir, exist_ok=True)
        dest_file = os.path.join(docs_dir, "python_course.txt")
        shutil.copy2(sample_course_file, dest_file)
        
        # Initialize RAG system
        with patch('rag_system.config', test_config):
            rag_system = RAGSystem()
            rag_system._initialize_components()
            rag_system._load_documents(docs_dir)
        
        # Verify components are initialized
        assert rag_system.vector_store is not None
        assert rag_system.document_processor is not None
        assert rag_system.session_manager is not None
        assert rag_system.llm_provider is not None
        assert rag_system.tool_manager is not None
        
        # Verify documents were loaded
        course_count = rag_system.vector_store.get_course_count()
        assert course_count > 0
        
        # Test query processing
        session_id = rag_system.create_session()
        response = rag_system.process_query(session_id, "What are Python variables?")
        
        assert response is not None
        mock_provider.generate_response.assert_called()
    
    def test_error_handling_integration(self, temp_dir, test_config):
        """Test error handling across integrated components"""
        # Test with invalid document
        invalid_file = os.path.join(temp_dir, "invalid.txt")
        with open(invalid_file, 'w', encoding='utf-8') as f:
            f.write("Invalid course format")
        
        processor = DocumentProcessor(test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP)
        
        # Should handle gracefully
        course, chunks = processor.process_course_document(invalid_file)
        assert course is not None
        # May have empty chunks or use filename as title
        
        # Test vector store with invalid path
        with pytest.raises(Exception):
            VectorStore("/invalid/path", test_config.EMBEDDING_MODEL)
    
    def test_performance_with_multiple_documents(self, temp_dir, test_config):
        """Test system performance with multiple documents"""
        # Create multiple sample documents
        docs = []
        for i in range(3):
            content = f"""Course Title: Test Course {i+1}
Course Instructor: Instructor {i+1}

Lesson 1: Introduction to Topic {i+1}
This is lesson content for course {i+1}. It contains information about topic {i+1}.

Lesson 2: Advanced Topic {i+1}
Advanced content for course {i+1} covering complex concepts of topic {i+1}.
"""
            file_path = os.path.join(temp_dir, f"course_{i+1}.txt")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            docs.append(file_path)
        
        # Process all documents
        processor = DocumentProcessor(test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP)
        vector_store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS
        )
        
        total_chunks = 0
        for doc_path in docs:
            course, chunks = processor.process_course_document(doc_path)
            vector_store.add_course_metadata(course)
            vector_store.add_course_content(chunks)
            total_chunks += len(chunks)
        
        # Verify all courses were stored
        assert vector_store.get_course_count() == 3
        
        # Test search across all documents
        search_tool = CourseSearchTool(vector_store)
        result = search_tool.execute("advanced concepts")
        
        # Should find content from multiple courses
        assert "advanced" in result.lower()
        
        # Test course-specific search
        result = search_tool.execute("topic", course_name="Test Course 2")
        assert "Course 2" in result or "topic 2" in result.lower()


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    def test_student_learning_session(self, sample_course_file, test_config, mock_llm_provider):
        """Simulate a student learning session with multiple queries"""
        # Setup complete system
        processor = DocumentProcessor(test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP)
        vector_store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS
        )
        session_manager = SessionManager(max_history=5)
        
        # Load course content
        course, chunks = processor.process_course_document(sample_course_file)
        vector_store.add_course_metadata(course)
        vector_store.add_course_content(chunks)
        
        # Setup tools
        tool_manager = ToolManager()
        tool_manager.register_tool(CourseSearchTool(vector_store))
        tool_manager.register_tool(CourseOutlineTool(vector_store))
        
        # Simulate learning session
        session_id = session_manager.create_session()
        
        # Student asks for course outline
        outline_result = tool_manager.execute_tool("get_course_outline", course_title="Python")
        session_manager.add_message(session_id, "user", "Can you show me the Python course outline?")
        session_manager.add_message(session_id, "assistant", outline_result)
        
        # Student asks about specific topic
        search_result = tool_manager.execute_tool("search_course_content", query="variables")
        session_manager.add_message(session_id, "user", "What are variables in Python?")
        session_manager.add_message(session_id, "assistant", search_result)
        
        # Student asks follow-up question
        search_result2 = tool_manager.execute_tool("search_course_content", query="data types", lesson_number=2)
        session_manager.add_message(session_id, "user", "Tell me about data types in lesson 2")
        session_manager.add_message(session_id, "assistant", search_result2)
        
        # Verify session history
        history = session_manager.get_conversation_history(session_id)
        assert "course outline" in history.lower()
        assert "variables" in history.lower()
        assert "data types" in history.lower()
        
        # Verify sources were tracked
        sources = tool_manager.get_last_sources()
        assert len(sources) > 0
        assert all("Introduction to Python" in source["text"] for source in sources)
    
    def test_instructor_content_review(self, sample_course_file, test_config):
        """Simulate instructor reviewing course content"""
        # Setup system
        processor = DocumentProcessor(test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP)
        vector_store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS
        )
        
        course, chunks = processor.process_course_document(sample_course_file)
        vector_store.add_course_metadata(course)
        vector_store.add_course_content(chunks)
        
        # Instructor checks course structure
        outline_tool = CourseOutlineTool(vector_store)
        outline = outline_tool.execute("Python")
        
        assert "3" in outline  # Should show 3 lessons
        assert "Jane Smith" in outline  # Should show instructor
        
        # Instructor searches for specific content coverage
        search_tool = CourseSearchTool(vector_store)
        
        # Check if control flow is covered
        control_flow_content = search_tool.execute("control flow")
        assert "control" in control_flow_content.lower()
        
        # Check lesson-specific content
        lesson1_content = search_tool.execute("", lesson_number=1)
        assert "getting started" in lesson1_content.lower() or "python is" in lesson1_content.lower()
    
    def test_concurrent_user_sessions(self, sample_course_file, test_config):
        """Test multiple concurrent user sessions"""
        # Setup shared components
        processor = DocumentProcessor(test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP)
        vector_store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS
        )
        
        course, chunks = processor.process_course_document(sample_course_file)
        vector_store.add_course_metadata(course)
        vector_store.add_course_content(chunks)
        
        # Create multiple session managers (simulating different users)
        session_managers = [SessionManager(max_history=3) for _ in range(3)]
        session_ids = [sm.create_session() for sm in session_managers]
        
        # Each user asks different questions
        search_tool = CourseSearchTool(vector_store)
        
        # User 1: Asks about variables
        result1 = search_tool.execute("variables")
        session_managers[0].add_exchange(session_ids[0], "What are variables?", result1)
        
        # User 2: Asks about data types
        result2 = search_tool.execute("data types")
        session_managers[1].add_exchange(session_ids[1], "Explain data types", result2)
        
        # User 3: Asks for course outline
        outline_tool = CourseOutlineTool(vector_store)
        result3 = outline_tool.execute("Python")
        session_managers[2].add_exchange(session_ids[2], "Show course structure", result3)
        
        # Verify session isolation
        history1 = session_managers[0].get_conversation_history(session_ids[0])
        history2 = session_managers[1].get_conversation_history(session_ids[1])
        history3 = session_managers[2].get_conversation_history(session_ids[2])
        
        assert "variables" in history1.lower()
        assert "variables" not in history2.lower()
        assert "variables" not in history3.lower()
        
        assert "data types" in history2.lower()
        assert "data types" not in history1.lower()
        
        assert "course structure" in history3.lower()
        assert "course structure" not in history1.lower()