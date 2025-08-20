#!/usr/bin/env python3
"""
Test script to verify that source links are working correctly
"""

from vector_store import VectorStore
from search_tools import CourseSearchTool
from config import config

def test_source_links():
    print("Testing source link functionality...")
    
    # Initialize vector store
    vector_store = VectorStore(
        chroma_path=config.CHROMA_PATH,
        embedding_model=config.EMBEDDING_MODEL,
        max_results=config.MAX_RESULTS
    )
    
    # Initialize search tool
    search_tool = CourseSearchTool(vector_store)
    
    # Test search for a specific lesson
    print("\n1. Testing search for lesson 0...")
    try:
        result = search_tool.execute(
            query="introduction", 
            course_name="Building Towards Computer Use",
            lesson_number=0
        )
        print(f"Search result: {result[:200]}...")
        
        # Check sources
        print(f"\n2. Checking last_sources...")
        sources = search_tool.last_sources
        print(f"Sources count: {len(sources)}")
        
        for i, source in enumerate(sources):
            print(f"Source {i+1}:")
            print(f"  Text: {source.get('text', 'N/A')}")
            print(f"  Link: {source.get('link', 'N/A')}")
            
    except Exception as e:
        print(f"Error during search: {e}")
    
    # Test direct lesson link retrieval
    print("\n3. Testing direct lesson link retrieval...")
    try:
        lesson_link = vector_store.get_lesson_link("Building Towards Computer Use with Anthropic", 0)
        print(f"Lesson 0 link: {lesson_link}")
    except Exception as e:
        print(f"Error getting lesson link: {e}")

if __name__ == "__main__":
    test_source_links()