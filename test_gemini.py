#!/usr/bin/env python3
"""Test script to verify basic Gemini API functionality"""

import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini_basic():
    """Test basic Gemini API call"""
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"API Key loaded: {'Yes' if api_key else 'No'}")
    print(f"API Key (first 10 chars): {api_key[:10] if api_key else 'None'}")
    
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Test different model names
        model_names = ["gemini-1.5-flash", "gemini-pro", "gemini-1.5-pro"]
        
        for model_name in model_names:
            print(f"\nTesting model: {model_name}")
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Say hello")
                print(f"SUCCESS {model_name} works: {response.text}")
                break
            except Exception as e:
                print(f"FAILED {model_name} error: {e}")
                
    except Exception as e:
        print(f"General error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    test_gemini_basic()