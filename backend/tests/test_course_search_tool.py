"""Tests for CourseSearchTool.execute() method"""

import pytest
from unittest.mock import Mock

from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchToolExecute:
    """Test cases for CourseSearchTool execute method"""
    
    def test_execute_basic_search(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test basic search functionality"""
        # Setup
        mock_vector_store.search.return_value = mock_search_results(
            documents=["This is content about API usage in MCP"],
            metadata=[{
                'course_title': 'MCP: Build Rich-Context AI Apps with Anthropic',
                'lesson_number': 2,
                'lesson_title': 'API Usage'
            }]
        )
        
        # Execute
        result = course_search_tool.execute("API usage")
        
        # Verify
        assert "MCP: Build Rich-Context AI Apps with Anthropic" in result
        assert "Lesson 2" in result
        assert "This is content about API usage in MCP" in result
        mock_vector_store.search.assert_called_once_with(
            query="API usage",
            course_name=None,
            lesson_number=None
        )
    
    def test_execute_with_course_filter(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test search with course name filter"""
        # Setup
        mock_vector_store.search.return_value = mock_search_results(
            documents=["Content about MCP servers"],
            metadata=[{
                'course_title': 'MCP: Build Rich-Context AI Apps with Anthropic',
                'lesson_number': 3
            }]
        )
        
        # Execute
        result = course_search_tool.execute("servers", course_name="MCP")
        
        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="servers",
            course_name="MCP",
            lesson_number=None
        )
        assert "MCP: Build Rich-Context AI Apps with Anthropic" in result
        assert "Content about MCP servers" in result
    
    def test_execute_with_lesson_filter(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test search with lesson number filter"""
        # Setup
        mock_vector_store.search.return_value = mock_search_results(
            documents=["Introduction content"],
            metadata=[{
                'course_title': 'Test Course',
                'lesson_number': 1
            }]
        )
        
        # Execute
        result = course_search_tool.execute("introduction", lesson_number=1)
        
        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="introduction",
            course_name=None,
            lesson_number=1
        )
        assert "Lesson 1" in result
        assert "Introduction content" in result
    
    def test_execute_with_both_filters(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test search with both course name and lesson number filters"""
        # Setup
        mock_vector_store.search.return_value = mock_search_results(
            documents=["Specific lesson content"],
            metadata=[{
                'course_title': 'MCP Course',
                'lesson_number': 2
            }]
        )
        
        # Execute
        result = course_search_tool.execute("content", course_name="MCP", lesson_number=2)
        
        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="content",
            course_name="MCP",
            lesson_number=2
        )
    
    def test_execute_no_results(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test behavior when no results are found"""
        # Setup
        mock_vector_store.search.return_value = mock_search_results(
            documents=[],
            metadata=[]
        )
        
        # Execute
        result = course_search_tool.execute("nonexistent topic")
        
        # Verify
        assert "No relevant content found" in result
        assert "nonexistent topic" not in result  # Should not echo the query
    
    def test_execute_no_results_with_filters(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test no results message includes filter information"""
        # Setup
        mock_vector_store.search.return_value = mock_search_results(
            documents=[],
            metadata=[]
        )
        
        # Execute
        result = course_search_tool.execute("topic", course_name="NonExistent", lesson_number=99)
        
        # Verify
        assert "No relevant content found" in result
        assert "in course 'NonExistent'" in result
        assert "in lesson 99" in result
    
    def test_execute_error_handling(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test error handling when vector store returns error"""
        # Setup
        mock_vector_store.search.return_value = mock_search_results(
            error="Database connection failed"
        )
        
        # Execute
        result = course_search_tool.execute("test query")
        
        # Verify
        assert result == "Database connection failed"
    
    def test_execute_multiple_results_formatting(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test formatting of multiple search results"""
        # Setup
        mock_vector_store.search.return_value = mock_search_results(
            documents=[
                "First piece of content",
                "Second piece of content"
            ],
            metadata=[
                {
                    'course_title': 'Course A',
                    'lesson_number': 1
                },
                {
                    'course_title': 'Course B',
                    'lesson_number': 2
                }
            ]
        )
        
        # Execute
        result = course_search_tool.execute("content")
        
        # Verify
        assert "Course A" in result
        assert "Course B" in result
        assert "Lesson 1" in result
        assert "Lesson 2" in result
        assert "First piece of content" in result
        assert "Second piece of content" in result
        # Results should be separated
        assert result.count("\n\n") >= 1
    
    def test_execute_source_tracking(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test that sources are tracked properly for UI display"""
        # Setup
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson/1"
        mock_vector_store.search.return_value = mock_search_results(
            documents=["Test content"],
            metadata=[{
                'course_title': 'Test Course',
                'lesson_number': 1
            }]
        )
        
        # Execute
        course_search_tool.execute("test")
        
        # Verify source tracking
        assert len(course_search_tool.last_sources) == 1
        source = course_search_tool.last_sources[0]
        assert source['text'] == "Test Course - Lesson 1"
        assert source['link'] == "https://example.com/lesson/1"
    
    def test_execute_metadata_edge_cases(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test handling of missing or incomplete metadata"""
        # Setup - missing lesson number
        mock_vector_store.search.return_value = mock_search_results(
            documents=["Content without lesson number"],
            metadata=[{
                'course_title': 'Test Course'
                # No lesson_number
            }]
        )
        
        # Execute
        result = course_search_tool.execute("test")
        
        # Verify
        assert "Test Course" in result
        assert "Content without lesson number" in result
        # Should handle missing lesson number gracefully
        
        # Test missing course title
        mock_vector_store.search.return_value = mock_search_results(
            documents=["Content without course title"],
            metadata=[{
                'lesson_number': 1
                # No course_title
            }]
        )
        
        result = course_search_tool.execute("test")
        assert "unknown" in result.lower() or "Content without course title" in result


class TestCourseSearchToolDefinition:
    """Test the tool definition for CourseSearchTool"""
    
    def test_tool_definition_structure(self, course_search_tool):
        """Test that tool definition has correct structure"""
        definition = course_search_tool.get_tool_definition()
        
        # Basic structure
        assert "name" in definition
        assert "description" in definition
        assert "input_schema" in definition
        
        # Tool name
        assert definition["name"] == "search_course_content"
        
        # Schema structure
        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        
        # Required parameter
        assert "query" in schema["required"]
        
        # Optional parameters
        properties = schema["properties"]
        assert "query" in properties
        assert "course_name" in properties
        assert "lesson_number" in properties
        
        # Parameter types
        assert properties["query"]["type"] == "string"
        assert properties["course_name"]["type"] == "string"
        assert properties["lesson_number"]["type"] == "integer"