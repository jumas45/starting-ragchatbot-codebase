import pytest
from pydantic import ValidationError
from models import Lesson, Course, CourseChunk


class TestLesson:
    """Test Lesson model"""
    
    def test_lesson_creation_minimal(self):
        """Test creating lesson with minimal required fields"""
        lesson = Lesson(lesson_number=1, title="Introduction")
        
        assert lesson.lesson_number == 1
        assert lesson.title == "Introduction"
        assert lesson.lesson_link is None
    
    def test_lesson_creation_complete(self):
        """Test creating lesson with all fields"""
        lesson = Lesson(
            lesson_number=2,
            title="Advanced Topics",
            lesson_link="https://example.com/lesson2"
        )
        
        assert lesson.lesson_number == 2
        assert lesson.title == "Advanced Topics"
        assert lesson.lesson_link == "https://example.com/lesson2"
    
    def test_lesson_validation_missing_required_fields(self):
        """Test validation error when required fields are missing"""
        with pytest.raises(ValidationError) as exc_info:
            Lesson(title="Missing lesson number")
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert "lesson_number" in errors[0]["loc"]
        
        with pytest.raises(ValidationError) as exc_info:
            Lesson(lesson_number=1)
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert "title" in errors[0]["loc"]
    
    def test_lesson_validation_field_types(self):
        """Test validation of field types"""
        # Test invalid lesson_number type
        with pytest.raises(ValidationError) as exc_info:
            Lesson(lesson_number="not_a_number", title="Test")
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "int_parsing" for error in errors)
        
        # Test invalid title type
        with pytest.raises(ValidationError) as exc_info:
            Lesson(lesson_number=1, title=123)
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "string_type" for error in errors)
    
    def test_lesson_validation_optional_fields(self):
        """Test that optional fields work correctly"""
        lesson = Lesson(lesson_number=1, title="Test", lesson_link=None)
        assert lesson.lesson_link is None
        
        # Test that empty string is preserved
        lesson = Lesson(lesson_number=1, title="Test", lesson_link="")
        assert lesson.lesson_link == ""
    
    def test_lesson_equality(self):
        """Test lesson equality comparison"""
        lesson1 = Lesson(lesson_number=1, title="Test", lesson_link="http://test.com")
        lesson2 = Lesson(lesson_number=1, title="Test", lesson_link="http://test.com")
        lesson3 = Lesson(lesson_number=2, title="Test", lesson_link="http://test.com")
        
        assert lesson1 == lesson2
        assert lesson1 != lesson3
    
    def test_lesson_serialization(self):
        """Test lesson serialization to dict"""
        lesson = Lesson(lesson_number=1, title="Test", lesson_link="http://test.com")
        data = lesson.model_dump()
        
        expected = {
            "lesson_number": 1,
            "title": "Test",
            "lesson_link": "http://test.com"
        }
        assert data == expected
    
    def test_lesson_json_serialization(self):
        """Test lesson JSON serialization"""
        lesson = Lesson(lesson_number=1, title="Test", lesson_link="http://test.com")
        json_str = lesson.model_dump_json()
        
        assert '"lesson_number":1' in json_str
        assert '"title":"Test"' in json_str
        assert '"lesson_link":"http://test.com"' in json_str
    
    def test_lesson_deserialization(self):
        """Test creating lesson from dict"""
        data = {
            "lesson_number": 1,
            "title": "Test Lesson",
            "lesson_link": "http://example.com"
        }
        
        lesson = Lesson(**data)
        
        assert lesson.lesson_number == 1
        assert lesson.title == "Test Lesson"
        assert lesson.lesson_link == "http://example.com"


class TestCourse:
    """Test Course model"""
    
    def test_course_creation_minimal(self):
        """Test creating course with minimal required fields"""
        course = Course(title="Python Basics")
        
        assert course.title == "Python Basics"
        assert course.course_link is None
        assert course.instructor is None
        assert course.lessons == []
    
    def test_course_creation_complete(self):
        """Test creating course with all fields"""
        lessons = [
            Lesson(lesson_number=1, title="Intro"),
            Lesson(lesson_number=2, title="Advanced")
        ]
        
        course = Course(
            title="Complete Course",
            course_link="https://example.com/course",
            instructor="John Doe",
            lessons=lessons
        )
        
        assert course.title == "Complete Course"
        assert course.course_link == "https://example.com/course"
        assert course.instructor == "John Doe"
        assert len(course.lessons) == 2
        assert course.lessons[0].title == "Intro"
        assert course.lessons[1].title == "Advanced"
    
    def test_course_validation_missing_title(self):
        """Test validation error when title is missing"""
        with pytest.raises(ValidationError) as exc_info:
            Course()
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert "title" in errors[0]["loc"]
    
    def test_course_validation_field_types(self):
        """Test validation of field types"""
        # Test invalid title type
        with pytest.raises(ValidationError) as exc_info:
            Course(title=123)
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "string_type" for error in errors)
        
        # Test invalid lessons type
        with pytest.raises(ValidationError) as exc_info:
            Course(title="Test", lessons="not_a_list")
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "list_type" for error in errors)
    
    def test_course_lessons_validation(self):
        """Test that lessons are properly validated"""
        # Test invalid lesson in list
        with pytest.raises(ValidationError) as exc_info:
            Course(title="Test", lessons=[
                Lesson(lesson_number=1, title="Valid"),
                {"invalid": "lesson"}  # This should fail
            ])
        
        # Should have validation errors
        errors = exc_info.value.errors()
        assert len(errors) > 0
    
    def test_course_add_lesson(self):
        """Test adding lessons to course"""
        course = Course(title="Test Course")
        lesson = Lesson(lesson_number=1, title="First Lesson")
        
        course.lessons.append(lesson)
        
        assert len(course.lessons) == 1
        assert course.lessons[0] == lesson
    
    def test_course_equality(self):
        """Test course equality comparison"""
        lesson1 = Lesson(lesson_number=1, title="Lesson 1")
        lesson2 = Lesson(lesson_number=1, title="Lesson 1")
        
        course1 = Course(title="Test", instructor="John", lessons=[lesson1])
        course2 = Course(title="Test", instructor="John", lessons=[lesson2])
        course3 = Course(title="Different", instructor="John", lessons=[lesson1])
        
        assert course1 == course2
        assert course1 != course3
    
    def test_course_serialization(self):
        """Test course serialization to dict"""
        lesson = Lesson(lesson_number=1, title="Test Lesson")
        course = Course(
            title="Test Course",
            instructor="Jane Doe",
            lessons=[lesson]
        )
        
        data = course.model_dump()
        
        assert data["title"] == "Test Course"
        assert data["instructor"] == "Jane Doe"
        assert len(data["lessons"]) == 1
        assert data["lessons"][0]["lesson_number"] == 1
    
    def test_course_json_serialization(self):
        """Test course JSON serialization"""
        lesson = Lesson(lesson_number=1, title="Test")
        course = Course(title="Test Course", lessons=[lesson])
        
        json_str = course.model_dump_json()
        
        assert '"title":"Test Course"' in json_str
        assert '"lessons":[' in json_str
        assert '"lesson_number":1' in json_str
    
    def test_course_deserialization(self):
        """Test creating course from dict"""
        data = {
            "title": "Deserialized Course",
            "course_link": "http://example.com",
            "instructor": "Test Instructor",
            "lessons": [
                {"lesson_number": 1, "title": "Lesson 1"},
                {"lesson_number": 2, "title": "Lesson 2", "lesson_link": "http://example.com/lesson2"}
            ]
        }
        
        course = Course(**data)
        
        assert course.title == "Deserialized Course"
        assert course.instructor == "Test Instructor"
        assert len(course.lessons) == 2
        assert course.lessons[0].lesson_number == 1
        assert course.lessons[1].lesson_link == "http://example.com/lesson2"


class TestCourseChunk:
    """Test CourseChunk model"""
    
    def test_course_chunk_creation_minimal(self):
        """Test creating course chunk with minimal required fields"""
        chunk = CourseChunk(
            content="This is test content",
            course_title="Test Course",
            chunk_index=0
        )
        
        assert chunk.content == "This is test content"
        assert chunk.course_title == "Test Course"
        assert chunk.lesson_number is None
        assert chunk.chunk_index == 0
    
    def test_course_chunk_creation_complete(self):
        """Test creating course chunk with all fields"""
        chunk = CourseChunk(
            content="Complete chunk content",
            course_title="Complete Course",
            lesson_number=1,
            chunk_index=5
        )
        
        assert chunk.content == "Complete chunk content"
        assert chunk.course_title == "Complete Course"
        assert chunk.lesson_number == 1
        assert chunk.chunk_index == 5
    
    def test_course_chunk_validation_missing_fields(self):
        """Test validation errors for missing required fields"""
        # Missing content
        with pytest.raises(ValidationError) as exc_info:
            CourseChunk(course_title="Test", chunk_index=0)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("content",) and error["type"] == "missing" for error in errors)
        
        # Missing course_title
        with pytest.raises(ValidationError) as exc_info:
            CourseChunk(content="Test", chunk_index=0)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("course_title",) and error["type"] == "missing" for error in errors)
        
        # Missing chunk_index
        with pytest.raises(ValidationError) as exc_info:
            CourseChunk(content="Test", course_title="Test")
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("chunk_index",) and error["type"] == "missing" for error in errors)
    
    def test_course_chunk_validation_field_types(self):
        """Test validation of field types"""
        # Invalid content type
        with pytest.raises(ValidationError) as exc_info:
            CourseChunk(content=123, course_title="Test", chunk_index=0)
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "string_type" for error in errors)
        
        # Invalid chunk_index type
        with pytest.raises(ValidationError) as exc_info:
            CourseChunk(content="Test", course_title="Test", chunk_index="not_int")
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "int_parsing" for error in errors)
        
        # Invalid lesson_number type
        with pytest.raises(ValidationError) as exc_info:
            CourseChunk(content="Test", course_title="Test", chunk_index=0, lesson_number="not_int")
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "int_parsing" for error in errors)
    
    def test_course_chunk_optional_lesson_number(self):
        """Test that lesson_number is properly optional"""
        chunk = CourseChunk(content="Test", course_title="Test", chunk_index=0, lesson_number=None)
        assert chunk.lesson_number is None
        
        chunk = CourseChunk(content="Test", course_title="Test", chunk_index=0, lesson_number=5)
        assert chunk.lesson_number == 5
    
    def test_course_chunk_equality(self):
        """Test course chunk equality comparison"""
        chunk1 = CourseChunk(content="Test", course_title="Course", lesson_number=1, chunk_index=0)
        chunk2 = CourseChunk(content="Test", course_title="Course", lesson_number=1, chunk_index=0)
        chunk3 = CourseChunk(content="Different", course_title="Course", lesson_number=1, chunk_index=0)
        
        assert chunk1 == chunk2
        assert chunk1 != chunk3
    
    def test_course_chunk_serialization(self):
        """Test course chunk serialization to dict"""
        chunk = CourseChunk(
            content="Serialization test",
            course_title="Test Course",
            lesson_number=2,
            chunk_index=10
        )
        
        data = chunk.model_dump()
        
        expected = {
            "content": "Serialization test",
            "course_title": "Test Course",
            "lesson_number": 2,
            "chunk_index": 10
        }
        assert data == expected
    
    def test_course_chunk_json_serialization(self):
        """Test course chunk JSON serialization"""
        chunk = CourseChunk(
            content="JSON test content",
            course_title="JSON Course",
            chunk_index=1
        )
        
        json_str = chunk.model_dump_json()
        
        assert '"content":"JSON test content"' in json_str
        assert '"course_title":"JSON Course"' in json_str
        assert '"chunk_index":1' in json_str
        assert '"lesson_number":null' in json_str
    
    def test_course_chunk_deserialization(self):
        """Test creating course chunk from dict"""
        data = {
            "content": "Deserialized content",
            "course_title": "Deserialized Course",
            "lesson_number": 3,
            "chunk_index": 7
        }
        
        chunk = CourseChunk(**data)
        
        assert chunk.content == "Deserialized content"
        assert chunk.course_title == "Deserialized Course"
        assert chunk.lesson_number == 3
        assert chunk.chunk_index == 7
    
    def test_course_chunk_edge_cases(self):
        """Test course chunk edge cases"""
        # Empty content
        chunk = CourseChunk(content="", course_title="Test", chunk_index=0)
        assert chunk.content == ""
        
        # Zero chunk_index
        chunk = CourseChunk(content="Test", course_title="Test", chunk_index=0)
        assert chunk.chunk_index == 0
        
        # Negative lesson_number (if allowed by business logic)
        chunk = CourseChunk(content="Test", course_title="Test", chunk_index=0, lesson_number=0)
        assert chunk.lesson_number == 0


class TestModelIntegration:
    """Test integration between different models"""
    
    def test_course_with_lessons_serialization_roundtrip(self):
        """Test complete serialization roundtrip for complex course"""
        # Create complex course
        lessons = [
            Lesson(lesson_number=1, title="Introduction", lesson_link="http://example.com/1"),
            Lesson(lesson_number=2, title="Advanced Topics"),
            Lesson(lesson_number=3, title="Conclusion", lesson_link="http://example.com/3")
        ]
        
        original_course = Course(
            title="Complete Integration Test",
            course_link="http://example.com/course",
            instructor="Integration Tester",
            lessons=lessons
        )
        
        # Serialize to dict
        course_data = original_course.model_dump()
        
        # Deserialize back
        restored_course = Course(**course_data)
        
        # Verify everything matches
        assert restored_course.title == original_course.title
        assert restored_course.course_link == original_course.course_link
        assert restored_course.instructor == original_course.instructor
        assert len(restored_course.lessons) == len(original_course.lessons)
        
        for original_lesson, restored_lesson in zip(original_course.lessons, restored_course.lessons):
            assert restored_lesson.lesson_number == original_lesson.lesson_number
            assert restored_lesson.title == original_lesson.title
            assert restored_lesson.lesson_link == original_lesson.lesson_link
    
    def test_models_with_special_characters(self):
        """Test models handle special characters correctly"""
        # Test with various special characters and unicode
        special_title = "Course with Special: @#$%^&*()[]{}|;:'\",.<>?/~`"
        unicode_title = "Course with Unicode: 你好, café, naïve, résumé"
        
        lesson = Lesson(lesson_number=1, title=unicode_title)
        course = Course(title=special_title, instructor="Test", lessons=[lesson])
        chunk = CourseChunk(
            content=f"{special_title} {unicode_title}",
            course_title=special_title,
            chunk_index=0
        )
        
        # All should work without issues
        assert course.title == special_title
        assert lesson.title == unicode_title
        assert chunk.content == f"{special_title} {unicode_title}"
        
        # Serialization should preserve special characters
        course_json = course.model_dump_json()
        restored_course = Course.model_validate_json(course_json)
        assert restored_course.title == special_title
        assert restored_course.lessons[0].title == unicode_title
    
    def test_model_validation_comprehensive(self):
        """Test comprehensive validation scenarios"""
        # Test valid scenarios don't raise errors
        valid_lesson = Lesson(lesson_number=1, title="Valid Lesson")
        valid_course = Course(title="Valid Course", lessons=[valid_lesson])
        valid_chunk = CourseChunk(content="Valid", course_title="Valid", chunk_index=0)
        
        assert valid_lesson.lesson_number == 1
        assert valid_course.title == "Valid Course"
        assert valid_chunk.content == "Valid"
        
        # Test boundary values
        edge_lesson = Lesson(lesson_number=0, title="")  # Empty title allowed
        edge_course = Course(title="X")  # Single character title
        edge_chunk = CourseChunk(content="X", course_title="Y", chunk_index=0)
        
        assert edge_lesson.lesson_number == 0
        assert edge_course.title == "X"
        assert edge_chunk.content == "X"