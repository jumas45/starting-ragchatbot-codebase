import pytest
from unittest.mock import Mock, patch
from round_manager import RoundManager, RoundResult


@pytest.fixture
def round_manager():
    """Create RoundManager instance for testing"""
    return RoundManager(max_rounds=3)


@pytest.fixture
def mock_anthropic_response():
    """Create mock Anthropic API response with tool calls"""
    response = Mock()
    response.content = [
        Mock(type="text"),
        Mock(type="tool_use")
    ]
    return response


@pytest.fixture
def mock_anthropic_response_no_tools():
    """Create mock Anthropic API response without tool calls"""
    response = Mock()
    response.content = [Mock(type="text")]
    return response


@pytest.fixture
def mock_gemini_response():
    """Create mock Gemini API response with tool calls"""
    response = Mock()
    candidate = Mock()
    part_with_function_call = Mock()
    part_with_function_call.function_call = Mock()
    
    # Explicitly create the content mock
    candidate.content = Mock()
    candidate.content.parts = [
        Mock(spec=['text']),
        part_with_function_call
    ]
    response.candidates = [candidate]
    return response


@pytest.fixture
def mock_gemini_response_no_tools():
    """Create mock Gemini API response without tool calls"""
    response = Mock()
    candidate = Mock()
    candidate.content = Mock()
    candidate.content.parts = [Mock(spec=['text'])]
    response.candidates = [candidate]
    return response


class TestRoundResult:
    """Test RoundResult dataclass"""
    
    def test_round_result_creation(self):
        """Test creating RoundResult instance"""
        result = RoundResult(
            round_number=1,
            tool_calls_made=2,
            tool_results=["result1", "result2"],
            api_response=Mock(),
            error=None,
            tokens_used={"input": 100, "output": 50}
        )
        
        assert result.round_number == 1
        assert result.tool_calls_made == 2
        assert result.tool_results == ["result1", "result2"]
        assert result.error is None
        assert result.tokens_used == {"input": 100, "output": 50}
    
    def test_round_result_with_error(self):
        """Test RoundResult with error"""
        result = RoundResult(
            round_number=1,
            tool_calls_made=0,
            tool_results=[],
            api_response=None,
            error="Test error"
        )
        
        assert result.error == "Test error"
        assert result.tokens_used is None


class TestRoundManager:
    """Test RoundManager class"""
    
    def test_init(self):
        """Test RoundManager initialization"""
        manager = RoundManager(max_rounds=5)
        
        assert manager.max_rounds == 5
        assert manager.current_round == 0
        assert manager.round_results == []
        assert manager.total_tokens == {"input": 0, "output": 0}
    
    def test_init_default_max_rounds(self):
        """Test RoundManager with default max_rounds"""
        manager = RoundManager()
        
        assert manager.max_rounds == 2
    
    def test_start_round(self, round_manager):
        """Test starting a new round"""
        with patch('round_manager.session_logger') as mock_logger:
            round_number = round_manager.start_round()
            
            assert round_number == 1
            assert round_manager.current_round == 1
            mock_logger.info.assert_called_once_with("Starting tool execution round 1/3")
    
    def test_start_multiple_rounds(self, round_manager):
        """Test starting multiple rounds"""
        with patch('round_manager.session_logger'):
            round1 = round_manager.start_round()
            round2 = round_manager.start_round()
            round3 = round_manager.start_round()
            
            assert round1 == 1
            assert round2 == 2
            assert round3 == 3
            assert round_manager.current_round == 3
    
    def test_should_continue_max_rounds_reached(self, round_manager, mock_anthropic_response):
        """Test should_continue when max rounds reached"""
        with patch('round_manager.session_logger') as mock_logger:
            # Simulate reaching max rounds
            round_manager.current_round = 3
            
            should_continue = round_manager.should_continue(mock_anthropic_response)
            
            assert should_continue is False
            mock_logger.info.assert_called_with("Terminating: Reached maximum rounds (3)")
    
    def test_should_continue_previous_error(self, round_manager, mock_anthropic_response):
        """Test should_continue with previous round error"""
        with patch('round_manager.session_logger') as mock_logger:
            round_manager.current_round = 1
            # Add a result with error
            error_result = RoundResult(1, 0, [], None, error="Test error")
            round_manager.round_results.append(error_result)
            
            should_continue = round_manager.should_continue(mock_anthropic_response)
            
            assert should_continue is False
            mock_logger.info.assert_called_with("Terminating: Previous round had errors")
    
    def test_should_continue_no_tool_calls(self, round_manager, mock_anthropic_response_no_tools):
        """Test should_continue with no tool calls in response"""
        with patch('round_manager.session_logger') as mock_logger:
            round_manager.current_round = 1
            
            should_continue = round_manager.should_continue(mock_anthropic_response_no_tools)
            
            assert should_continue is False
            mock_logger.info.assert_called_with("Terminating: No tool calls in response")
    
    def test_should_continue_success(self, round_manager, mock_anthropic_response):
        """Test should_continue when conditions allow continuation"""
        with patch('round_manager.session_logger') as mock_logger:
            round_manager.current_round = 1
            
            should_continue = round_manager.should_continue(mock_anthropic_response)
            
            assert should_continue is True
            mock_logger.info.assert_called_with("Continuing to round 2")
    
    def test_response_has_tool_calls_anthropic_with_tools(self, round_manager, mock_anthropic_response):
        """Test _response_has_tool_calls with Anthropic response containing tools"""
        has_tools = round_manager._response_has_tool_calls(mock_anthropic_response)
        
        assert has_tools is True
    
    def test_response_has_tool_calls_anthropic_no_tools(self, round_manager, mock_anthropic_response_no_tools):
        """Test _response_has_tool_calls with Anthropic response without tools"""
        has_tools = round_manager._response_has_tool_calls(mock_anthropic_response_no_tools)
        
        assert has_tools is False
    
    def test_response_has_tool_calls_gemini_with_tools(self, round_manager, mock_gemini_response):
        """Test _response_has_tool_calls with Gemini response containing tools"""
        has_tools = round_manager._response_has_tool_calls(mock_gemini_response)
        
        assert has_tools is True
    
    def test_response_has_tool_calls_gemini_no_tools(self, round_manager, mock_gemini_response_no_tools):
        """Test _response_has_tool_calls with Gemini response without tools"""
        has_tools = round_manager._response_has_tool_calls(mock_gemini_response_no_tools)
        
        assert has_tools is False
    
    def test_response_has_tool_calls_empty_response(self, round_manager):
        """Test _response_has_tool_calls with empty response"""
        empty_response = Mock()
        empty_response.content = []
        
        has_tools = round_manager._response_has_tool_calls(empty_response)
        
        assert has_tools is False
    
    def test_response_has_tool_calls_exception_handling(self, round_manager):
        """Test _response_has_tool_calls exception handling"""
        with patch('round_manager.session_logger') as mock_logger:
            # Response that will cause an exception when accessing content
            bad_response = Mock()
            bad_response.content = Mock(side_effect=Exception("Test error"))
            
            has_tools = round_manager._response_has_tool_calls(bad_response)
            
            assert has_tools is False
            mock_logger.error.assert_called_once()
    
    def test_record_round_result_success(self, round_manager):
        """Test recording successful round result"""
        with patch('round_manager.session_logger') as mock_logger:
            api_response = Mock()
            
            round_manager.record_round_result(
                round_number=1,
                tool_calls_made=2,
                tool_results=["result1", "result2"],
                api_response=api_response,
                tokens_used={"input": 100, "output": 50}
            )
            
            assert len(round_manager.round_results) == 1
            result = round_manager.round_results[0]
            
            assert result.round_number == 1
            assert result.tool_calls_made == 2
            assert result.tool_results == ["result1", "result2"]
            assert result.api_response == api_response
            assert result.error is None
            assert result.tokens_used == {"input": 100, "output": 50}
            
            # Check token tracking
            assert round_manager.total_tokens == {"input": 100, "output": 50}
            
            # Check logging
            mock_logger.info.assert_called_with(
                "Round 1 completed: SUCCESS, Tools: 2, Results: 2"
            )
    
    def test_record_round_result_with_error(self, round_manager):
        """Test recording round result with error"""
        with patch('round_manager.session_logger') as mock_logger:
            round_manager.record_round_result(
                round_number=1,
                tool_calls_made=0,
                tool_results=[],
                api_response=None,
                error="Test error"
            )
            
            result = round_manager.round_results[0]
            assert result.error == "Test error"
            
            # Check logging
            mock_logger.info.assert_called_with(
                "Round 1 completed: ERROR, Tools: 0, Results: 0"
            )
            mock_logger.error.assert_called_with("Round 1 error: Test error")
    
    def test_record_round_result_token_accumulation(self, round_manager):
        """Test token accumulation across multiple rounds"""
        round_manager.record_round_result(1, 1, ["r1"], Mock(), tokens_used={"input": 100, "output": 50})
        round_manager.record_round_result(2, 2, ["r2"], Mock(), tokens_used={"input": 200, "output": 75})
        
        assert round_manager.total_tokens == {"input": 300, "output": 125}
    
    def test_record_round_result_no_tokens(self, round_manager):
        """Test recording round result without token information"""
        round_manager.record_round_result(1, 1, ["result"], Mock())
        
        result = round_manager.round_results[0]
        assert result.tokens_used == {}
        assert round_manager.total_tokens == {"input": 0, "output": 0}
    
    def test_get_execution_summary_empty(self, round_manager):
        """Test execution summary with no rounds"""
        summary = round_manager.get_execution_summary()
        
        expected = {
            "total_rounds": 0,
            "max_rounds": 3,
            "total_tool_calls": 0,
            "total_tokens": {"input": 0, "output": 0},
            "errors": [],
            "success": True
        }
        
        assert summary == expected
    
    def test_get_execution_summary_with_data(self, round_manager):
        """Test execution summary with round data"""
        round_manager.record_round_result(1, 2, ["r1"], Mock(), tokens_used={"input": 100, "output": 50})
        round_manager.record_round_result(2, 1, ["r2"], Mock(), error="Test error")
        
        summary = round_manager.get_execution_summary()
        
        expected = {
            "total_rounds": 2,
            "max_rounds": 3,
            "total_tool_calls": 3,
            "total_tokens": {"input": 100, "output": 50},
            "errors": ["Test error"],
            "success": False
        }
        
        assert summary == expected
    
    def test_has_errors_no_errors(self, round_manager):
        """Test has_errors with no errors"""
        round_manager.record_round_result(1, 1, ["result"], Mock())
        
        assert round_manager.has_errors() is False
    
    def test_has_errors_with_errors(self, round_manager):
        """Test has_errors with errors"""
        round_manager.record_round_result(1, 0, [], None, error="Test error")
        
        assert round_manager.has_errors() is True
    
    def test_has_errors_mixed_results(self, round_manager):
        """Test has_errors with mixed success and error results"""
        round_manager.record_round_result(1, 1, ["result"], Mock())
        round_manager.record_round_result(2, 0, [], None, error="Test error")
        
        assert round_manager.has_errors() is True
    
    def test_get_last_round_result_empty(self, round_manager):
        """Test get_last_round_result with no rounds"""
        result = round_manager.get_last_round_result()
        
        assert result is None
    
    def test_get_last_round_result_single_round(self, round_manager):
        """Test get_last_round_result with single round"""
        round_manager.record_round_result(1, 1, ["result"], Mock())
        
        result = round_manager.get_last_round_result()
        
        assert result is not None
        assert result.round_number == 1
    
    def test_get_last_round_result_multiple_rounds(self, round_manager):
        """Test get_last_round_result with multiple rounds"""
        round_manager.record_round_result(1, 1, ["r1"], Mock())
        round_manager.record_round_result(2, 2, ["r2"], Mock())
        round_manager.record_round_result(3, 1, ["r3"], Mock())
        
        result = round_manager.get_last_round_result()
        
        assert result.round_number == 3
        assert result.tool_results == ["r3"]
    
    def test_complete_workflow(self, round_manager, mock_anthropic_response):
        """Test complete round management workflow"""
        with patch('round_manager.session_logger'):
            # Round 1
            round1 = round_manager.start_round()
            round_manager.record_round_result(round1, 2, ["r1", "r2"], mock_anthropic_response)
            should_continue_1 = round_manager.should_continue(mock_anthropic_response)
            
            # Round 2
            round2 = round_manager.start_round()
            round_manager.record_round_result(round2, 1, ["r3"], mock_anthropic_response)
            should_continue_2 = round_manager.should_continue(mock_anthropic_response)
            
            # Round 3 (max reached)
            round3 = round_manager.start_round()
            round_manager.record_round_result(round3, 0, [], mock_anthropic_response)
            should_continue_3 = round_manager.should_continue(mock_anthropic_response)
            
            # Verify workflow
            assert round1 == 1
            assert round2 == 2
            assert round3 == 3
            assert should_continue_1 is True
            assert should_continue_2 is True
            assert should_continue_3 is False  # Max rounds reached
            
            # Verify summary
            summary = round_manager.get_execution_summary()
            assert summary["total_rounds"] == 3
            assert summary["total_tool_calls"] == 3
            assert summary["success"] is True