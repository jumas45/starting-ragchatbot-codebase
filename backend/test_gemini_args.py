#!/usr/bin/env python3
"""
Test script to verify Gemini argument parsing fix
"""

import json
from google.protobuf.struct_pb2 import Struct
from google.protobuf.json_format import MessageToDict

def test_gemini_argument_parsing():
    """Test how to properly parse Gemini function arguments"""
    
    print("Testing Gemini argument parsing...")
    
    # Create a mock Struct like Gemini would provide
    mock_args = Struct()
    mock_args.update({
        "query": "Tell me about lesson 0",
        "course_name": "Building Towards Computer Use",
        "lesson_number": 0
    })
    
    print(f"Mock args struct: {mock_args}")
    print(f"Mock args type: {type(mock_args)}")
    
    # Test Method 1: MessageToDict
    try:
        args_dict_1 = MessageToDict(mock_args)
        print(f"Method 1 (MessageToDict): {args_dict_1}")
    except Exception as e:
        print(f"Method 1 failed: {e}")
    
    # Test Method 2: Field iteration
    try:
        args_dict_2 = {}
        for key, value in mock_args.fields.items():
            if value.HasField('string_value'):
                args_dict_2[key] = value.string_value
            elif value.HasField('number_value'):
                args_dict_2[key] = int(value.number_value)
            elif value.HasField('bool_value'):
                args_dict_2[key] = value.bool_value
        print(f"Method 2 (field iteration): {args_dict_2}")
    except Exception as e:
        print(f"Method 2 failed: {e}")
    
    # Test Method 3: Direct dict conversion
    try:
        args_dict_3 = dict(mock_args)
        print(f"Method 3 (direct dict): {args_dict_3}")
    except Exception as e:
        print(f"Method 3 failed: {e}")

if __name__ == "__main__":
    test_gemini_argument_parsing()