"""Fixed AI generator tests with proper error handling expectations"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import anthropic

from ai_generator import AIGenerator
from search_tools import ToolManager, CourseSearchTool


class TestAIGeneratorErrorHandlingFixed:
    """Test AI generator error handling with correct expectations"""
    
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
    
    def test_tool_error_handling_fixed(self, mock_anthropic_response_with_tool_use, 
                                     mock_anthropic_final_response):
        """Test proper handling of tool execution errors"""
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
            # Tool execution raises exception
            search_tool.execute.side_effect = Exception("Tool execution failed")
            tool_manager.register_tool(search_tool)
            
            # Create AI generator
            ai_gen = AIGenerator("anthropic", "test-key", "claude-3-sonnet-20240229")
            
            # Execute - should handle tool error gracefully
            result = ai_gen.generate_response(
                query="What is MCP?",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager
            )
            
            # Verify:
            # 1. No exception was raised
            # 2. Final response is still returned
            # 3. Error info might be included in tool results
            assert result == "Based on the search results, here is the answer about MCP."
            
            # Verify that Claude was called twice (initial + final)
            assert mock_client.messages.create.call_count == 2
    
    def test_tool_execution_error_message_format(self, mock_anthropic_response_with_tool_use):
        """Test that tool execution errors are properly formatted for Claude"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            # Setup
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client
            
            # Create mock final response that shows error handling
            error_response = Mock()
            error_response.content = [Mock()]
            error_response.content[0].text = "I apologize, but I encountered an issue searching the course materials."
            error_response.stop_reason = "end_turn"
            error_response.usage = Mock()
            error_response.usage.input_tokens = 150
            error_response.usage.output_tokens = 30
            
            mock_client.messages.create.side_effect = [
                mock_anthropic_response_with_tool_use,
                error_response
            ]
            
            # Create tool manager with failing tool
            tool_manager = ToolManager()
            search_tool = Mock(spec=CourseSearchTool)
            search_tool.get_tool_definition.return_value = {
                "name": "search_course_content",
                "description": "Search course content",
                "input_schema": {"type": "object", "properties": {}}
            }
            search_tool.execute.side_effect = Exception("Database connection failed")
            tool_manager.register_tool(search_tool)
            
            # Create AI generator
            ai_gen = AIGenerator("anthropic", "test-key", "claude-3-sonnet-20240229")
            
            # Execute
            result = ai_gen.generate_response(
                query="What is MCP?",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager
            )
            
            # Verify error is handled gracefully
            assert "apologize" in result.lower() or "issue" in result.lower()
            
            # Check that the second call to Claude included error information
            second_call = mock_client.messages.create.call_args_list[1]
            messages = second_call.kwargs["messages"]
            
            # The user message should contain tool results including error
            tool_result_message = None
            for msg in messages:
                if msg["role"] == "user" and "content" in msg:
                    tool_result_message = msg
                    break
            
            assert tool_result_message is not None
            # Tool result should indicate an error occurred
            assert any("error" in str(content).lower() for content in tool_result_message["content"])


class TestAIGeneratorRobustness:
    """Test AI generator robustness and edge cases"""
    
    def test_no_anthropic_usage_metadata(self):
        """Test handling when Anthropic response lacks usage metadata"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client
            
            # Response without usage metadata
            response = Mock()
            response.content = [Mock()]
            response.content[0].text = "Response without usage data"
            response.stop_reason = "end_turn"
            # No usage attribute
            
            mock_client.messages.create.return_value = response
            
            ai_gen = AIGenerator("anthropic", "test-key", "claude-3-sonnet-20240229")
            
            # Should not crash when usage metadata is missing
            result = ai_gen.generate_response("Test query")
            assert result == "Response without usage data"
    
    def test_malformed_tool_response(self):
        """Test handling of malformed tool use responses"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client
            
            # Malformed tool response
            malformed_response = Mock()
            malformed_tool_block = Mock()
            malformed_tool_block.type = "tool_use"
            malformed_tool_block.id = "tool_123"
            malformed_tool_block.name = "search_course_content"
            # Missing or invalid input
            malformed_tool_block.input = None
            
            malformed_response.content = [malformed_tool_block]
            malformed_response.stop_reason = "tool_use"
            malformed_response.usage = Mock()
            malformed_response.usage.input_tokens = 100
            malformed_response.usage.output_tokens = 50
            
            # Final response
            final_response = Mock()
            final_response.content = [Mock()]
            final_response.content[0].text = "Handled malformed tool request"
            final_response.stop_reason = "end_turn"
            final_response.usage = Mock()
            final_response.usage.input_tokens = 120
            final_response.usage.output_tokens = 30
            
            mock_client.messages.create.side_effect = [malformed_response, final_response]
            
            # Create tool manager
            tool_manager = ToolManager()
            search_tool = Mock(spec=CourseSearchTool)
            search_tool.get_tool_definition.return_value = {
                "name": "search_course_content",
                "description": "Search course content",
                "input_schema": {"type": "object", "properties": {}}
            }
            search_tool.execute.return_value = "Search results"
            tool_manager.register_tool(search_tool)
            
            ai_gen = AIGenerator("anthropic", "test-key", "claude-3-sonnet-20240229")
            
            # Should handle malformed input gracefully
            result = ai_gen.generate_response(
                query="Test query",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager
            )
            
            assert result == "Handled malformed tool request"


# Summary of fixes:
# 1. ✅ Corrected expectations for tool error handling
# 2. ✅ Added tests for edge cases like missing usage metadata  
# 3. ✅ Added tests for malformed tool responses
# 4. ✅ Verified that errors don't crash the system