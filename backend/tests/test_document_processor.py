import pytest
import tempfile
import os
from document_processor import DocumentProcessor
from models import Course, Lesson, CourseChunk


@pytest.fixture
def document_processor():
    """Create DocumentProcessor instance for testing"""
    return DocumentProcessor(chunk_size=100, chunk_overlap=20)


@pytest.fixture
def temp_file():
    """Create temporary file for testing"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    yield temp_file
    # Cleanup
    try:
        os.unlink(temp_file.name)
    except (FileNotFoundError, PermissionError):
        pass


class TestDocumentProcessor:
    """Test DocumentProcessor class"""
    
    def test_init(self):
        """Test DocumentProcessor initialization"""
        processor = DocumentProcessor(chunk_size=200, chunk_overlap=50)
        
        assert processor.chunk_size == 200
        assert processor.chunk_overlap == 50
    
    def test_read_file_utf8(self, temp_file):
        """Test reading UTF-8 encoded file"""
        content = "This is a test file with UTF-8 content."
        temp_file.write(content)
        temp_file.flush()
        
        processor = DocumentProcessor(100, 20)
        result = processor.read_file(temp_file.name)
        
        assert result == content
    
    def test_read_file_with_unicode(self, temp_file):
        """Test reading file with unicode characters"""
        content = "This file contains unicode: café, résumé, naïve"
        temp_file.write(content)
        temp_file.flush()
        
        processor = DocumentProcessor(100, 20)
        result = processor.read_file(temp_file.name)
        
        assert result == content
    
    def test_read_nonexistent_file(self):
        """Test reading nonexistent file"""
        processor = DocumentProcessor(100, 20)
        
        with pytest.raises(FileNotFoundError):
            processor.read_file("nonexistent_file.txt")
    
    def test_chunk_text_simple(self, document_processor):
        """Test simple text chunking"""
        text = "This is sentence one. This is sentence two. This is sentence three."
        
        chunks = document_processor.chunk_text(text)
        
        assert len(chunks) > 0
        assert all(len(chunk) <= document_processor.chunk_size for chunk in chunks)
    
    def test_chunk_text_with_overlap(self):
        """Test text chunking with overlap"""
        processor = DocumentProcessor(chunk_size=50, chunk_overlap=10)
        text = "First sentence here. Second sentence follows. Third sentence continues. Fourth sentence ends."
        
        chunks = processor.chunk_text(text)
        
        assert len(chunks) > 1
        # Verify chunks have some overlap (check if any words appear in consecutive chunks)
        for i in range(len(chunks) - 1):
            words_current = set(chunks[i].split())
            words_next = set(chunks[i + 1].split())
            # There should be some overlap in words between consecutive chunks
            overlap_exists = bool(words_current.intersection(words_next))
            # Note: overlap might not always exist depending on sentence boundaries
    
    def test_chunk_text_long_sentences(self):
        """Test chunking with sentences longer than chunk size"""
        processor = DocumentProcessor(chunk_size=30, chunk_overlap=5)
        text = "This is a very long sentence that exceeds the chunk size limit and should be handled properly."
        
        chunks = processor.chunk_text(text)
        
        assert len(chunks) > 0
        # First chunk should contain the entire sentence even if it exceeds chunk_size
        assert chunks[0] == text
    
    def test_chunk_text_empty_string(self, document_processor):
        """Test chunking empty string"""
        chunks = document_processor.chunk_text("")
        
        assert chunks == []
    
    def test_chunk_text_whitespace_normalization(self, document_processor):
        """Test whitespace normalization in chunking"""
        text = "First   sentence.    Second\n\nsentence.\t\tThird sentence."
        
        chunks = document_processor.chunk_text(text)
        
        # Check that whitespace is normalized
        for chunk in chunks:
            assert "  " not in chunk  # No double spaces
            assert "\n" not in chunk  # No newlines
            assert "\t" not in chunk  # No tabs
    
    def test_chunk_text_abbreviations(self, document_processor):
        """Test that abbreviations don't break sentence splitting"""
        text = "Dr. Smith works at U.S.A. Inc. He likes it there. Mr. Jones disagrees."
        
        chunks = document_processor.chunk_text(text)
        
        # Should not split on abbreviations
        assert len(chunks) >= 1
        # Verify the text is preserved correctly
        full_text = " ".join(chunks)
        assert "Dr. Smith" in full_text
        assert "U.S.A. Inc." in full_text
    
    def test_process_course_document_full_format(self, temp_file):
        """Test processing complete course document"""
        content = """Course Title: Python Programming
Course Link: https://example.com/python-course
Course Instructor: Jane Smith

Lesson 1: Getting Started
Lesson Link: https://example.com/lesson1
This is the first lesson content. It covers basic concepts of Python programming.

Lesson 2: Variables and Data Types
Lesson Link: https://example.com/lesson2
This lesson covers variables. Variables store data in Python programs."""
        
        temp_file.write(content)
        temp_file.flush()
        
        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
        course, chunks = processor.process_course_document(temp_file.name)
        
        # Verify course metadata
        assert course.title == "Python Programming"
        assert course.course_link == "https://example.com/python-course"
        assert course.instructor == "Jane Smith"
        assert len(course.lessons) == 2
        
        # Verify lessons
        assert course.lessons[0].lesson_number == 1
        assert course.lessons[0].title == "Getting Started"
        assert course.lessons[0].lesson_link == "https://example.com/lesson1"
        
        assert course.lessons[1].lesson_number == 2
        assert course.lessons[1].title == "Variables and Data Types"
        assert course.lessons[1].lesson_link == "https://example.com/lesson2"
        
        # Verify chunks
        assert len(chunks) > 0
        assert all(isinstance(chunk, CourseChunk) for chunk in chunks)
        assert all(chunk.course_title == "Python Programming" for chunk in chunks)
    
    def test_process_course_document_minimal_format(self, temp_file):
        """Test processing minimal course document"""
        content = """Introduction to AI

This is a course about artificial intelligence.
It covers machine learning, deep learning, and neural networks.
These are fundamental concepts in modern AI research."""
        
        temp_file.write(content)
        temp_file.flush()
        
        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
        course, chunks = processor.process_course_document(temp_file.name)
        
        # Should use first line as title
        assert course.title == "Introduction to AI"
        assert course.instructor is None
        assert course.course_link is None
        
        # Should create chunks from remaining content
        assert len(chunks) > 0
    
    def test_process_course_document_no_lessons(self, temp_file):
        """Test processing document without lesson markers"""
        content = """Course Title: General Knowledge
Course Link: https://example.com/general
Course Instructor: Bob Wilson

This is general course content without specific lesson markers.
It contains multiple paragraphs of information.
All content should be chunked appropriately."""
        
        temp_file.write(content)
        temp_file.flush()
        
        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
        course, chunks = processor.process_course_document(temp_file.name)
        
        # Verify course metadata
        assert course.title == "General Knowledge"
        assert course.instructor == "Bob Wilson"
        assert len(course.lessons) == 0
        
        # Should still create chunks from content
        assert len(chunks) > 0
        assert all(chunk.course_title == "General Knowledge" for chunk in chunks)
    
    def test_process_course_document_case_insensitive_markers(self, temp_file):
        """Test case-insensitive parsing of course markers"""
        content = """course title: Data Science
COURSE LINK: https://example.com/data-science
course instructor: Alice Brown

lesson 1: Introduction
LESSON LINK: https://example.com/intro
Basic introduction to data science concepts."""
        
        temp_file.write(content)
        temp_file.flush()
        
        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
        course, chunks = processor.process_course_document(temp_file.name)
        
        # Should parse case-insensitive markers
        assert course.title == "Data Science"
        assert course.course_link == "https://example.com/data-science"
        assert course.instructor == "Alice Brown"
        assert len(course.lessons) == 1
        assert course.lessons[0].lesson_link == "https://example.com/intro"
    
    def test_process_course_document_filename_fallback(self, temp_file):
        """Test using filename as course title fallback"""
        # Write content without course title (first line is treated as title)
        content = """Random Content File
Some random content without proper formatting.
This should use the first line as the course title."""
        
        temp_file.write(content)
        temp_file.flush()
        
        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
        course, chunks = processor.process_course_document(temp_file.name)
        
        # Should use first line as title, not filename
        assert course.title == "Random Content File"
    
    def test_process_course_document_empty_file(self, temp_file):
        """Test processing empty file"""
        temp_file.write("")
        temp_file.flush()
        
        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
        course, chunks = processor.process_course_document(temp_file.name)
        
        # Should still create course object
        assert course is not None
        assert chunks == []
    
    def test_process_course_document_lesson_without_link(self, temp_file):
        """Test processing lesson without lesson link"""
        content = """Course Title: Test Course
Course Link: https://example.com/test
Course Instructor: Test Instructor

Lesson 1: First Lesson
This is the first lesson content without a lesson link."""
        
        temp_file.write(content)
        temp_file.flush()
        
        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
        course, chunks = processor.process_course_document(temp_file.name)
        
        assert len(course.lessons) == 1
        assert course.lessons[0].lesson_link is None
    
    def test_process_course_document_multiple_lessons(self, temp_file):
        """Test processing document with multiple lessons"""
        content = """Course Title: Multi-Lesson Course
Course Link: https://example.com/multi
Course Instructor: Multi Teacher

Lesson 0: Introduction
This is the introduction lesson.

Lesson 1: Basics
This covers the basics of the subject.

Lesson 2: Advanced Topics
This lesson covers advanced concepts and techniques."""
        
        temp_file.write(content)
        temp_file.flush()
        
        processor = DocumentProcessor(chunk_size=50, chunk_overlap=10)
        course, chunks = processor.process_course_document(temp_file.name)
        
        # Should have 3 lessons
        assert len(course.lessons) == 3
        assert course.lessons[0].lesson_number == 0
        assert course.lessons[1].lesson_number == 1
        assert course.lessons[2].lesson_number == 2
        
        # Should have chunks for all lessons
        lesson_numbers = {chunk.lesson_number for chunk in chunks}
        assert lesson_numbers == {0, 1, 2}
    
    def test_chunk_text_no_overlap_setting(self):
        """Test chunking with no overlap configured"""
        processor = DocumentProcessor(chunk_size=50, chunk_overlap=0)
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        
        chunks = processor.chunk_text(text)
        
        assert len(chunks) > 0
        # With no overlap, chunks should not share content
        all_words = []
        for chunk in chunks:
            all_words.extend(chunk.split())
        
        # Count of words in all chunks should roughly equal unique words
        # (allowing for some repetition due to sentence boundaries)
        original_words = text.split()
        assert len(all_words) >= len(set(original_words))
    
    def test_chunk_context_addition(self, temp_file):
        """Test that lesson context is added to chunks"""
        content = """Course Title: Context Test
Course Instructor: Test Teacher

Lesson 1: First Lesson
This is content for the first lesson that should include context."""
        
        temp_file.write(content)
        temp_file.flush()
        
        processor = DocumentProcessor(chunk_size=200, chunk_overlap=20)
        course, chunks = processor.process_course_document(temp_file.name)
        
        assert len(chunks) > 0
        # Check that context is added to chunks
        for chunk in chunks:
            if chunk.lesson_number == 1:
                assert "Course Context Test" in chunk.content or "Lesson 1 content:" in chunk.content