from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import anthropic
import google.generativeai as genai
import json
from session_logger import session_logger


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """Generate AI response with optional tool usage and conversation context"""
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation"""
    
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **One search per query maximum**
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """Generate AI response with Anthropic Claude"""
        
        # Build system content efficiently
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Log token usage
        if hasattr(response, 'usage'):
            token_msg = f"ANTHROPIC TOKENS - Input: {response.usage.input_tokens}, Output: {response.usage.output_tokens}"
            print(token_msg)
            session_logger.token(token_msg, provider="anthropic", input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)
        
        # Return direct response
        return response.content[0].text
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """Handle execution of tool calls and get follow-up response"""
        # Start with existing messages
        messages = base_params["messages"].copy()
        
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})
        
        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name, 
                    **content_block.input
                )
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })
        
        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        
        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        
        # Get final response
        final_response = self.client.messages.create(**final_params)
        
        # Log token usage for final response
        if hasattr(final_response, 'usage'):
            token_msg = f"ANTHROPIC TOKENS (final) - Input: {final_response.usage.input_tokens}, Output: {final_response.usage.output_tokens}"
            print(token_msg)
            session_logger.token(token_msg, provider="anthropic", input_tokens=final_response.usage.input_tokens, output_tokens=final_response.usage.output_tokens, stage="final")
        
        return final_response.content[0].text


class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation"""
    
    SYSTEM_PROMPT = """You are an AI assistant that MUST use the search_course_content tool for all queries about courses, lessons, or educational content.

MANDATORY TOOL USAGE: For ANY question that mentions:
- Courses, lessons, or lesson numbers
- Course content, topics, or concepts  
- Educational materials
- Specific course names or instructors

YOU MUST call the search_course_content function FIRST before responding.

If you don't find relevant content in the search results, then provide general knowledge.
"""
    
    def __init__(self, api_key: str, model: str):
        print(f"Initializing Gemini with model: {model}")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        print(f"Gemini provider initialized successfully")
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """Generate AI response with Google Gemini"""
        
        # Build system content with conversation history like Anthropic provider
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare the full prompt with system instructions
        full_prompt = f"{system_content}\n\nUser query: {query}"
        
        # Use tools if available
        print(f"Tools present: {bool(tools)}, tool_manager present: {bool(tool_manager)}")
        if tools and tool_manager:
            print(f"Gemini called with tools: {True}")
            print(f"Tools count: {len(tools)}")
            print(f"Tool names: {[tool['name'] for tool in tools]}")
            print("About to call _handle_with_tools")
            try:
                result = self._handle_with_tools(full_prompt, tools, tool_manager)
                print("_handle_with_tools returned successfully")
                return result
            except Exception as tool_error:
                print(f"Tool handling failed: {tool_error}")
                print("Falling back to non-tool response")
        
        try:
            print("Gemini called WITHOUT tools")
            response = self.model.generate_content(full_prompt)
            print(f"Gemini Response received: {type(response)}")
            
            # Log token usage
            if hasattr(response, 'usage_metadata'):
                token_msg = f"GEMINI TOKENS - Input: {response.usage_metadata.prompt_token_count}, Output: {response.usage_metadata.candidates_token_count}"
                print(token_msg)
                session_logger.token(token_msg, provider="gemini", input_tokens=response.usage_metadata.prompt_token_count, output_tokens=response.usage_metadata.candidates_token_count)
            
            return response.text
        except Exception as e:
            print(f"Gemini Error: {e}")
            raise e
    
    def _handle_with_tools(self, prompt: str, tools: List, tool_manager):
        """Handle tool execution with Gemini"""
        print("_handle_with_tools called")
        try:
            # Convert tools to Gemini function declarations format
            gemini_tools = [{
                "function_declarations": [
                    {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"]
                    } for tool in tools
                ]
            }]
            
            # Create model with tools
            model_with_tools = genai.GenerativeModel(
                self.model.model_name,
                tools=gemini_tools
            )
            
            # Generate response with tools
            response = model_with_tools.generate_content(prompt)
            print(f"Gemini response candidates: {len(response.candidates) if response.candidates else 0}")
            
            # Log token usage for initial response
            if hasattr(response, 'usage_metadata'):
                token_msg = f"GEMINI TOKENS (with tools) - Input: {response.usage_metadata.prompt_token_count}, Output: {response.usage_metadata.candidates_token_count}"
                print(token_msg)
                session_logger.token(token_msg, provider="gemini", input_tokens=response.usage_metadata.prompt_token_count, output_tokens=response.usage_metadata.candidates_token_count, stage="with_tools")
            
            # Check if tools were called
            if response.candidates and response.candidates[0].content.parts:
                function_calls = []
                print(f"Response parts: {len(response.candidates[0].content.parts)}")
                for part in response.candidates[0].content.parts:
                    print(f"Part type: {type(part)}, has function_call: {hasattr(part, 'function_call')}")
                    if hasattr(part, 'function_call'):
                        function_calls.append(part.function_call)
                
                print(f"Found {len(function_calls)} function calls")
                if function_calls:
                    print(f"Gemini is calling {len(function_calls)} tool(s)")
                    print(f"About to start tool execution loop")
                    # Execute tool calls
                    tool_results = []
                    for function_call in function_calls:
                        print(f"=== PROCESSING FUNCTION CALL ===")
                        print(f"Calling tool: {function_call.name}")
                        print(f"Raw function_call: {function_call}")
                        print(f"function_call.args type: {type(function_call.args)}")
                        print(f"function_call.args: {function_call.args}")
                        
                        # Convert Gemini function arguments properly
                        try:
                            # Gemini function_call.args is a google.protobuf.struct_pb2.Struct
                            # The correct way to access it is through the fields attribute
                            args_dict = {}
                            if hasattr(function_call, 'args') and function_call.args:
                                # Convert protobuf Struct to Python dict
                                import json
                                from google.protobuf.json_format import MessageToDict
                                args_dict = MessageToDict(function_call.args)
                                print(f"Parsed args using MessageToDict: {args_dict}")
                            
                            # If that fails, try the direct approach
                            if not args_dict and hasattr(function_call, 'args'):
                                try:
                                    # Alternative: iterate through the struct fields
                                    for key, value in function_call.args.fields.items():
                                        if value.HasField('string_value'):
                                            args_dict[key] = value.string_value
                                        elif value.HasField('number_value'):
                                            args_dict[key] = value.number_value
                                        elif value.HasField('bool_value'):
                                            args_dict[key] = value.bool_value
                                    print(f"Parsed args using field iteration: {args_dict}")
                                except Exception as field_error:
                                    print(f"Field iteration failed: {field_error}")
                            
                            print(f"Final tool args dict: {args_dict}")
                        except Exception as dict_error:
                            print(f"Error converting args to dict: {dict_error}")
                            # Intelligent fallback: extract query from the original prompt
                            user_query_part = prompt.split("User query: ")[-1] if "User query: " in prompt else "lesson 0"
                            
                            # Create a reasonable default based on the user query
                            args_dict = {"query": user_query_part}
                            
                            # Try to extract course name and lesson number from the query
                            if "lesson" in user_query_part.lower():
                                # Extract lesson number if mentioned
                                import re
                                lesson_match = re.search(r'lesson\s+(\d+)', user_query_part.lower())
                                if lesson_match:
                                    args_dict["lesson_number"] = int(lesson_match.group(1))
                            
                            # Extract course name if mentioned
                            for course_keyword in ["computer use", "anthropic", "mcp", "retrieval", "chroma"]:
                                if course_keyword.lower() in user_query_part.lower():
                                    args_dict["course_name"] = course_keyword
                                    break
                            
                            print(f"Intelligent fallback args: {args_dict}")
                        
                        # Try calling the tool
                        try:
                            print(f"About to call tool_manager.execute_tool with: {function_call.name}, {args_dict}")
                            tool_result = tool_manager.execute_tool(
                                function_call.name,
                                **args_dict
                            )
                            print(f"Tool executed successfully, result: {tool_result[:100]}...")
                        except Exception as tool_exec_error:
                            print(f"Tool execution error: {tool_exec_error}")
                            tool_result = f"Error executing tool: {tool_exec_error}"
                        tool_results.append(tool_result)
                    
                    # Create follow-up prompt with tool results
                    follow_up_prompt = f"{prompt}\n\nTool results: {'; '.join(tool_results)}\n\nPlease provide a comprehensive response based on the search results above."
                    
                    # Get final response without tools
                    final_response = self.model.generate_content(follow_up_prompt)
                    
                    # Log token usage for final response
                    if hasattr(final_response, 'usage_metadata'):
                        token_msg = f"GEMINI TOKENS (final) - Input: {final_response.usage_metadata.prompt_token_count}, Output: {final_response.usage_metadata.candidates_token_count}"
                        print(token_msg)
                        session_logger.token(token_msg, provider="gemini", input_tokens=final_response.usage_metadata.prompt_token_count, output_tokens=final_response.usage_metadata.candidates_token_count, stage="final")
                    
                    return final_response.text
            
            # No tools called, return original response
            return response.text
            
        except Exception as e:
            print(f"Gemini Tool Error: {e}")
            # Fall back to non-tool response
            try:
                response = self.model.generate_content(prompt)
                
                # Log token usage for fallback response
                if hasattr(response, 'usage_metadata'):
                    token_msg = f"GEMINI TOKENS (fallback) - Input: {response.usage_metadata.prompt_token_count}, Output: {response.usage_metadata.candidates_token_count}"
                    print(token_msg)
                    session_logger.token(token_msg, provider="gemini", input_tokens=response.usage_metadata.prompt_token_count, output_tokens=response.usage_metadata.candidates_token_count, stage="fallback")
                
                return response.text
            except Exception as fallback_error:
                print(f"Gemini Fallback Error: {fallback_error}")
                return f"Error generating response: {fallback_error}"


def create_llm_provider(provider_type: str, api_key: str, model: str) -> LLMProvider:
    """Factory function to create LLM provider instances"""
    if provider_type.lower() == "anthropic":
        return AnthropicProvider(api_key, model)
    elif provider_type.lower() == "gemini":
        return GeminiProvider(api_key, model)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_type}")