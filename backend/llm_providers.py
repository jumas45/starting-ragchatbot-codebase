from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import anthropic
import google.generativeai as genai
import json


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
        return final_response.content[0].text


class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation"""
    
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
        print(f"Gemini generate_response called")
        
        # Simple prompt like our working test
        prompt = f"You are a helpful AI assistant. Please answer this question: {query}"
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini Error: {e}")
            raise e
    
    def _handle_with_tools(self, prompt: str, tools: List, tool_manager):
        """Handle tool execution with Gemini"""
        try:
            # Convert tools to Gemini function declarations
            gemini_tools = []
            for tool in tools:
                gemini_tool = {
                    "function_declarations": [{
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"]
                    }]
                }
                gemini_tools.append(gemini_tool)
            
            # Create model with tools
            model_with_tools = genai.GenerativeModel(
                self.model_name,
                tools=gemini_tools
            )
            
            # Generate response with tools
            response = model_with_tools.generate_content(
                prompt,
                generation_config=self.generation_config
            )
        except Exception as e:
            print(f"Gemini Tool Error: {e}")
            # Fall back to non-tool response
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            return response.text
        
        # Check if tools were called - fix the structure access
        if hasattr(response.candidates[0].content, 'parts'):
            function_calls = []
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call'):
                    function_calls.append(part.function_call)
            
            if function_calls:
                # Execute tool calls
                tool_results = []
                for function_call in function_calls:
                    tool_result = tool_manager.execute_tool(
                        function_call.name,
                        **dict(function_call.args)
                    )
                    tool_results.append(tool_result)
                
                # Create follow-up prompt with tool results
                follow_up_prompt = f"{prompt}\n\nTool results: {json.dumps(tool_results)}\n\nPlease provide a final response based on the tool results."
                
                # Get final response
                final_response = self.model.generate_content(
                    follow_up_prompt,
                    generation_config=self.generation_config
                )
                
                return final_response.text
        
        return response.text


def create_llm_provider(provider_type: str, api_key: str, model: str) -> LLMProvider:
    """Factory function to create LLM provider instances"""
    if provider_type.lower() == "anthropic":
        return AnthropicProvider(api_key, model)
    elif provider_type.lower() == "gemini":
        return GeminiProvider(api_key, model)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_type}")