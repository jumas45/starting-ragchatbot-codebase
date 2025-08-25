#!/usr/bin/env python3
"""
Test script to verify the complete tool execution flow works
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from vector_store import VectorStore
from search_tools import CourseSearchTool, ToolManager
from config import config

def test_tool_execution_with_args():
    """Test that the tool execution works with proper arguments"""
    
    print("Testing tool execution with various argument patterns...")
    
    # Initialize components
    vector_store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, 3)
    search_tool = CourseSearchTool(vector_store)
    tool_manager = ToolManager()
    tool_manager.register_tool(search_tool)
    
    # Test cases that Gemini might call
    test_cases = [
        {"query": "Tell me about lesson 0"},
        {"query": "lesson 0", "course_name": "computer use"},
        {"query": "introduction", "lesson_number": 0},
        {"query": "computer use course lesson 0", "course_name": "Building Towards Computer Use", "lesson_number": 0}
    ]
    
    for i, args in enumerate(test_cases):
        print(f"\n=== Test Case {i+1}: {args} ===")
        try:
            result = tool_manager.execute_tool("search_course_content", **args)
            print(f"SUCCESS: {result[:100]}...")
            
            # Check if sources were generated
            sources = tool_manager.get_last_sources()
            print(f"Sources generated: {len(sources)}")
            if sources:
                for j, source in enumerate(sources[:2]):  # Show first 2 sources
                    print(f"  Source {j+1}: {source.get('text', 'N/A')}")
                    print(f"  Link: {source.get('link', 'N/A')}")
        except Exception as e:
            print(f"FAILED: {e}")

if __name__ == "__main__":
    test_tool_execution_with_args()