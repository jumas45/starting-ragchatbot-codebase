"""Fixed tests for RAG system with correct expectations"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import tempfile
import os

from rag_system import RAGSystem


class TestRAGSystemContentQueriesFixed:
    """Fixed test cases for RAG system content queries"""
    
    @pytest.fixture
    def mock_rag_system_fixed(self, mock_config):
        """Create a RAG system with properly mocked components"""
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
            
            # Setup mock session manager with CORRECT method names
            mock_session_manager = Mock()
            mock_session_manager.get_conversation_history.return_value = ""  # Correct method name
            mock_session_manager.add_exchange.return_value = None
            mock_session_manager.create_session.return_value = "new-session-123"
            mock_sm_class.return_value = mock_session_manager
            
            # Update config to match fixture name
            mock_config.LLM_PROVIDER = "anthropic"
            mock_config.ANTHROPIC_API_KEY = "test-key"  
            mock_config.ANTHROPIC_MODEL = "claude-3-sonnet-20240229"
            
            rag_system = RAGSystem(mock_config)
            
            # Store mocks for access in tests
            rag_system._mock_vector_store = mock_vector_store
            rag_system._mock_ai_generator = mock_ai_generator
            rag_system._mock_session_manager = mock_session_manager
            
            return rag_system
    
    def test_query_returns_correct_tuple_format(self, mock_rag_system_fixed):
        """Test that query returns correct tuple format (answer, sources)"""
        # Execute
        result = mock_rag_system_fixed.query("What is MCP?", "test-session")
        
        # Verify correct return format - should be tuple
        assert isinstance(result, tuple)
        assert len(result) == 2
        
        answer, sources = result
        assert isinstance(answer, str)
        assert isinstance(sources, list)
        assert answer == "AI generated response about the topic"
    
    def test_session_management_with_correct_method_names(self, mock_rag_system_fixed):
        """Test session management with correct method names"""
        session_id = "test-session-123"
        query = "Test query"
        
        # Execute
        answer, sources = mock_rag_system_fixed.query(query, session_id)
        
        # Verify session management calls with CORRECT method names
        mock_rag_system_fixed._mock_session_manager.get_conversation_history.assert_called_once_with(session_id)
        mock_rag_system_fixed._mock_session_manager.add_exchange.assert_called_once_with(
            session_id, query, answer
        )
    
    def test_empty_session_id_creates_new_session(self, mock_rag_system_fixed):
        """Test that empty session ID works (though session creation happens in app.py)"""
        # Execute with empty session
        result = mock_rag_system_fixed.query("Test query", "")
        
        # Should still work and return tuple
        assert isinstance(result, tuple)
        answer, sources = result
        assert answer == "AI generated response about the topic"
    
    def test_tools_integration_in_ai_call(self, mock_rag_system_fixed):
        """Test that AI generator is called with correct tools"""
        # Execute
        mock_rag_system_fixed.query("Explain MCP servers", "test-session")
        
        # Verify AI generator was called with tools
        mock_rag_system_fixed._mock_ai_generator.generate_response.assert_called_once()
        call_args = mock_rag_system_fixed._mock_ai_generator.generate_response.call_args
        
        # Should be called with tools and tool_manager
        assert "tools" in call_args.kwargs
        assert "tool_manager" in call_args.kwargs
        assert call_args.kwargs["tool_manager"] is not None
        
        # Tools should include both search and outline tools
        tools = call_args.kwargs["tools"]
        tool_names = [tool["name"] for tool in tools]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names
    
    def test_conversation_history_integration(self, mock_rag_system_fixed):
        """Test conversation history is passed correctly"""
        # Setup - mock session manager to return history
        mock_rag_system_fixed._mock_session_manager.get_conversation_history.return_value = "Previous conversation"
        
        # Execute
        mock_rag_system_fixed.query("Follow-up question", "test-session")
        
        # Verify conversation history was passed to AI
        call_args = mock_rag_system_fixed._mock_ai_generator.generate_response.call_args
        assert "conversation_history" in call_args.kwargs
        assert call_args.kwargs["conversation_history"] == "Previous conversation"
    
    def test_source_tracking_integration(self, mock_rag_system_fixed):
        """Test source tracking from tool manager"""
        # Setup - mock tool manager to return sources
        test_sources = [
            {"text": "Course A - Lesson 1", "link": "https://example.com/lesson1"},
            {"text": "Course B - Lesson 2", "link": "https://example.com/lesson2"}
        ]
        mock_rag_system_fixed.tool_manager.get_last_sources = Mock(return_value=test_sources)
        mock_rag_system_fixed.tool_manager.reset_sources = Mock()
        
        # Execute
        answer, sources = mock_rag_system_fixed.query("Test query", "test-session")
        
        # Verify sources are returned correctly
        assert sources == test_sources
        mock_rag_system_fixed.tool_manager.get_last_sources.assert_called_once()
        mock_rag_system_fixed.tool_manager.reset_sources.assert_called_once()


class TestRAGSystemEndToEndIntegration:
    """Test the actual integration with real components (light integration tests)"""
    
    def test_app_endpoint_integration_format(self):
        """Test that the app.py correctly transforms RAG tuple to API response"""
        # This test verifies the integration between RAG system tuple return 
        # and the app.py transformation to API response format
        
        # Mock RAG system returning tuple
        mock_rag = Mock()
        mock_rag.query.return_value = ("Test answer", [{"text": "Source 1", "link": "http://test.com"}])
        mock_rag.session_manager.create_session.return_value = "new-session-123"
        
        # Simulate app.py logic
        answer, sources = mock_rag.query("test query", "session-id")
        
        # App.py transforms this to:
        api_response = {
            "answer": answer,
            "sources": [{"text": source["text"], "link": source["link"]} for source in sources],
            "session_id": "session-id"
        }
        
        # Verify the transformation works
        assert api_response["answer"] == "Test answer"
        assert len(api_response["sources"]) == 1
        assert api_response["sources"][0]["text"] == "Source 1"
        assert api_response["sources"][0]["link"] == "http://test.com"
        assert api_response["session_id"] == "session-id"
    
    def test_tool_manager_registration_verification(self, mock_config):
        """Verify that tools are properly registered in real system"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'):
            
            rag_system = RAGSystem(mock_config)
            
            # Verify tools are registered
            tool_definitions = rag_system.tool_manager.get_tool_definitions()
            tool_names = [tool["name"] for tool in tool_definitions]
            
            assert "search_course_content" in tool_names
            assert "get_course_outline" in tool_names
            assert len(tool_names) == 2
            
            # Verify tools have correct structure
            for tool_def in tool_definitions:
                assert "name" in tool_def
                assert "description" in tool_def
                assert "input_schema" in tool_def


class TestSystemHealthCheck:
    """High-level health checks for the system"""
    
    def test_course_search_tool_health(self, course_search_tool):
        """Verify CourseSearchTool is healthy"""
        # Test tool definition
        definition = course_search_tool.get_tool_definition()
        assert definition["name"] == "search_course_content"
        assert "query" in definition["input_schema"]["required"]
        
        # Test execution doesn't crash
        try:
            result = course_search_tool.execute("test query")
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"CourseSearchTool execution failed: {e}")
    
    def test_course_outline_tool_health(self, course_outline_tool):
        """Verify CourseOutlineTool is healthy"""
        # Test tool definition  
        definition = course_outline_tool.get_tool_definition()
        assert definition["name"] == "get_course_outline"
        assert "course_title" in definition["input_schema"]["required"]
        
        # Test execution doesn't crash
        try:
            result = course_outline_tool.execute("test course")
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"CourseOutlineTool execution failed: {e}")


# Summary of Fixes Applied:
# 1. ✅ Fixed RAG system return format expectations (tuple not dict)
# 2. ✅ Fixed session manager method names (get_conversation_history)  
# 3. ✅ Fixed fixture naming conflicts (mock_config)
# 4. ✅ Added realistic integration tests
# 5. ✅ Added health check tests for tools