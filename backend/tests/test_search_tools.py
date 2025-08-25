"""Comprehensive tests for search_tools module including all tools and managers"""

import pytest
from unittest.mock import Mock, patch
from search_tools import Tool, CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing"""
    store = Mock()
    store.search.return_value = SearchResults([], [], [])
    store.get_lesson_link.return_value = None
    store.get_all_courses_metadata.return_value = []
    return store


@pytest.fixture
def mock_search_results():
    """Factory for creating mock search results"""
    def _create_results(documents=None, metadata=None, distances=None, error=None):
        return SearchResults(
            documents=documents or [],
            metadata=metadata or [],
            distances=distances or [],
            error=error
        )
    return _create_results


@pytest.fixture
def course_search_tool(mock_vector_store):
    """CourseSearchTool instance for testing"""
    return CourseSearchTool(mock_vector_store)


@pytest.fixture
def course_outline_tool(mock_vector_store):
    """CourseOutlineTool instance for testing"""
    return CourseOutlineTool(mock_vector_store)


@pytest.fixture
def tool_manager():
    """ToolManager instance for testing"""
    return ToolManager()


class TestTool:
    """Test abstract Tool base class"""
    
    def test_abstract_base_class(self):
        """Test that Tool cannot be instantiated directly"""
        with pytest.raises(TypeError):
            Tool()
    
    def test_abstract_methods(self):
        """Test that Tool has required abstract methods"""
        assert hasattr(Tool, 'get_tool_definition')
        assert hasattr(Tool, 'execute')
        assert Tool.get_tool_definition.__isabstractmethod__
        assert Tool.execute.__isabstractmethod__


class TestCourseSearchTool:
    """Test CourseSearchTool class - comprehensive coverage"""
    
    def test_init(self, mock_vector_store):
        """Test CourseSearchTool initialization"""
        tool = CourseSearchTool(mock_vector_store)
        
        assert tool.store == mock_vector_store
        assert tool.last_sources == []
    
    def test_get_tool_definition(self, course_search_tool):
        """Test tool definition structure"""
        definition = course_search_tool.get_tool_definition()
        
        # Basic structure
        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        
        # Schema validation
        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        
        # Required fields
        assert schema["required"] == ["query"]
        
        # Properties
        properties = schema["properties"]
        assert "query" in properties
        assert "course_name" in properties
        assert "lesson_number" in properties
        
        # Property types
        assert properties["query"]["type"] == "string"
        assert properties["course_name"]["type"] == "string"
        assert properties["lesson_number"]["type"] == "integer"
        
        # Descriptions
        assert "description" in properties["query"]
        assert "description" in properties["course_name"]
        assert "description" in properties["lesson_number"]
    
    def test_execute_basic_search(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test basic search execution"""
        mock_vector_store.search.return_value = mock_search_results(
            documents=["Test content about Python"],
            metadata=[{"course_title": "Python Course", "lesson_number": 1}]
        )
        
        result = course_search_tool.execute("Python programming")
        
        mock_vector_store.search.assert_called_once_with(
            query="Python programming",
            course_name=None,
            lesson_number=None
        )
        
        assert "Python Course" in result
        assert "Lesson 1" in result
        assert "Test content about Python" in result
    
    def test_execute_with_course_filter(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test search with course name filter"""
        mock_vector_store.search.return_value = mock_search_results(
            documents=["Course-specific content"],
            metadata=[{"course_title": "Specific Course", "lesson_number": 2}]
        )
        
        result = course_search_tool.execute("content", course_name="Specific")
        
        mock_vector_store.search.assert_called_once_with(
            query="content",
            course_name="Specific",
            lesson_number=None
        )
        
        assert "Specific Course" in result
        assert "Course-specific content" in result
    
    def test_execute_with_lesson_filter(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test search with lesson number filter"""
        mock_vector_store.search.return_value = mock_search_results(
            documents=["Lesson-specific content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 3}]
        )
        
        result = course_search_tool.execute("content", lesson_number=3)
        
        mock_vector_store.search.assert_called_once_with(
            query="content",
            course_name=None,
            lesson_number=3
        )
        
        assert "Lesson 3" in result
        assert "Lesson-specific content" in result
    
    def test_execute_with_both_filters(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test search with both filters"""
        mock_vector_store.search.return_value = mock_search_results(
            documents=["Filtered content"],
            metadata=[{"course_title": "Target Course", "lesson_number": 1}]
        )
        
        result = course_search_tool.execute("content", course_name="Target", lesson_number=1)
        
        mock_vector_store.search.assert_called_once_with(
            query="content",
            course_name="Target",
            lesson_number=1
        )
    
    def test_execute_error_handling(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test error handling in search execution"""
        mock_vector_store.search.return_value = mock_search_results(
            error="Search failed: Database error"
        )
        
        result = course_search_tool.execute("test query")
        
        assert result == "Search failed: Database error"
    
    def test_execute_no_results(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test handling when no results found"""
        mock_vector_store.search.return_value = mock_search_results()
        
        result = course_search_tool.execute("nonexistent")
        
        assert "No relevant content found" in result
    
    def test_execute_no_results_with_filters(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test no results message includes filter information"""
        mock_vector_store.search.return_value = mock_search_results()
        
        result = course_search_tool.execute("query", course_name="Missing", lesson_number=99)
        
        assert "No relevant content found" in result
        assert "in course 'Missing'" in result
        assert "in lesson 99" in result
    
    def test_execute_no_results_course_filter_only(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test no results with only course filter"""
        mock_vector_store.search.return_value = mock_search_results()
        
        result = course_search_tool.execute("query", course_name="Missing")
        
        assert "No relevant content found in course 'Missing'" in result
        assert "lesson" not in result.lower()
    
    def test_execute_no_results_lesson_filter_only(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test no results with only lesson filter"""
        mock_vector_store.search.return_value = mock_search_results()
        
        result = course_search_tool.execute("query", lesson_number=99)
        
        assert "No relevant content found in lesson 99" in result
        assert "course" not in result.lower()
    
    def test_format_results_multiple(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test formatting multiple results"""
        mock_vector_store.search.return_value = mock_search_results(
            documents=["First result", "Second result", "Third result"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
                {"course_title": "Course C", "lesson_number": None}
            ]
        )
        
        result = course_search_tool.execute("test")
        
        assert "Course A - Lesson 1" in result
        assert "Course B - Lesson 2" in result
        assert "[Course C]" in result  # No lesson number
        assert "First result" in result
        assert "Second result" in result
        assert "Third result" in result
        
        # Should have separators between results
        assert result.count("\n\n") >= 2
    
    def test_format_results_missing_metadata(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test formatting with missing metadata fields"""
        mock_vector_store.search.return_value = mock_search_results(
            documents=["Content with missing metadata"],
            metadata=[{}]  # Empty metadata
        )
        
        result = course_search_tool.execute("test")
        
        assert "unknown" in result.lower()
        assert "Content with missing metadata" in result
    
    def test_source_tracking(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test that sources are tracked correctly"""
        mock_vector_store.search.return_value = mock_search_results(
            documents=["Test content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}]
        )
        mock_vector_store.get_lesson_link.return_value = "http://example.com/lesson1"
        
        course_search_tool.execute("test")
        
        assert len(course_search_tool.last_sources) == 1
        source = course_search_tool.last_sources[0]
        assert source["text"] == "Test Course - Lesson 1"
        assert source["link"] == "http://example.com/lesson1"
    
    def test_source_tracking_no_lesson(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test source tracking without lesson number"""
        mock_vector_store.search.return_value = mock_search_results(
            documents=["Content"],
            metadata=[{"course_title": "Test Course"}]
        )
        
        course_search_tool.execute("test")
        
        assert len(course_search_tool.last_sources) == 1
        source = course_search_tool.last_sources[0]
        assert source["text"] == "Test Course"
        assert source["link"] is None
    
    def test_source_tracking_multiple_results(self, course_search_tool, mock_vector_store, mock_search_results):
        """Test source tracking with multiple results"""
        mock_vector_store.search.return_value = mock_search_results(
            documents=["Content 1", "Content 2"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2}
            ]
        )
        mock_vector_store.get_lesson_link.side_effect = ["link1", "link2"]
        
        course_search_tool.execute("test")
        
        assert len(course_search_tool.last_sources) == 2
        assert course_search_tool.last_sources[0]["text"] == "Course A - Lesson 1"
        assert course_search_tool.last_sources[1]["text"] == "Course B - Lesson 2"


class TestCourseOutlineTool:
    """Test CourseOutlineTool class"""
    
    def test_init(self, mock_vector_store):
        """Test CourseOutlineTool initialization"""
        tool = CourseOutlineTool(mock_vector_store)
        
        assert tool.store == mock_vector_store
    
    def test_get_tool_definition(self, course_outline_tool):
        """Test tool definition structure"""
        definition = course_outline_tool.get_tool_definition()
        
        assert definition["name"] == "get_course_outline"
        assert "description" in definition
        assert "input_schema" in definition
        
        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert schema["required"] == ["course_title"]
        
        properties = schema["properties"]
        assert "course_title" in properties
        assert properties["course_title"]["type"] == "string"
        assert "description" in properties["course_title"]
    
    def test_execute_course_found(self, course_outline_tool, mock_vector_store):
        """Test successful course outline retrieval"""
        mock_course = {
            "title": "Python Programming",
            "course_link": "http://example.com/python",
            "instructor": "John Doe",
            "lessons": [
                {"lesson_number": 1, "lesson_title": "Introduction"},
                {"lesson_number": 2, "lesson_title": "Variables"},
                {"lesson_number": 3, "lesson_title": "Functions"}
            ]
        }
        
        mock_vector_store.get_all_courses_metadata.return_value = [mock_course]
        
        result = course_outline_tool.execute("Python")
        
        assert "**Course Title:** Python Programming" in result
        assert "**Course Link:** http://example.com/python" in result
        assert "**Instructor:** John Doe" in result
        assert "**Lessons:**" in result
        assert "Lesson 1: Introduction" in result
        assert "Lesson 2: Variables" in result
        assert "Lesson 3: Functions" in result
    
    def test_execute_course_partial_match(self, course_outline_tool, mock_vector_store):
        """Test course matching with partial names"""
        mock_courses = [
            {"title": "Advanced Python Programming", "instructor": "Jane", "lessons": []},
            {"title": "Introduction to JavaScript", "instructor": "Bob", "lessons": []}
        ]
        
        mock_vector_store.get_all_courses_metadata.return_value = mock_courses
        
        # Should match "Advanced Python Programming" with "Python"
        result = course_outline_tool.execute("Python")
        
        assert "Advanced Python Programming" in result
        assert "JavaScript" not in result
    
    def test_execute_course_case_insensitive(self, course_outline_tool, mock_vector_store):
        """Test case-insensitive course matching"""
        mock_course = {
            "title": "Python Programming",
            "instructor": "Test",
            "lessons": []
        }
        
        mock_vector_store.get_all_courses_metadata.return_value = [mock_course]
        
        result = course_outline_tool.execute("python")  # lowercase
        
        assert "Python Programming" in result
    
    def test_execute_course_not_found(self, course_outline_tool, mock_vector_store):
        """Test behavior when course is not found"""
        mock_courses = [
            {"title": "Java Programming"},
            {"title": "C++ Basics"}
        ]
        
        mock_vector_store.get_all_courses_metadata.return_value = mock_courses
        
        result = course_outline_tool.execute("Python")
        
        assert "Course 'Python' not found" in result
        assert "Available courses:" in result
        assert "Java Programming" in result
        assert "C++ Basics" in result
    
    def test_execute_no_courses_in_system(self, course_outline_tool, mock_vector_store):
        """Test behavior when no courses exist"""
        mock_vector_store.get_all_courses_metadata.return_value = []
        
        result = course_outline_tool.execute("Any Course")
        
        assert "No courses found in the system" in result
    
    def test_execute_exception_handling(self, course_outline_tool, mock_vector_store):
        """Test exception handling"""
        mock_vector_store.get_all_courses_metadata.side_effect = Exception("Database error")
        
        result = course_outline_tool.execute("Test Course")
        
        assert "Error retrieving course outline" in result
        assert "Database error" in result
    
    def test_format_course_outline_complete(self, course_outline_tool):
        """Test formatting complete course outline"""
        course_data = {
            "title": "Complete Course",
            "course_link": "http://example.com/complete",
            "instructor": "Complete Instructor",
            "lessons": [
                {"lesson_number": 1, "lesson_title": "First Lesson"},
                {"lesson_number": 2, "lesson_title": "Second Lesson"}
            ]
        }
        
        result = course_outline_tool._format_course_outline(course_data)
        
        assert "**Course Title:** Complete Course" in result
        assert "**Course Link:** http://example.com/complete" in result
        assert "**Instructor:** Complete Instructor" in result
        assert "**Lessons:**" in result
        assert "Lesson 1: First Lesson" in result
        assert "Lesson 2: Second Lesson" in result
    
    def test_format_course_outline_minimal(self, course_outline_tool):
        """Test formatting course outline with minimal data"""
        course_data = {}  # Empty course data
        
        result = course_outline_tool._format_course_outline(course_data)
        
        assert "**Course Title:** Unknown Course" in result
        assert "**Course Link:** No link available" in result
        assert "**Instructor:** Unknown" in result
        assert "No lessons found for this course" in result
    
    def test_format_course_outline_no_lessons(self, course_outline_tool):
        """Test formatting course outline with no lessons"""
        course_data = {
            "title": "No Lessons Course",
            "course_link": "http://example.com/none",
            "instructor": "Teacher",
            "lessons": []
        }
        
        result = course_outline_tool._format_course_outline(course_data)
        
        assert "No Lessons Course" in result
        assert "No lessons found for this course" in result
    
    def test_format_course_outline_missing_lesson_data(self, course_outline_tool):
        """Test formatting with incomplete lesson data"""
        course_data = {
            "title": "Test Course",
            "lessons": [
                {"lesson_number": 1},  # Missing title
                {"lesson_title": "Title Only"},  # Missing number
                {}  # Empty lesson
            ]
        }
        
        result = course_outline_tool._format_course_outline(course_data)
        
        assert "Lesson 1: Untitled" in result
        assert "Lesson N/A: Title Only" in result
        assert "Lesson N/A: Untitled" in result


class TestToolManager:
    """Test ToolManager class"""
    
    def test_init(self, tool_manager):
        """Test ToolManager initialization"""
        assert tool_manager.tools == {}
    
    def test_register_tool(self, tool_manager, course_search_tool):
        """Test registering a tool"""
        tool_manager.register_tool(course_search_tool)
        
        assert "search_course_content" in tool_manager.tools
        assert tool_manager.tools["search_course_content"] == course_search_tool
    
    def test_register_tool_without_name(self, tool_manager):
        """Test registering tool without name raises error"""
        mock_tool = Mock()
        mock_tool.get_tool_definition.return_value = {"description": "No name"}
        
        with pytest.raises(ValueError, match="Tool must have a 'name'"):
            tool_manager.register_tool(mock_tool)
    
    def test_register_multiple_tools(self, tool_manager, course_search_tool, course_outline_tool):
        """Test registering multiple tools"""
        tool_manager.register_tool(course_search_tool)
        tool_manager.register_tool(course_outline_tool)
        
        assert len(tool_manager.tools) == 2
        assert "search_course_content" in tool_manager.tools
        assert "get_course_outline" in tool_manager.tools
    
    def test_get_tool_definitions(self, tool_manager, course_search_tool, course_outline_tool):
        """Test getting all tool definitions"""
        tool_manager.register_tool(course_search_tool)
        tool_manager.register_tool(course_outline_tool)
        
        definitions = tool_manager.get_tool_definitions()
        
        assert len(definitions) == 2
        tool_names = [defn["name"] for defn in definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names
    
    def test_get_tool_definitions_empty(self, tool_manager):
        """Test getting tool definitions when no tools registered"""
        definitions = tool_manager.get_tool_definitions()
        
        assert definitions == []
    
    def test_execute_tool(self, tool_manager, mock_vector_store):
        """Test executing a registered tool"""
        course_search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(course_search_tool)
        
        with patch.object(course_search_tool, 'execute', return_value="Test result") as mock_execute:
            result = tool_manager.execute_tool("search_course_content", query="test", course_name="Test Course")
        
        assert result == "Test result"
        mock_execute.assert_called_once_with(query="test", course_name="Test Course")
    
    def test_execute_nonexistent_tool(self, tool_manager):
        """Test executing nonexistent tool"""
        result = tool_manager.execute_tool("nonexistent_tool", param="value")
        
        assert "Tool 'nonexistent_tool' not found" in result
    
    def test_get_last_sources_with_sources(self, tool_manager, mock_vector_store):
        """Test getting last sources when tool has sources"""
        course_search_tool = CourseSearchTool(mock_vector_store)
        course_search_tool.last_sources = [{"text": "Test Source", "link": "http://test.com"}]
        tool_manager.register_tool(course_search_tool)
        
        sources = tool_manager.get_last_sources()
        
        assert len(sources) == 1
        assert sources[0]["text"] == "Test Source"
        assert sources[0]["link"] == "http://test.com"
    
    def test_get_last_sources_no_sources(self, tool_manager, course_outline_tool):
        """Test getting last sources when no tools have sources"""
        tool_manager.register_tool(course_outline_tool)  # Doesn't have last_sources
        
        sources = tool_manager.get_last_sources()
        
        assert sources == []
    
    def test_get_last_sources_multiple_tools(self, tool_manager, mock_vector_store):
        """Test getting sources with multiple tools (should return first non-empty)"""
        tool1 = CourseSearchTool(mock_vector_store)
        tool2 = CourseSearchTool(mock_vector_store)
        
        tool1.last_sources = []
        tool2.last_sources = [{"text": "Tool2 Source"}]
        
        tool_manager.register_tool(tool1)
        tool_manager.register_tool(tool2)
        
        sources = tool_manager.get_last_sources()
        
        assert len(sources) == 1
        assert sources[0]["text"] == "Tool2 Source"
    
    def test_reset_sources(self, tool_manager, mock_vector_store):
        """Test resetting sources from all tools"""
        # Create two different tools with different names
        tool1 = CourseSearchTool(mock_vector_store)
        tool1.last_sources = [{"text": "Source1"}]
        
        # Create mock tool2 with different name
        tool2 = Mock()
        tool2.get_tool_definition.return_value = {"name": "mock_search_tool"}
        tool2.last_sources = [{"text": "Source2"}]
        
        tool_manager.register_tool(tool1)
        tool_manager.register_tool(tool2)
        
        tool_manager.reset_sources()
        
        assert tool1.last_sources == []
        assert tool2.last_sources == []
    
    def test_reset_sources_mixed_tools(self, tool_manager, mock_vector_store):
        """Test resetting sources with tools that don't have last_sources"""
        course_search_tool = CourseSearchTool(mock_vector_store)
        course_search_tool.last_sources = [{"text": "Source"}]
        
        # Create a mock tool without last_sources attribute
        mock_tool = Mock()
        mock_tool.get_tool_definition.return_value = {"name": "mock_tool"}
        del mock_tool.last_sources  # Ensure it doesn't have this attribute
        
        tool_manager.register_tool(course_search_tool)
        tool_manager.register_tool(mock_tool)
        
        # Should not raise error
        tool_manager.reset_sources()
        
        assert course_search_tool.last_sources == []


class TestIntegration:
    """Integration tests for search tools"""
    
    def test_full_search_workflow(self, mock_vector_store, mock_search_results):
        """Test complete search workflow with tool manager"""
        # Setup
        mock_vector_store.search.return_value = mock_search_results(
            documents=["Python is great for beginners"],
            metadata=[{"course_title": "Python Basics", "lesson_number": 1}]
        )
        
        # Create and register tools
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager = ToolManager()
        tool_manager.register_tool(search_tool)
        
        # Execute through tool manager
        result = tool_manager.execute_tool("search_course_content", query="Python beginners")
        
        # Verify
        assert "Python Basics" in result
        assert "Python is great for beginners" in result
        
        # Check sources were tracked
        sources = tool_manager.get_last_sources()
        assert len(sources) == 1
        assert "Python Basics - Lesson 1" in sources[0]["text"]
    
    def test_full_outline_workflow(self, mock_vector_store):
        """Test complete course outline workflow"""
        # Setup
        mock_courses = [{
            "title": "Python Programming Course",
            "course_link": "http://example.com/python",
            "instructor": "Alice Smith",
            "lessons": [
                {"lesson_number": 1, "lesson_title": "Getting Started"},
                {"lesson_number": 2, "lesson_title": "Data Types"}
            ]
        }]
        
        mock_vector_store.get_all_courses_metadata.return_value = mock_courses
        
        # Create and register tool
        outline_tool = CourseOutlineTool(mock_vector_store)
        tool_manager = ToolManager()
        tool_manager.register_tool(outline_tool)
        
        # Execute
        result = tool_manager.execute_tool("get_course_outline", course_title="Python")
        
        # Verify complete outline
        assert "Python Programming Course" in result
        assert "Alice Smith" in result
        assert "Lesson 1: Getting Started" in result
        assert "Lesson 2: Data Types" in result
    
    def test_error_propagation(self, mock_vector_store):
        """Test that errors are properly propagated through the system"""
        # Setup search tool to return error
        mock_vector_store.search.return_value = SearchResults([], [], [], error="Connection failed")
        
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager = ToolManager()
        tool_manager.register_tool(search_tool)
        
        result = tool_manager.execute_tool("search_course_content", query="test")
        
        assert result == "Connection failed"