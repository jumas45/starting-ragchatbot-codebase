import pytest
from fastapi.testclient import TestClient
from fastapi import status

class TestRootEndpoint:
    """Test the root endpoint /"""
    
    @pytest.mark.api
    def test_root_endpoint_success(self, client):
        """Test successful root endpoint response"""
        response = client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "RAG System API"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "/api/query" in data["endpoints"]
        assert "/api/courses" in data["endpoints"]
        assert "/" in data["endpoints"]

class TestQueryEndpoint:
    """Test the /api/query endpoint"""
    
    @pytest.mark.api
    def test_query_endpoint_success(self, client, sample_query_request):
        """Test successful query processing"""
        response = client.post("/api/query", json=sample_query_request)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "confidence" in data
        
        # Verify response content
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["confidence"], float)
        assert 0.0 <= data["confidence"] <= 1.0
        
        # Verify the query is referenced in the answer
        assert sample_query_request["query"] in data["answer"]
    
    @pytest.mark.api
    def test_query_endpoint_with_context(self, client):
        """Test query endpoint with context"""
        request_data = {
            "query": "Explain neural networks",
            "context": "Machine learning course material"
        }
        
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "neural networks" in data["answer"].lower()
    
    @pytest.mark.api
    def test_query_endpoint_empty_query(self, client, empty_query_request):
        """Test query endpoint with empty query"""
        response = client.post("/api/query", json=empty_query_request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "empty" in data["detail"].lower()
    
    @pytest.mark.api
    def test_query_endpoint_whitespace_only(self, client):
        """Test query endpoint with whitespace-only query"""
        request_data = {"query": "   ", "context": None}
        
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "empty" in data["detail"].lower()
    
    @pytest.mark.api
    def test_query_endpoint_missing_query_field(self, client):
        """Test query endpoint with missing query field"""
        request_data = {"context": "Some context"}
        
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.api
    def test_query_endpoint_invalid_json(self, client):
        """Test query endpoint with invalid JSON"""
        response = client.post(
            "/api/query",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

class TestCoursesEndpoint:
    """Test the /api/courses endpoints"""
    
    @pytest.mark.api
    def test_get_all_courses(self, client, sample_courses):
        """Test getting all courses"""
        response = client.get("/api/courses")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == len(sample_courses)
        
        # Verify course structure
        for course in data:
            assert "id" in course
            assert "title" in course
            assert "description" in course
            assert "instructor" in course
            assert isinstance(course["id"], int)
            assert isinstance(course["title"], str)
            assert isinstance(course["description"], str)
            assert isinstance(course["instructor"], str)
    
    @pytest.mark.api
    def test_get_specific_course_success(self, client, valid_course_id):
        """Test getting a specific course that exists"""
        response = client.get(f"/api/courses/{valid_course_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == valid_course_id
        assert "title" in data
        assert "description" in data
        assert "instructor" in data
    
    @pytest.mark.api
    def test_get_specific_course_not_found(self, client, invalid_course_id):
        """Test getting a course that doesn't exist"""
        response = client.get(f"/api/courses/{invalid_course_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    @pytest.mark.api
    def test_get_course_invalid_id_format(self, client):
        """Test getting a course with invalid ID format"""
        response = client.get("/api/courses/invalid-id")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

class TestAPIIntegration:
    """Integration tests for the API"""
    
    @pytest.mark.integration
    def test_api_workflow(self, client):
        """Test a typical API workflow"""
        # First, check the root endpoint
        root_response = client.get("/")
        assert root_response.status_code == status.HTTP_200_OK
        
        # Then, get courses
        courses_response = client.get("/api/courses")
        assert courses_response.status_code == status.HTTP_200_OK
        courses = courses_response.json()
        assert len(courses) > 0
        
        # Get a specific course
        course_id = courses[0]["id"]
        course_response = client.get(f"/api/courses/{course_id}")
        assert course_response.status_code == status.HTTP_200_OK
        
        # Make a query related to the course
        query_data = {
            "query": f"Tell me about {courses[0]['title']}",
            "context": "Course information request"
        }
        query_response = client.post("/api/query", json=query_data)
        assert query_response.status_code == status.HTTP_200_OK
        
        query_result = query_response.json()
        assert courses[0]["title"].lower() in query_result["answer"].lower()
    
    @pytest.mark.integration
    def test_error_handling_consistency(self, client):
        """Test that error responses are consistent across endpoints"""
        # Test 404 responses
        not_found_response = client.get("/api/courses/999")
        assert not_found_response.status_code == status.HTTP_404_NOT_FOUND
        assert "detail" in not_found_response.json()
        
        # Test 400 responses
        bad_request_response = client.post("/api/query", json={"query": ""})
        assert bad_request_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in bad_request_response.json()
        
        # Test 422 responses
        validation_error_response = client.post("/api/query", json={})
        assert validation_error_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY