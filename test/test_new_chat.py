#!/usr/bin/env python3
"""
Test script to verify the new chat functionality works correctly
"""

import requests
import json

def test_new_chat_flow():
    """Test that multiple new chats create separate sessions"""
    
    base_url = "http://localhost:8000"
    
    print("Testing new chat functionality...")
    
    # Test 1: Create first chat session
    print("\n=== Test 1: First Chat Session ===")
    response1 = requests.post(f"{base_url}/api/query", json={
        "query": "Hello, this is my first message",
        "session_id": None  # No session ID - should create new one
    })
    
    if response1.status_code == 200:
        data1 = response1.json()
        session1 = data1.get("session_id")
        print(f"SUCCESS: First session created: {session1}")
        print(f"  Response: {data1.get('answer', '')[:50]}...")
    else:
        print(f"FAILED: First request failed: {response1.status_code}")
        return
    
    # Test 2: Continue first session
    print("\n=== Test 2: Continue First Session ===")
    response2 = requests.post(f"{base_url}/api/query", json={
        "query": "This is my second message in the same session",
        "session_id": session1
    })
    
    if response2.status_code == 200:
        data2 = response2.json()
        session2 = data2.get("session_id")
        print(f"SUCCESS: Continued session: {session2}")
        print(f"  Same session: {session1 == session2}")
    else:
        print(f"FAILED: Second request failed: {response2.status_code}")
        return
    
    # Test 3: Create new chat session (simulating NEW CHAT button)
    print("\n=== Test 3: New Chat Session (NULL session_id) ===")
    response3 = requests.post(f"{base_url}/api/query", json={
        "query": "This should be a new chat session",
        "session_id": None  # Simulating frontend setting currentSessionId = null
    })
    
    if response3.status_code == 200:
        data3 = response3.json()
        session3 = data3.get("session_id")
        print(f"SUCCESS: New session created: {session3}")
        print(f"  Different from first: {session1 != session3}")
        print(f"  Response: {data3.get('answer', '')[:50]}...")
    else:
        print(f"FAILED: Third request failed: {response3.status_code}")
        return
    
    print("\n=== Summary ===")
    print(f"Session 1: {session1}")
    print(f"Session 2: {session2} (should be same as Session 1)")
    print(f"Session 3: {session3} (should be different from Session 1)")
    print(f"New chat working: {session1 != session3 and session1 == session2}")

if __name__ == "__main__":
    test_new_chat_flow()