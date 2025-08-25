"""Tests for RAG system content query handling"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import tempfile
import os

from rag_system import RAGSystem
from search_tools import ToolManager


class TestRAGSystemContentQueries:
    """Test RAG system handling of content-related queries"""
    
    @pytest.fixture
    def mock_rag_config(self):
        """Create a mock config for RAG system testing"""
        config = Mock()
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.CHROMA_PATH = tempfile.mkdtemp()
        config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        config.MAX_RESULTS = 5
        config.MAX_HISTORY = 10
        config.LLM_PROVIDER = "anthropic"
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "claude-3-sonnet-20240229"
        return config
    
    @pytest.fixture
    def mock_rag_system(self, mock_rag_config):
        """Create a RAG system with mocked components"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as mock_vs_class, \
             patch('rag_system.AIGenerator') as mock_ai_class, \
             patch('rag_system.SessionManager') as mock_sm_class:
            
            # Setup mock vector store
            mock_vector_store = Mock()
            mock_vector_store.search.return_value = Mock()
            mock_vector_store.search.return_value.documents = ["Test content"]
            mock_vector_store.search.return_value.metadata = [{"course_title": "Test Course"}]
            mock_vector_store.search.return_value.error = None
            mock_vector_store.search.return_value.is_empty.return_value = False
            mock_vector_store.get_lesson_link.return_value = "https://test.com/lesson"
            mock_vs_class.return_value = mock_vector_store
            
            # Setup mock AI generator
            mock_ai_generator = Mock()
            mock_ai_generator.generate_response.return_value = "AI generated response about the topic"
            mock_ai_class.return_value = mock_ai_generator
            
            # Setup mock session manager
            mock_session_manager = Mock()
            mock_session_manager.get_history.return_value = ""
            mock_session_manager.add_exchange.return_value = None
            mock_sm_class.return_value = mock_session_manager
            
            rag_system = RAGSystem(mock_rag_config)
            
            # Store mocks for access in tests
            rag_system._mock_vector_store = mock_vector_store
            rag_system._mock_ai_generator = mock_ai_generator
            rag_system._mock_session_manager = mock_session_manager
            
            return rag_system
    
    def test_query_processing_basic(self, mock_rag_system):
        """Test basic query processing flow"""
        # Execute
        result = mock_rag_system.query("What is MCP?", "test-session")
        
        # Verify
        assert "answer" in result
        assert "sources" in result
        assert "session_id" in result
        assert result["session_id"] == "test-session"
        assert result["answer"] == "AI generated response about the topic"
    
    def test_query_with_tools_integration(self, mock_rag_system):
        """Test that query processing integrates with tools correctly"""
        # Execute
        result = mock_rag_system.query("Explain MCP servers", "test-session")
        
        # Verify AI generator was called with tools
        mock_rag_system._mock_ai_generator.generate_response.assert_called_once()
        call_args = mock_rag_system._mock_ai_generator.generate_response.call_args
        
        # Should be called with tools and tool_manager
        assert "tools" in call_args.kwargs
        assert "tool_manager" in call_args.kwargs
        assert call_args.kwargs["tool_manager"] is not None
        
        # Tools should include both search and outline tools
        tools = call_args.kwargs["tools"]
        tool_names = [tool["name"] for tool in tools]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names
    
    def test_session_management(self, mock_rag_system):
        """Test session management in query processing"""
        session_id = "test-session-123"
        query = "Test query"
        
        # Execute
        result = mock_rag_system.query(query, session_id)
        
        # Verify session management calls
        mock_rag_system._mock_session_manager.get_history.assert_called_once_with(session_id)
        mock_rag_system._mock_session_manager.add_exchange.assert_called_once_with(
            session_id, query, result["answer"]
        )
    
    def test_conversation_history_passed_to_ai(self, mock_rag_system):
        """Test that conversation history is passed to AI generator"""
        # Setup - mock session manager to return history
        mock_rag_system._mock_session_manager.get_history.return_value = "Previous: conversation history"
        
        # Execute
        mock_rag_system.query("Follow-up question", "test-session")
        
        # Verify conversation history was passed to AI
        call_args = mock_rag_system._mock_ai_generator.generate_response.call_args
        assert "conversation_history" in call_args.kwargs
        assert call_args.kwargs["conversation_history"] == "Previous: conversation history"
    
    def test_source_tracking_from_tools(self, mock_rag_system):
        """Test that sources are properly tracked from tool executions"""
        # Setup - mock tool manager to return sources
        mock_search_tool = Mock()
        mock_search_tool.last_sources = [
            {"text": "Course A - Lesson 1", "link": "https://example.com/lesson1"},
            {"text": "Course B - Lesson 2", "link": "https://example.com/lesson2"}
        ]
        mock_rag_system.tool_manager.get_last_sources = Mock(return_value=mock_search_tool.last_sources)
        
        # Execute
        result = mock_rag_system.query("Test query", "test-session")
        
        # Verify sources are included in result
        assert len(result["sources"]) == 2
        assert result["sources"][0]["text"] == "Course A - Lesson 1"
        assert result["sources"][0]["link"] == "https://example.com/lesson1"
        assert result["sources"][1]["text"] == "Course B - Lesson 2"
        assert result["sources"][1]["link"] == "https://example.com/lesson2"
    
    def test_error_handling_ai_generator_failure(self, mock_rag_system):
        """Test error handling when AI generator fails"""
        # Setup - make AI generator raise exception
        mock_rag_system._mock_ai_generator.generate_response.side_effect = Exception("AI service unavailable")
        
        # Execute - should not raise exception
        result = mock_rag_system.query("Test query", "test-session")
        
        # Verify error is handled gracefully
        assert "answer" in result
        assert "error" in result["answer"].lower() or "sorry" in result["answer"].lower()
    
    def test_query_with_empty_session_id(self, mock_rag_system):
        """Test query processing with empty session ID"""
        # Execute
        result = mock_rag_system.query("Test query", "")
        
        # Should still work and return a session ID
        assert "session_id" in result
        assert result["session_id"] != ""
    
    def test_content_vs_outline_query_routing(self, mock_rag_system):
        """Test that different query types are handled appropriately"""
        # Test content query
        content_result = mock_rag_system.query("How do MCP servers work?", "session1")
        
        # Test outline query  
        outline_result = mock_rag_system.query("What are the lessons in MCP course?", "session2")
        
        # Both should succeed
        assert content_result["answer"] == "AI generated response about the topic"
        assert outline_result["answer"] == "AI generated response about the topic"
        
        # Both should call AI generator with tools
        assert mock_rag_system._mock_ai_generator.generate_response.call_count == 2


class TestRAGSystemInitialization:
    """Test RAG system initialization and component setup"""
    
    def test_initialization_with_anthropic_provider(self, mock_rag_config):
        """Test RAG system initialization with Anthropic provider"""
        mock_rag_config.LLM_PROVIDER = "anthropic"
        
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator') as mock_ai_class, \
             patch('rag_system.SessionManager'):
            
            rag_system = RAGSystem(mock_rag_config)
            
            # Verify AI generator was initialized with correct parameters
            mock_ai_class.assert_called_once_with(
                "anthropic", 
                mock_rag_config.ANTHROPIC_API_KEY, 
                mock_rag_config.ANTHROPIC_MODEL
            )
    
    def test_initialization_with_gemini_provider(self, mock_rag_config):
        """Test RAG system initialization with Gemini provider"""
        mock_rag_config.LLM_PROVIDER = "gemini"
        mock_rag_config.GEMINI_API_KEY = "gemini-test-key"
        mock_rag_config.GEMINI_MODEL = "gemini-pro"
        
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator') as mock_ai_class, \
             patch('rag_system.SessionManager'):
            
            rag_system = RAGSystem(mock_rag_config)
            
            # Verify AI generator was initialized with correct parameters
            mock_ai_class.assert_called_once_with(
                "gemini", 
                mock_rag_config.GEMINI_API_KEY, 
                mock_rag_config.GEMINI_MODEL
            )
    
    def test_unsupported_provider_raises_error(self, mock_rag_config):
        """Test that unsupported LLM provider raises error"""
        mock_rag_config.LLM_PROVIDER = "unsupported"
        
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'):
            
            with pytest.raises(ValueError) as exc_info:
                RAGSystem(mock_rag_config)
            
            assert "Unsupported LLM provider" in str(exc_info.value)
    
    def test_tools_registration(self, mock_rag_config):
        """Test that both search and outline tools are registered"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'):
            
            rag_system = RAGSystem(mock_rag_config)
            
            # Verify both tools are registered
            tool_definitions = rag_system.tool_manager.get_tool_definitions()
            tool_names = [tool["name"] for tool in tool_definitions]
            
            assert "search_course_content" in tool_names
            assert "get_course_outline" in tool_names
            assert len(tool_names) == 2
    
    def test_component_initialization_order(self, mock_rag_config):
        """Test that components are initialized in correct order"""
        with patch('rag_system.DocumentProcessor') as mock_dp, \
             patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_sm:
            
            rag_system = RAGSystem(mock_rag_config)
            
            # Verify all components were initialized
            mock_dp.assert_called_once()
            mock_vs.assert_called_once()
            mock_ai.assert_called_once()
            mock_sm.assert_called_once()
            
            # Verify vector store is passed to tools
            assert hasattr(rag_system, 'search_tool')
            assert hasattr(rag_system, 'outline_tool')
            assert hasattr(rag_system, 'tool_manager')


class TestRAGSystemDocumentManagement:
    """Test RAG system document management functionality"""
    
    def test_add_course_document(self, mock_rag_config):
        """Test adding a course document"""
        with patch('rag_system.DocumentProcessor') as mock_dp_class, \
             patch('rag_system.VectorStore') as mock_vs_class, \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'):
            
            # Setup mock document processor
            mock_dp = Mock()
            mock_course = Mock()
            mock_course.title = "Test Course"
            mock_chunks = [Mock(), Mock()]  # 2 chunks
            mock_dp.process_document.return_value = (mock_course, mock_chunks)
            mock_dp_class.return_value = mock_dp
            
            # Setup mock vector store
            mock_vs = Mock()
            mock_vs_class.return_value = mock_vs
            
            rag_system = RAGSystem(mock_rag_config)
            
            # Execute
            course, chunk_count = rag_system.add_course_document("test_file.txt")
            
            # Verify
            assert course == mock_course
            assert chunk_count == 2
            mock_dp.process_document.assert_called_once_with("test_file.txt")
            mock_vs.add_course_metadata.assert_called_once_with(mock_course)
            mock_vs.add_course_chunks.assert_called_once_with(mock_chunks)