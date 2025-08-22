from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import anthropic
import google.generativeai as genai
import json
from session_logger import session_logger
from round_manager import RoundManager


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
    
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Multi-Round Tool Usage:
- You can make tool calls across up to 2 rounds to handle complex queries
- **Round 1**: Exploratory searches, broad information gathering
  * Use **get_course_outline** for course structure, lesson lists, complete overviews
  * Use **search_course_content** for initial content searches
- **Round 2**: Targeted searches based on Round 1 results
  * Refine searches with specific course/lesson information from Round 1
  * Search for comparative information across courses
  * Follow up on specific topics discovered in Round 1
- **Termination**: Provide complete answers when sufficient information is available
- Synthesize tool results into accurate, fact-based responses
- If tool yields no results, state this clearly without offering alternatives

Tool Selection:
- Use **get_course_outline** when users ask for:
  * Course outlines, lesson lists, course structure, or lesson titles  
  * Words like "outline", "lessons", "structure", "list of lessons", "course content overview"
  * Complete course information including all lesson numbers and titles
- Use **search_course_content** for:
  * Specific content within lessons
  * Technical details, explanations, or concepts from course materials
  * Questions about what is taught in specific lessons

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course outline/structure questions**: Use get_course_outline tool first, then return the COMPLETE FORMATTED OUTPUT from the tool including course title, course link, instructor, and every single lesson number with its title
- **Course content questions**: Use search_course_content tool first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "based on the tool results"

All responses must be:
1. **Brief and focused** for general questions - EXCEPT for course outline questions where you must provide complete detailed information
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Complete** - For course outlines, include ALL lesson details exactly as provided by the tool
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
        """Handle sequential tool calling execution with up to 2 rounds"""
        round_manager = RoundManager(max_rounds=2)
        messages = base_params["messages"].copy()
        current_response = initial_response
        
        # Process up to 2 rounds of tool calls
        for round_number in range(1, round_manager.max_rounds + 1):
            try:
                # Check if current response has tool calls, if not, break
                if not round_manager._response_has_tool_calls(current_response):
                    session_logger.info(f"No tool calls in response, stopping at round {round_number - 1}")
                    break
                
                round_manager.start_round()
                
                # Add AI's tool use response to conversation
                messages.append({"role": "assistant", "content": current_response.content})
                
                # Execute all tool calls in current round
                tool_results, tool_calls_made = self._execute_round_tools(current_response, tool_manager)
                
                # Add tool results to conversation
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})
                
                # Prepare API call parameters
                api_params = {
                    **self.base_params,
                    "messages": messages,
                    "system": base_params["system"]
                }
                
                # Determine if this should be the final round (reached max rounds)
                is_final_round = (round_number >= round_manager.max_rounds)
                
                # Include tools only if not the final round
                if not is_final_round:
                    api_params["tools"] = base_params.get("tools", [])
                    api_params["tool_choice"] = {"type": "auto"}
                
                # Make API call for next round
                current_response = self.client.messages.create(**api_params)
                
                # Log token usage
                tokens_used = {}
                if hasattr(current_response, 'usage'):
                    tokens_used = {
                        "input": current_response.usage.input_tokens,
                        "output": current_response.usage.output_tokens
                    }
                    stage = f"round_{round_number}"
                    token_msg = f"ANTHROPIC TOKENS ({stage}) - Input: {tokens_used['input']}, Output: {tokens_used['output']}"
                    print(token_msg)
                    session_logger.token(token_msg, provider="anthropic", 
                                       input_tokens=tokens_used['input'], 
                                       output_tokens=tokens_used['output'], 
                                       stage=stage)
                
                # Record round result
                round_manager.record_round_result(
                    round_number=round_number,
                    tool_calls_made=tool_calls_made,
                    tool_results=[r["content"] for r in tool_results],
                    api_response=current_response,
                    tokens_used=tokens_used
                )
                
                # If this is the final round, break regardless of response
                if is_final_round:
                    break
                
            except Exception as e:
                error_msg = f"Error in round {round_number}: {str(e)}"
                session_logger.error(error_msg)
                
                # Record error and terminate
                round_manager.record_round_result(
                    round_number=round_number,
                    tool_calls_made=0,
                    tool_results=[],
                    api_response=None,
                    error=error_msg
                )
                break
        
        # Log execution summary
        summary = round_manager.get_execution_summary()
        session_logger.info(f"Sequential tool execution completed: {summary}")
        
        # Return final response text
        try:
            # Check if we have errors - if so, return error message
            if round_manager.has_errors():
                return "Error: Unable to generate response due to tool execution errors"
            
            return current_response.content[0].text
        except (AttributeError, IndexError):
            return "Error: Unable to generate response"
    
    def _execute_round_tools(self, response, tool_manager):
        """Execute all tool calls in the current response"""
        tool_results = []
        tool_calls_made = 0
        
        for content_block in response.content:
            if content_block.type == "tool_use":
                tool_calls_made += 1
                try:
                    # Handle case where input might be None or invalid
                    tool_input = content_block.input or {}
                    if not isinstance(tool_input, dict):
                        tool_input = {}
                    
                    tool_result = tool_manager.execute_tool(
                        content_block.name, 
                        **tool_input
                    )
                    
                    session_logger.info(f"Tool executed: {content_block.name} -> {len(str(tool_result))} chars")
                    
                except Exception as e:
                    # Handle tool execution errors gracefully
                    tool_result = f"Error executing tool {content_block.name}: {str(e)}"
                    session_logger.error(f"Tool execution failed: {content_block.name} - {str(e)}")
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })
        
        return tool_results, tool_calls_made


class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation"""
    
    SYSTEM_PROMPT = """You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Multi-Round Tool Usage:
- You can make tool calls across up to 2 rounds to handle complex queries
- **Round 1**: Exploratory searches, broad information gathering
  * Use **get_course_outline** for course structure, lesson lists, complete overviews
  * Use **search_course_content** for initial content searches
- **Round 2**: Targeted searches based on Round 1 results
  * Refine searches with specific course/lesson information from Round 1
  * Search for comparative information across courses
  * Follow up on specific topics discovered in Round 1
- **Termination**: Provide complete answers when sufficient information is available

Tool Selection:
- Use **get_course_outline** when users ask for:
  * Course outlines, lesson lists, course structure, or lesson titles  
  * Words like "outline", "lessons", "structure", "list of lessons", "course content overview"
  * Complete course information including all lesson numbers and titles
- Use **search_course_content** for:
  * Specific content within lessons
  * Technical details, explanations, or concepts from course materials
  * Questions about what is taught in specific lessons

For ANY question that mentions courses, lessons, or educational content, you MUST use the appropriate tool before responding.
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
    
    def _handle_with_tools(self, initial_prompt: str, tools: List, tool_manager):
        """Handle sequential tool calling execution with up to 2 rounds for Gemini"""
        round_manager = RoundManager(max_rounds=2)
        current_prompt = initial_prompt
        current_response = None
        
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
        
        # Initial call to get first response
        current_response = model_with_tools.generate_content(current_prompt)
        session_logger.info(f"Gemini initial response received")
        
        # Process sequential rounds
        while round_manager.should_continue(current_response):
            round_number = round_manager.start_round()
            
            try:
                # Execute all tool calls in current round
                tool_results, tool_calls_made = self._execute_gemini_round_tools(current_response, tool_manager)
                
                # Log token usage
                tokens_used = {}
                if hasattr(current_response, 'usage_metadata'):
                    tokens_used = {
                        "input": current_response.usage_metadata.prompt_token_count,
                        "output": current_response.usage_metadata.candidates_token_count
                    }
                    stage = f"round_{round_number}"
                    token_msg = f"GEMINI TOKENS ({stage}) - Input: {tokens_used['input']}, Output: {tokens_used['output']}"
                    print(token_msg)
                    session_logger.token(token_msg, provider="gemini", 
                                       input_tokens=tokens_used['input'], 
                                       output_tokens=tokens_used['output'], 
                                       stage=stage)
                
                # Build new prompt with tool results
                if tool_results:
                    tool_results_text = '; '.join(tool_results)
                    current_prompt = f"{current_prompt}\n\nTool results from Round {round_number}: {tool_results_text}"
                
                # Determine if this should be the final round (reached max rounds)
                is_final_round = (round_number >= round_manager.max_rounds)
                
                # Make next API call (with or without tools)
                if is_final_round:
                    # Final round - no tools
                    final_prompt = f"{current_prompt}\n\nPlease provide a comprehensive response based on all the search results above."
                    current_response = self.model.generate_content(final_prompt)
                else:
                    # Continue with tools for next round
                    next_prompt = f"{current_prompt}\n\nBased on the results above, do you need to search for additional information? If so, use the appropriate tools."
                    current_response = model_with_tools.generate_content(next_prompt)
                
                # Record round result
                round_manager.record_round_result(
                    round_number=round_number,
                    tool_calls_made=tool_calls_made,
                    tool_results=tool_results,
                    api_response=current_response,
                    tokens_used=tokens_used
                )
                
            except Exception as e:
                error_msg = f"Error in Gemini round {round_number}: {str(e)}"
                session_logger.error(error_msg)
                
                # Record error and terminate
                round_manager.record_round_result(
                    round_number=round_number,
                    tool_calls_made=0,
                    tool_results=[],
                    api_response=None,
                    error=error_msg
                )
                break
        
        # Log execution summary
        summary = round_manager.get_execution_summary()
        session_logger.info(f"Gemini sequential tool execution completed: {summary}")
        
        # Return final response text
        try:
            # Check if we have errors - if so, return error message
            if round_manager.has_errors():
                return "Error: Unable to generate response due to tool execution errors"
            
            return current_response.text
        except (AttributeError, IndexError):
            return "Error: Unable to generate response"
    
    def _execute_gemini_round_tools(self, response, tool_manager):
        """Execute all tool calls in the current Gemini response"""
        tool_results = []
        tool_calls_made = 0
        
        try:
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call'):
                        tool_calls_made += 1
                        function_call = part.function_call
                        
                        try:
                            # Convert Gemini function arguments to dict
                            args_dict = self._parse_gemini_function_args(function_call)
                            
                            # Execute the tool
                            tool_result = tool_manager.execute_tool(
                                function_call.name,
                                **args_dict
                            )
                            
                            tool_results.append(tool_result)
                            session_logger.info(f"Gemini tool executed: {function_call.name} -> {len(str(tool_result))} chars")
                            
                        except Exception as e:
                            error_result = f"Error executing tool {function_call.name}: {str(e)}"
                            tool_results.append(error_result)
                            session_logger.error(f"Gemini tool execution failed: {function_call.name} - {str(e)}")
        except Exception as e:
            session_logger.error(f"Error parsing Gemini tool calls: {str(e)}")
        
        return tool_results, tool_calls_made
    
    def _parse_gemini_function_args(self, function_call):
        """Parse Gemini function call arguments into a Python dict"""
        args_dict = {}
        
        try:
            if hasattr(function_call, 'args') and function_call.args:
                # Try protobuf MessageToDict conversion
                from google.protobuf.json_format import MessageToDict
                args_dict = MessageToDict(function_call.args)
        except Exception:
            try:
                # Fallback: iterate through struct fields
                if hasattr(function_call, 'args'):
                    for key, value in function_call.args.fields.items():
                        if value.HasField('string_value'):
                            args_dict[key] = value.string_value
                        elif value.HasField('number_value'):
                            args_dict[key] = value.number_value
                        elif value.HasField('bool_value'):
                            args_dict[key] = value.bool_value
            except Exception:
                # Final fallback: empty dict (tool will use defaults)
                args_dict = {}
        
        return args_dict


def create_llm_provider(provider_type: str, api_key: str, model: str) -> LLMProvider:
    """Factory function to create LLM provider instances"""
    if provider_type.lower() == "anthropic":
        return AnthropicProvider(api_key, model)
    elif provider_type.lower() == "gemini":
        return GeminiProvider(api_key, model)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_type}")