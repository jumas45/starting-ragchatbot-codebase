import pytest
from unittest.mock import Mock, patch, MagicMock
from llm_providers import (
    LLMProvider, AnthropicProvider, GeminiProvider, create_llm_provider
)


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client"""
    client = Mock()
    response = Mock()
    response.content = [Mock(text="Test response", type="text")]
    response.stop_reason = "end_turn"
    response.usage = Mock(input_tokens=100, output_tokens=50)
    client.messages.create.return_value = response
    return client


@pytest.fixture
def mock_gemini_model():
    """Mock Gemini model"""
    model = Mock()
    response = Mock()
    response.text = "Test Gemini response"
    response.usage_metadata = Mock(prompt_token_count=100, candidates_token_count=50)
    model.generate_content.return_value = response
    return model


@pytest.fixture
def mock_tool_manager():
    """Mock tool manager"""
    manager = Mock()
    manager.execute_tool.return_value = "Tool execution result"
    return manager


class TestLLMProvider:
    """Test abstract LLMProvider base class"""
    
    def test_abstract_base_class(self):
        """Test that LLMProvider cannot be instantiated directly"""
        with pytest.raises(TypeError):
            LLMProvider()
    
    def test_abstract_method_signature(self):
        """Test that abstract method has correct signature"""
        assert hasattr(LLMProvider, 'generate_response')
        assert LLMProvider.generate_response.__isabstractmethod__


class TestAnthropicProvider:
    """Test AnthropicProvider class"""
    
    @patch('llm_providers.anthropic.Anthropic')
    def test_init(self, mock_anthropic):
        """Test AnthropicProvider initialization"""
        provider = AnthropicProvider("test_key", "test_model")
        
        assert provider.model == "test_model"
        assert provider.base_params["model"] == "test_model"
        assert provider.base_params["temperature"] == 0
        assert provider.base_params["max_tokens"] == 800
        mock_anthropic.assert_called_once_with(api_key="test_key")
    
    @patch('llm_providers.anthropic.Anthropic')
    @patch('llm_providers.session_logger')
    def test_generate_response_simple(self, mock_logger, mock_anthropic, mock_anthropic_client):
        """Test simple response generation without tools"""
        mock_anthropic.return_value = mock_anthropic_client
        
        provider = AnthropicProvider("test_key", "test_model")
        response = provider.generate_response("Test query")
        
        assert response == "Test response"
        mock_anthropic_client.messages.create.assert_called_once()
        
        # Check call parameters
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert call_args["model"] == "test_model"
        assert call_args["messages"][0]["content"] == "Test query"
        assert "system" in call_args
    
    @patch('llm_providers.anthropic.Anthropic')
    @patch('llm_providers.session_logger')
    def test_generate_response_with_history(self, mock_logger, mock_anthropic, mock_anthropic_client):
        """Test response generation with conversation history"""
        mock_anthropic.return_value = mock_anthropic_client
        
        provider = AnthropicProvider("test_key", "test_model")
        response = provider.generate_response(
            "Test query", 
            conversation_history="Previous: Hello\nAssistant: Hi there!"
        )
        
        assert response == "Test response"
        
        # Check that history is included in system prompt
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert "Previous conversation:" in call_args["system"]
        assert "Hello" in call_args["system"]
    
    @patch('llm_providers.anthropic.Anthropic')
    @patch('llm_providers.session_logger')
    def test_generate_response_with_tools(self, mock_logger, mock_anthropic, mock_tool_manager):
        """Test response generation with tools"""
        mock_anthropic_client = Mock()
        response = Mock()
        response.content = [Mock(text="Tool response", type="text")]
        response.stop_reason = "tool_use"
        response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_anthropic_client.messages.create.return_value = response
        mock_anthropic.return_value = mock_anthropic_client
        
        provider = AnthropicProvider("test_key", "test_model")
        
        tools = [{"name": "test_tool", "description": "Test tool"}]
        
        with patch.object(provider, '_handle_tool_execution', return_value="Tool handled"):
            response = provider.generate_response(
                "Test query",
                tools=tools,
                tool_manager=mock_tool_manager
            )
        
        assert response == "Tool handled"
        
        # Check that tools were added to call
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert "tools" in call_args
        assert call_args["tools"] == tools
        assert call_args["tool_choice"] == {"type": "auto"}
    
    @patch('llm_providers.anthropic.Anthropic')
    @patch('llm_providers.session_logger')
    def test_token_logging(self, mock_logger, mock_anthropic, mock_anthropic_client):
        """Test token usage logging"""
        mock_anthropic.return_value = mock_anthropic_client
        
        provider = AnthropicProvider("test_key", "test_model")
        provider.generate_response("Test query")
        
        # Check token logging
        mock_logger.token.assert_called_once()
        call_args = mock_logger.token.call_args[0]
        assert "ANTHROPIC TOKENS" in call_args[0]
        assert "Input: 100" in call_args[0]
        assert "Output: 50" in call_args[0]
    
    def test_system_prompt_content(self):
        """Test that system prompt contains expected content"""
        assert "course materials" in AnthropicProvider.SYSTEM_PROMPT.lower()
        assert "tool" in AnthropicProvider.SYSTEM_PROMPT.lower()
        assert "round" in AnthropicProvider.SYSTEM_PROMPT.lower()
    
    @patch('llm_providers.anthropic.Anthropic')
    @patch('llm_providers.session_logger')
    def test_execute_round_tools(self, mock_logger, mock_anthropic, mock_tool_manager):
        """Test executing tools in a round"""
        mock_anthropic.return_value = Mock()
        provider = AnthropicProvider("test_key", "test_model")
        
        # Mock response with tool use
        response = Mock()
        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.name = "test_tool"
        tool_block.id = "tool_123"
        tool_block.input = {"param": "value"}
        response.content = [tool_block]
        
        tool_results, tool_calls_made = provider._execute_round_tools(response, mock_tool_manager)
        
        assert tool_calls_made == 1
        assert len(tool_results) == 1
        assert tool_results[0]["type"] == "tool_result"
        assert tool_results[0]["tool_use_id"] == "tool_123"
        assert tool_results[0]["content"] == "Tool execution result"
        
        mock_tool_manager.execute_tool.assert_called_once_with("test_tool", param="value")
    
    @patch('llm_providers.anthropic.Anthropic')
    @patch('llm_providers.session_logger')
    def test_execute_round_tools_error_handling(self, mock_logger, mock_anthropic, mock_tool_manager):
        """Test error handling in tool execution"""
        mock_anthropic.return_value = Mock()
        provider = AnthropicProvider("test_key", "test_model")
        
        # Mock tool manager to raise exception
        mock_tool_manager.execute_tool.side_effect = Exception("Tool error")
        
        # Mock response with tool use
        response = Mock()
        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.name = "failing_tool"
        tool_block.id = "tool_456"
        tool_block.input = {}
        response.content = [tool_block]
        
        tool_results, tool_calls_made = provider._execute_round_tools(response, mock_tool_manager)
        
        assert tool_calls_made == 1
        assert len(tool_results) == 1
        assert "Error executing tool" in tool_results[0]["content"]
        
        # Should log error
        mock_logger.error.assert_called()


class TestGeminiProvider:
    """Test GeminiProvider class"""
    
    @patch('llm_providers.genai.configure')
    @patch('llm_providers.genai.GenerativeModel')
    def test_init(self, mock_model_class, mock_configure):
        """Test GeminiProvider initialization"""
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        
        provider = GeminiProvider("test_key", "test_model")
        
        mock_configure.assert_called_once_with(api_key="test_key")
        mock_model_class.assert_called_once_with("test_model")
        assert provider.model == mock_model
    
    @patch('llm_providers.genai.configure')
    @patch('llm_providers.genai.GenerativeModel')
    @patch('llm_providers.session_logger')
    def test_generate_response_simple(self, mock_logger, mock_model_class, mock_configure, mock_gemini_model):
        """Test simple Gemini response generation"""
        mock_model_class.return_value = mock_gemini_model
        
        provider = GeminiProvider("test_key", "test_model")
        response = provider.generate_response("Test query")
        
        assert response == "Test Gemini response"
        mock_gemini_model.generate_content.assert_called_once()
        
        # Check that system prompt is included
        call_args = mock_gemini_model.generate_content.call_args[0][0]
        assert "course materials" in call_args.lower()
        assert "Test query" in call_args
    
    @patch('llm_providers.genai.configure')
    @patch('llm_providers.genai.GenerativeModel')
    @patch('llm_providers.session_logger')
    def test_generate_response_with_history(self, mock_logger, mock_model_class, mock_configure, mock_gemini_model):
        """Test Gemini response generation with history"""
        mock_model_class.return_value = mock_gemini_model
        
        provider = GeminiProvider("test_key", "test_model")
        response = provider.generate_response(
            "Test query",
            conversation_history="Previous conversation"
        )
        
        assert response == "Test Gemini response"
        
        # Check that history is included in prompt
        call_args = mock_gemini_model.generate_content.call_args[0][0]
        assert "Previous conversation" in call_args
    
    @patch('llm_providers.genai.configure')
    @patch('llm_providers.genai.GenerativeModel')
    @patch('llm_providers.session_logger')
    def test_gemini_token_logging(self, mock_logger, mock_model_class, mock_configure, mock_gemini_model):
        """Test Gemini token usage logging"""
        mock_model_class.return_value = mock_gemini_model
        
        provider = GeminiProvider("test_key", "test_model")
        provider.generate_response("Test query")
        
        # Check token logging
        mock_logger.token.assert_called_once()
        call_args = mock_logger.token.call_args[0]
        assert "GEMINI TOKENS" in call_args[0]
        assert "Input: 100" in call_args[0]
        assert "Output: 50" in call_args[0]
    
    @patch('llm_providers.genai.configure')
    @patch('llm_providers.genai.GenerativeModel')
    @patch('llm_providers.session_logger')
    def test_generate_response_with_tools(self, mock_logger, mock_model_class, mock_configure, mock_tool_manager):
        """Test Gemini response generation with tools"""
        mock_gemini_model = Mock()
        mock_model_class.return_value = mock_gemini_model
        
        provider = GeminiProvider("test_key", "test_model")
        tools = [{"name": "test_tool", "description": "Test tool", "input_schema": {}}]
        
        with patch.object(provider, '_handle_with_tools', return_value="Tool handled"):
            response = provider.generate_response(
                "Test query",
                tools=tools,
                tool_manager=mock_tool_manager
            )
        
        assert response == "Tool handled"
    
    @patch('llm_providers.genai.configure')
    @patch('llm_providers.genai.GenerativeModel')
    def test_parse_gemini_function_args(self, mock_model_class, mock_configure):
        """Test parsing Gemini function arguments"""
        mock_model_class.return_value = Mock()
        provider = GeminiProvider("test_key", "test_model")
        
        # Mock function call with args
        function_call = Mock()
        function_call.args = Mock()
        
        # Test with MessageToDict
        with patch('llm_providers.MessageToDict', return_value={"param": "value"}):
            args = provider._parse_gemini_function_args(function_call)
            assert args == {"param": "value"}
    
    @patch('llm_providers.genai.configure')
    @patch('llm_providers.genai.GenerativeModel')
    def test_parse_gemini_function_args_fallback(self, mock_model_class, mock_configure):
        """Test parsing Gemini function arguments fallback method"""
        mock_model_class.return_value = Mock()
        provider = GeminiProvider("test_key", "test_model")
        
        # Mock function call
        function_call = Mock()
        function_call.args = Mock()
        
        # Mock struct fields
        string_field = Mock()
        string_field.HasField.return_value = True
        string_field.string_value = "test_value"
        
        number_field = Mock()
        number_field.HasField.side_effect = lambda field: field == "number_value"
        number_field.number_value = 42
        
        function_call.args.fields = {
            "string_param": string_field,
            "number_param": number_field
        }
        
        # Test fallback when MessageToDict fails
        with patch('llm_providers.MessageToDict', side_effect=Exception("Import failed")):
            args = provider._parse_gemini_function_args(function_call)
            assert args == {"string_param": "test_value", "number_param": 42}
    
    def test_gemini_system_prompt_content(self):
        """Test that Gemini system prompt contains expected content"""
        assert "course materials" in GeminiProvider.SYSTEM_PROMPT.lower()
        assert "tool" in GeminiProvider.SYSTEM_PROMPT.lower()
        assert "round" in GeminiProvider.SYSTEM_PROMPT.lower()


class TestLLMProviderFactory:
    """Test create_llm_provider factory function"""
    
    @patch('llm_providers.AnthropicProvider')
    def test_create_anthropic_provider(self, mock_anthropic):
        """Test creating Anthropic provider"""
        mock_instance = Mock()
        mock_anthropic.return_value = mock_instance
        
        provider = create_llm_provider("anthropic", "test_key", "test_model")
        
        assert provider == mock_instance
        mock_anthropic.assert_called_once_with("test_key", "test_model")
    
    @patch('llm_providers.GeminiProvider')
    def test_create_gemini_provider(self, mock_gemini):
        """Test creating Gemini provider"""
        mock_instance = Mock()
        mock_gemini.return_value = mock_instance
        
        provider = create_llm_provider("gemini", "test_key", "test_model")
        
        assert provider == mock_instance
        mock_gemini.assert_called_once_with("test_key", "test_model")
    
    @patch('llm_providers.AnthropicProvider')
    def test_create_anthropic_provider_case_insensitive(self, mock_anthropic):
        """Test creating Anthropic provider with different case"""
        mock_instance = Mock()
        mock_anthropic.return_value = mock_instance
        
        provider = create_llm_provider("ANTHROPIC", "test_key", "test_model")
        
        assert provider == mock_instance
        mock_anthropic.assert_called_once_with("test_key", "test_model")
    
    @patch('llm_providers.GeminiProvider')
    def test_create_gemini_provider_case_insensitive(self, mock_gemini):
        """Test creating Gemini provider with different case"""
        mock_instance = Mock()
        mock_gemini.return_value = mock_instance
        
        provider = create_llm_provider("GEMINI", "test_key", "test_model")
        
        assert provider == mock_instance
        mock_gemini.assert_called_once_with("test_key", "test_model")
    
    def test_create_unsupported_provider(self):
        """Test creating unsupported provider raises error"""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            create_llm_provider("unsupported", "test_key", "test_model")
    
    def test_create_empty_provider_type(self):
        """Test creating with empty provider type"""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            create_llm_provider("", "test_key", "test_model")


class TestIntegrationScenarios:
    """Test integration scenarios between providers and components"""
    
    @patch('llm_providers.anthropic.Anthropic')
    @patch('llm_providers.session_logger')
    @patch('llm_providers.RoundManager')
    def test_anthropic_tool_execution_flow(self, mock_round_manager, mock_logger, mock_anthropic):
        """Test complete Anthropic tool execution flow"""
        # Setup mocks
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        
        # Mock initial tool response
        initial_response = Mock()
        initial_response.stop_reason = "tool_use"
        initial_response.content = [Mock(type="tool_use", name="test_tool", id="123", input={})]
        initial_response.usage = Mock(input_tokens=100, output_tokens=50)
        
        # Mock final response
        final_response = Mock()
        final_response.content = [Mock(text="Final answer", type="text")]
        final_response.usage = Mock(input_tokens=150, output_tokens=75)
        
        mock_client.messages.create.side_effect = [initial_response, final_response]
        
        # Mock round manager
        mock_rm_instance = Mock()
        mock_rm_instance.max_rounds = 2
        mock_rm_instance._response_has_tool_calls.side_effect = [True, False]
        mock_rm_instance.start_round.return_value = 1
        mock_rm_instance.get_execution_summary.return_value = {"success": True}
        mock_rm_instance.has_errors.return_value = False
        mock_round_manager.return_value = mock_rm_instance
        
        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"
        
        provider = AnthropicProvider("test_key", "test_model")
        tools = [{"name": "test_tool", "description": "Test"}]
        
        response = provider.generate_response(
            "Test query",
            tools=tools,
            tool_manager=mock_tool_manager
        )
        
        assert response == "Final answer"
        assert mock_client.messages.create.call_count == 2
        mock_tool_manager.execute_tool.assert_called_once()
    
    @patch('llm_providers.genai.configure')
    @patch('llm_providers.genai.GenerativeModel')
    @patch('llm_providers.session_logger')
    def test_error_handling_in_providers(self, mock_logger, mock_model_class, mock_configure):
        """Test error handling in both providers"""
        # Test Anthropic error handling
        with patch('llm_providers.anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception("API Error")
            mock_anthropic.return_value = mock_client
            
            provider = AnthropicProvider("test_key", "test_model")
            
            with pytest.raises(Exception):
                provider.generate_response("Test query")
        
        # Test Gemini error handling
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("Gemini API Error")
        mock_model_class.return_value = mock_model
        
        provider = GeminiProvider("test_key", "test_model")
        
        with pytest.raises(Exception):
            provider.generate_response("Test query")