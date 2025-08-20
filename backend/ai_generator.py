from typing import List, Optional, Dict, Any
from llm_providers import create_llm_provider, LLMProvider

class AIGenerator:
    """Handles interactions with LLM APIs for generating responses"""
    
    def __init__(self, provider_type: str, api_key: str, model: str):
        self.provider: LLMProvider = create_llm_provider(provider_type, api_key, model)
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        return self.provider.generate_response(query, conversation_history, tools, tool_manager)