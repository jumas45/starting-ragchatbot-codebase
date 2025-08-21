"""Tests for AI generator calling CourseSearchTool"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import anthropic

from ai_generator import AIGenerator
from search_tools import ToolManager, CourseSearchTool


class TestAIGeneratorToolIntegration:
    """Test AI generator integration with CourseSearchTool"""
    
    @pytest.fixture
    def mock_anthropic_response_with_tool_use(self):
        """Create a mock Anthropic response that includes tool use"""
        response = Mock()
        
        # Mock tool use content block
        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.id = "tool_123"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "test query", "course_name": "MCP"}
        
        response.content = [tool_block]
        response.stop_reason = "tool_use"
        response.usage = Mock()
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        
        return response
    
    @pytest.fixture
    def mock_anthropic_final_response(self):
        """Create a mock final response after tool execution"""
        response = Mock()
        
        text_block = Mock()
        text_block.text = "Based on the search results, here is the answer about MCP."
        
        response.content = [text_block]
        response.stop_reason = "end_turn"
        response.usage = Mock()
        response.usage.input_tokens = 150
        response.usage.output_tokens = 75
        
        return response
    
    @pytest.fixture
    def tool_manager_with_search(self, mock_vector_store):
        """Create a tool manager with search tool"""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)
        return manager
    
    def test_ai_generator_calls_search_tool(self, mock_anthropic_response_with_tool_use, 
                                          mock_anthropic_final_response, tool_manager_with_search):
        """Test that AI generator correctly calls search tool when instructed"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            # Setup mock client
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client
            
            # First call returns tool use, second call returns final response
            mock_client.messages.create.side_effect = [
                mock_anthropic_response_with_tool_use,
                mock_anthropic_final_response
            ]
            
            # Create AI generator
            ai_gen = AIGenerator("anthropic", "test-key", "claude-3-sonnet-20240229")
            
            # Get tool definitions
            tools = tool_manager_with_search.get_tool_definitions()
            
            # Execute
            result = ai_gen.generate_response(
                query="What is MCP?",
                tools=tools,
                tool_manager=tool_manager_with_search
            )
            
            # Verify
            assert result == "Based on the search results, here is the answer about MCP."
            assert mock_client.messages.create.call_count == 2
            
            # Verify first call included tools
            first_call = mock_client.messages.create.call_args_list[0]
            assert "tools" in first_call.kwargs
            assert "tool_choice" in first_call.kwargs
            
            # Verify second call was for final response (no tools)
            second_call = mock_client.messages.create.call_args_list[1]
            assert "tools" not in second_call.kwargs
    
    def test_tool_execution_called_with_correct_parameters(self, mock_anthropic_response_with_tool_use,
                                                         mock_anthropic_final_response, mock_vector_store):
        """Test that tool is executed with correct parameters from AI"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            # Setup
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client
            mock_client.messages.create.side_effect = [
                mock_anthropic_response_with_tool_use,
                mock_anthropic_final_response
            ]
            
            # Create tool manager with mocked search tool
            tool_manager = ToolManager()
            search_tool = Mock(spec=CourseSearchTool)
            search_tool.get_tool_definition.return_value = {
                "name": "search_course_content",
                "description": "Search course content",
                "input_schema": {"type": "object", "properties": {}}
            }
            search_tool.execute.return_value = "Mock search results"
            tool_manager.register_tool(search_tool)
            
            # Create AI generator
            ai_gen = AIGenerator("anthropic", "test-key", "claude-3-sonnet-20240229")
            
            # Execute
            result = ai_gen.generate_response(
                query="What is MCP?",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager
            )
            
            # Verify tool was called with correct parameters
            search_tool.execute.assert_called_once_with(
                query="test query",
                course_name="MCP"
            )
    
    def test_no_tool_call_when_no_tools_provided(self):
        """Test that no tools are called when none are provided"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            # Setup
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client
            
            # Mock direct response (no tool use)
            direct_response = Mock()
            direct_response.content = [Mock()]
            direct_response.content[0].text = "Direct answer without tools"
            direct_response.stop_reason = "end_turn"
            direct_response.usage = Mock()
            direct_response.usage.input_tokens = 50
            direct_response.usage.output_tokens = 25
            
            mock_client.messages.create.return_value = direct_response
            
            # Create AI generator
            ai_gen = AIGenerator("anthropic", "test-key", "claude-3-sonnet-20240229")
            
            # Execute without tools
            result = ai_gen.generate_response(query="What is AI?")
            
            # Verify
            assert result == "Direct answer without tools"
            assert mock_client.messages.create.call_count == 1
            
            # Verify no tools were included in the call
            call_args = mock_client.messages.create.call_args
            assert "tools" not in call_args.kwargs
    
    def test_tool_error_handling(self, mock_anthropic_response_with_tool_use, mock_anthropic_final_response):
        """Test handling of tool execution errors"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            # Setup
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client
            mock_client.messages.create.side_effect = [
                mock_anthropic_response_with_tool_use,
                mock_anthropic_final_response
            ]
            
            # Create tool manager with failing tool
            tool_manager = ToolManager()
            search_tool = Mock(spec=CourseSearchTool)
            search_tool.get_tool_definition.return_value = {
                "name": "search_course_content",
                "description": "Search course content",
                "input_schema": {"type": "object", "properties": {}}
            }
            search_tool.execute.side_effect = Exception("Tool execution failed")
            tool_manager.register_tool(search_tool)
            
            # Create AI generator
            ai_gen = AIGenerator("anthropic", "test-key", "claude-3-sonnet-20240229")
            
            # Execute - should not raise exception
            result = ai_gen.generate_response(
                query="What is MCP?",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager
            )
            
            # Should still return a response even if tool fails
            assert result == "Based on the search results, here is the answer about MCP."
    
    def test_conversation_history_included(self):
        """Test that conversation history is properly included in AI calls"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            # Setup
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client
            
            response = Mock()
            response.content = [Mock()]
            response.content[0].text = "Response with history context"
            response.stop_reason = "end_turn"
            response.usage = Mock()
            response.usage.input_tokens = 150
            response.usage.output_tokens = 50
            
            mock_client.messages.create.return_value = response
            
            # Create AI generator
            ai_gen = AIGenerator("anthropic", "test-key", "claude-3-sonnet-20240229")
            
            # Execute with conversation history
            history = "User: Previous question\nAssistant: Previous answer"
            result = ai_gen.generate_response(
                query="Follow-up question",
                conversation_history=history
            )
            
            # Verify
            call_args = mock_client.messages.create.call_args
            system_content = call_args.kwargs["system"]
            assert "Previous conversation:" in system_content
            assert history in system_content


class TestAIGeneratorConfiguration:
    """Test AI generator configuration and initialization"""
    
    def test_anthropic_provider_initialization(self):
        """Test Anthropic provider initialization"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client
            
            ai_gen = AIGenerator("anthropic", "test-api-key", "claude-3-sonnet-20240229")
            
            # Verify Anthropic client was created with correct API key
            mock_anthropic_class.assert_called_once_with(api_key="test-api-key")
    
    def test_unsupported_provider_raises_error(self):
        """Test that unsupported provider raises appropriate error"""
        with pytest.raises(ValueError) as exc_info:
            AIGenerator("unsupported_provider", "api-key", "model")
        
        assert "Unsupported LLM provider" in str(exc_info.value)
    
    def test_system_prompt_configuration(self):
        """Test that system prompt is properly configured for tool usage"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client
            
            response = Mock()
            response.content = [Mock()]
            response.content[0].text = "Test response"
            response.stop_reason = "end_turn"
            response.usage = Mock()
            response.usage.input_tokens = 100
            response.usage.output_tokens = 50
            
            mock_client.messages.create.return_value = response
            
            ai_gen = AIGenerator("anthropic", "test-key", "claude-3-sonnet-20240229")
            ai_gen.generate_response("Test query")
            
            # Verify system prompt includes tool usage instructions
            call_args = mock_client.messages.create.call_args
            system_content = call_args.kwargs["system"]
            assert "search_course_content" in system_content
            assert "get_course_outline" in system_content
            assert "Tool Usage" in system_content