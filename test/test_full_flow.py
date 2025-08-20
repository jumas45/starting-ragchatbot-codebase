#!/usr/bin/env python3
"""
Test script to demonstrate the full flow with clickable source links
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from vector_store import VectorStore
from search_tools import CourseSearchTool, ToolManager
from app import Source
import json

def test_full_flow():
    print("Testing full flow with source links...")
    
    # Initialize components
    vector_store = VectorStore("./chroma_db", "all-MiniLM-L6-v2", 3)
    search_tool = CourseSearchTool(vector_store)
    tool_manager = ToolManager()
    tool_manager.register_tool(search_tool)
    
    print("\n1. Testing tool execution...")
    result = tool_manager.execute_tool(
        "search_course_content",
        query="introduction to computer use",
        course_name="Building Towards Computer Use",
        lesson_number=0
    )
    print(f"Tool result: {result[:100]}...")
    
    print("\n2. Getting sources from tool manager...")
    sources = tool_manager.get_last_sources()
    print(f"Found {len(sources)} sources")
    
    print("\n3. Converting to API format...")
    source_models = []
    for source in sources:
        if isinstance(source, dict):
            source_models.append({
                "text": source["text"], 
                "link": source["link"]
            })
        else:
            source_models.append({
                "text": str(source), 
                "link": None
            })
    
    print("\n4. Final API response format:")
    api_response = {
        "answer": "Based on the course materials, here's what I found...",
        "sources": source_models,
        "session_id": "test_session"
    }
    
    print(json.dumps(api_response, indent=2))
    
    print("\n5. Frontend rendering simulation:")
    for i, source in enumerate(source_models):
        if source["link"]:
            print(f"Source {i+1}: <a href=\"{source['link']}\" target=\"_blank\" rel=\"noopener noreferrer\">{source['text']}</a>")
        else:
            print(f"Source {i+1}: {source['text']}")

if __name__ == "__main__":
    test_full_flow()