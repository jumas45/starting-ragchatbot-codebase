import pytest
import tempfile
import shutil
import os
from unittest.mock import patch, Mock
from vector_store import VectorStore, SearchResults
from models import Course, Lesson, CourseChunk


@pytest.fixture
def temp_chroma_path():
    """Create temporary directory for ChromaDB"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def vector_store(temp_chroma_path):
    """Create VectorStore instance for testing"""
    return VectorStore(
        chroma_path=temp_chroma_path,
        embedding_model="all-MiniLM-L6-v2",
        max_results=5
    )


@pytest.fixture
def sample_course():
    """Create sample course for testing"""
    lessons = [
        Lesson(lesson_number=1, title="Introduction", lesson_link="http://example.com/lesson1"),
        Lesson(lesson_number=2, title="Advanced Topics", lesson_link="http://example.com/lesson2")
    ]
    return Course(
        title="Python Basics",
        course_link="http://example.com/course",
        instructor="John Doe",
        lessons=lessons
    )


@pytest.fixture
def sample_chunks():
    """Create sample course chunks for testing"""
    return [
        CourseChunk(
            content="Python is a programming language",
            course_title="Python Basics",
            lesson_number=1,
            chunk_index=0
        ),
        CourseChunk(
            content="Variables store data in memory",
            course_title="Python Basics",
            lesson_number=1,
            chunk_index=1
        ),
        CourseChunk(
            content="Functions help organize code",
            course_title="Python Basics",
            lesson_number=2,
            chunk_index=2
        )
    ]


class TestSearchResults:
    """Test SearchResults class"""
    
    def test_from_chroma_with_results(self):
        """Test creating SearchResults from ChromaDB results"""
        chroma_results = {
            'documents': [['doc1', 'doc2']],
            'metadatas': [[{'key': 'value1'}, {'key': 'value2'}]],
            'distances': [[0.1, 0.2]]
        }
        
        results = SearchResults.from_chroma(chroma_results)
        
        assert results.documents == ['doc1', 'doc2']
        assert results.metadata == [{'key': 'value1'}, {'key': 'value2'}]
        assert results.distances == [0.1, 0.2]
        assert results.error is None
    
    def test_from_chroma_empty_results(self):
        """Test creating SearchResults from empty ChromaDB results"""
        chroma_results = {
            'documents': [],
            'metadatas': [],
            'distances': []
        }
        
        results = SearchResults.from_chroma(chroma_results)
        
        assert results.documents == []
        assert results.metadata == []
        assert results.distances == []
        assert results.error is None
    
    def test_empty_with_error(self):
        """Test creating empty SearchResults with error"""
        results = SearchResults.empty("Test error")
        
        assert results.documents == []
        assert results.metadata == []
        assert results.distances == []
        assert results.error == "Test error"
    
    def test_is_empty(self):
        """Test is_empty method"""
        empty_results = SearchResults([], [], [])
        non_empty_results = SearchResults(['doc'], [{}], [0.1])
        
        assert empty_results.is_empty() is True
        assert non_empty_results.is_empty() is False


class TestVectorStore:
    """Test VectorStore class"""
    
    def test_init(self, temp_chroma_path):
        """Test VectorStore initialization"""
        vs = VectorStore(
            chroma_path=temp_chroma_path,
            embedding_model="all-MiniLM-L6-v2",
            max_results=10
        )
        
        assert vs.max_results == 10
        assert vs.client is not None
        assert vs.embedding_function is not None
        assert vs.course_catalog is not None
        assert vs.course_content is not None
    
    def test_add_course_metadata(self, vector_store, sample_course):
        """Test adding course metadata"""
        vector_store.add_course_metadata(sample_course)
        
        # Verify course was added
        existing_titles = vector_store.get_existing_course_titles()
        assert "Python Basics" in existing_titles
        
        # Verify metadata
        metadata = vector_store.get_all_courses_metadata()
        assert len(metadata) == 1
        assert metadata[0]['title'] == "Python Basics"
        assert metadata[0]['instructor'] == "John Doe"
        assert metadata[0]['lesson_count'] == 2
    
    def test_add_course_content(self, vector_store, sample_chunks):
        """Test adding course content chunks"""
        vector_store.add_course_content(sample_chunks)
        
        # Test search to verify content was added
        results = vector_store.search("Python programming")
        assert not results.is_empty()
        assert len(results.documents) > 0
    
    def test_add_empty_chunks(self, vector_store):
        """Test adding empty chunks list"""
        # Should not raise an error
        vector_store.add_course_content([])
    
    def test_search_without_filters(self, vector_store, sample_chunks):
        """Test search without any filters"""
        vector_store.add_course_content(sample_chunks)
        
        results = vector_store.search("Python")
        
        assert not results.is_empty()
        assert len(results.documents) > 0
    
    def test_search_with_course_filter(self, vector_store, sample_course, sample_chunks):
        """Test search with course name filter"""
        vector_store.add_course_metadata(sample_course)
        vector_store.add_course_content(sample_chunks)
        
        results = vector_store.search("programming", course_name="Python Basics")
        
        assert not results.is_empty()
    
    def test_search_with_lesson_filter(self, vector_store, sample_chunks):
        """Test search with lesson number filter"""
        vector_store.add_course_content(sample_chunks)
        
        results = vector_store.search("Variables", lesson_number=1)
        
        assert not results.is_empty()
        for metadata in results.metadata:
            assert metadata['lesson_number'] == 1
    
    def test_search_with_both_filters(self, vector_store, sample_course, sample_chunks):
        """Test search with both course and lesson filters"""
        vector_store.add_course_metadata(sample_course)
        vector_store.add_course_content(sample_chunks)
        
        results = vector_store.search("Variables", course_name="Python Basics", lesson_number=1)
        
        assert not results.is_empty()
        for metadata in results.metadata:
            assert metadata['lesson_number'] == 1
    
    def test_search_nonexistent_course(self, vector_store, sample_chunks):
        """Test search with nonexistent course name"""
        vector_store.add_course_content(sample_chunks)
        
        results = vector_store.search("test", course_name="Nonexistent Course")
        
        assert results.is_empty()
        assert "No course found matching" in results.error
    
    def test_search_with_limit(self, vector_store, sample_chunks):
        """Test search with custom limit"""
        vector_store.add_course_content(sample_chunks)
        
        results = vector_store.search("Python", limit=2)
        
        assert not results.is_empty()
        assert len(results.documents) <= 2
    
    @patch('vector_store.VectorStore._resolve_course_name')
    def test_search_course_resolution_failure(self, mock_resolve, vector_store):
        """Test search when course name resolution fails"""
        mock_resolve.return_value = None
        
        results = vector_store.search("test", course_name="Some Course")
        
        assert results.is_empty()
        assert "No course found matching" in results.error
    
    def test_resolve_course_name_success(self, vector_store, sample_course):
        """Test successful course name resolution"""
        vector_store.add_course_metadata(sample_course)
        
        resolved_title = vector_store._resolve_course_name("Python Basics")
        
        assert resolved_title == "Python Basics"
    
    def test_resolve_course_name_partial_match(self, vector_store, sample_course):
        """Test course name resolution with partial match"""
        vector_store.add_course_metadata(sample_course)
        
        resolved_title = vector_store._resolve_course_name("Python")
        
        assert resolved_title == "Python Basics"
    
    def test_resolve_course_name_no_match(self, vector_store):
        """Test course name resolution with no match"""
        resolved_title = vector_store._resolve_course_name("Nonexistent")
        
        assert resolved_title is None
    
    def test_build_filter_no_params(self, vector_store):
        """Test filter building with no parameters"""
        filter_dict = vector_store._build_filter(None, None)
        
        assert filter_dict is None
    
    def test_build_filter_course_only(self, vector_store):
        """Test filter building with course title only"""
        filter_dict = vector_store._build_filter("Test Course", None)
        
        assert filter_dict == {"course_title": "Test Course"}
    
    def test_build_filter_lesson_only(self, vector_store):
        """Test filter building with lesson number only"""
        filter_dict = vector_store._build_filter(None, 1)
        
        assert filter_dict == {"lesson_number": 1}
    
    def test_build_filter_both_params(self, vector_store):
        """Test filter building with both parameters"""
        filter_dict = vector_store._build_filter("Test Course", 1)
        
        expected = {"$and": [
            {"course_title": "Test Course"},
            {"lesson_number": 1}
        ]}
        assert filter_dict == expected
    
    def test_clear_all_data(self, vector_store, sample_course, sample_chunks):
        """Test clearing all data"""
        vector_store.add_course_metadata(sample_course)
        vector_store.add_course_content(sample_chunks)
        
        # Verify data exists
        assert vector_store.get_course_count() > 0
        
        # Clear data
        vector_store.clear_all_data()
        
        # Verify data is cleared
        assert vector_store.get_course_count() == 0
        assert vector_store.get_existing_course_titles() == []
    
    def test_get_existing_course_titles(self, vector_store, sample_course):
        """Test getting existing course titles"""
        assert vector_store.get_existing_course_titles() == []
        
        vector_store.add_course_metadata(sample_course)
        titles = vector_store.get_existing_course_titles()
        
        assert "Python Basics" in titles
    
    def test_get_course_count(self, vector_store, sample_course):
        """Test getting course count"""
        assert vector_store.get_course_count() == 0
        
        vector_store.add_course_metadata(sample_course)
        
        assert vector_store.get_course_count() == 1
    
    def test_get_all_courses_metadata(self, vector_store, sample_course):
        """Test getting all courses metadata"""
        assert vector_store.get_all_courses_metadata() == []
        
        vector_store.add_course_metadata(sample_course)
        metadata = vector_store.get_all_courses_metadata()
        
        assert len(metadata) == 1
        assert metadata[0]['title'] == "Python Basics"
        assert 'lessons' in metadata[0]
        assert len(metadata[0]['lessons']) == 2
    
    def test_get_course_link(self, vector_store, sample_course):
        """Test getting course link"""
        vector_store.add_course_metadata(sample_course)
        
        link = vector_store.get_course_link("Python Basics")
        
        assert link == "http://example.com/course"
    
    def test_get_course_link_nonexistent(self, vector_store):
        """Test getting course link for nonexistent course"""
        link = vector_store.get_course_link("Nonexistent")
        
        assert link is None
    
    def test_get_lesson_link(self, vector_store, sample_course):
        """Test getting lesson link"""
        vector_store.add_course_metadata(sample_course)
        
        link = vector_store.get_lesson_link("Python Basics", 1)
        
        assert link == "http://example.com/lesson1"
    
    def test_get_lesson_link_nonexistent_course(self, vector_store):
        """Test getting lesson link for nonexistent course"""
        link = vector_store.get_lesson_link("Nonexistent", 1)
        
        assert link is None
    
    def test_get_lesson_link_nonexistent_lesson(self, vector_store, sample_course):
        """Test getting lesson link for nonexistent lesson"""
        vector_store.add_course_metadata(sample_course)
        
        link = vector_store.get_lesson_link("Python Basics", 999)
        
        assert link is None
    
    def test_search_exception_handling(self, vector_store):
        """Test search exception handling"""
        # Mock the course_content collection to raise an exception
        mock_collection = Mock()
        mock_collection.query.side_effect = Exception("Database error")
        vector_store.course_content = mock_collection
        
        results = vector_store.search("test query")
        
        assert results.is_empty()
        assert "Search error" in results.error
    
    def test_resolve_course_name_exception_handling(self, vector_store):
        """Test course name resolution exception handling"""
        # Mock the course_catalog collection to raise an exception
        mock_collection = Mock()
        mock_collection.query.side_effect = Exception("Database error")
        vector_store.course_catalog = mock_collection
        
        resolved_title = vector_store._resolve_course_name("test")
        
        assert resolved_title is None
    
    def test_get_course_count_exception_handling(self, vector_store):
        """Test course count exception handling"""
        # Mock the course_catalog collection to raise an exception
        mock_collection = Mock()
        mock_collection.get.side_effect = Exception("Database error")
        vector_store.course_catalog = mock_collection
        
        count = vector_store.get_course_count()
        
        assert count == 0
    
    def test_get_all_courses_metadata_exception_handling(self, vector_store):
        """Test courses metadata exception handling"""
        # Mock the course_catalog collection to raise an exception
        mock_collection = Mock()
        mock_collection.get.side_effect = Exception("Database error")
        vector_store.course_catalog = mock_collection
        
        metadata = vector_store.get_all_courses_metadata()
        
        assert metadata == []