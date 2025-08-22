from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from session_logger import session_logger


@dataclass
class RoundResult:
    """Result of a tool execution round"""
    round_number: int
    tool_calls_made: int
    tool_results: List[str]
    api_response: Any
    error: Optional[str] = None
    tokens_used: Dict[str, int] = None


class RoundManager:
    """Manages sequential tool calling rounds with proper termination logic"""
    
    def __init__(self, max_rounds: int = 2):
        self.max_rounds = max_rounds
        self.current_round = 0
        self.round_results: List[RoundResult] = []
        self.total_tokens = {"input": 0, "output": 0}
        
    def start_round(self) -> int:
        """Start a new round and return the round number"""
        self.current_round += 1
        session_logger.info(f"Starting tool execution round {self.current_round}/{self.max_rounds}")
        return self.current_round
    
    def should_continue(self, response) -> bool:
        """
        Determine if we should continue to the next round
        
        Termination conditions:
        1. Reached maximum rounds (2)
        2. Response has no tool_use blocks
        3. Previous round had errors
        
        Args:
            response: API response object from LLM
            
        Returns:
            bool: True if should continue to next round
        """
        # Check if we've reached max rounds
        if self.current_round >= self.max_rounds:
            session_logger.info(f"Terminating: Reached maximum rounds ({self.max_rounds})")
            return False
        
        # Check if last round had errors
        if self.round_results and self.round_results[-1].error:
            session_logger.info("Terminating: Previous round had errors")
            return False
        
        # Check if response has tool calls
        has_tool_calls = self._response_has_tool_calls(response)
        if not has_tool_calls:
            session_logger.info("Terminating: No tool calls in response")
            return False
        
        session_logger.info(f"Continuing to round {self.current_round + 1}")
        return True
    
    def _response_has_tool_calls(self, response) -> bool:
        """Check if response contains tool use blocks"""
        try:
            # For Anthropic responses
            if hasattr(response, 'content') and response.content:
                for content_block in response.content:
                    if hasattr(content_block, 'type') and content_block.type == "tool_use":
                        return True
            
            # For Gemini responses  
            if hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'function_call'):
                                return True
            
            return False
        except Exception as e:
            session_logger.error(f"Error checking for tool calls: {e}")
            return False
    
    def record_round_result(self, round_number: int, tool_calls_made: int, 
                          tool_results: List[str], api_response: Any,
                          error: Optional[str] = None, tokens_used: Optional[Dict[str, int]] = None):
        """Record the result of a completed round"""
        result = RoundResult(
            round_number=round_number,
            tool_calls_made=tool_calls_made,
            tool_results=tool_results,
            api_response=api_response,
            error=error,
            tokens_used=tokens_used or {}
        )
        
        self.round_results.append(result)
        
        # Track token usage
        if tokens_used:
            self.total_tokens["input"] += tokens_used.get("input", 0)
            self.total_tokens["output"] += tokens_used.get("output", 0)
        
        # Log round completion
        status = "ERROR" if error else "SUCCESS"
        session_logger.info(f"Round {round_number} completed: {status}, "
                          f"Tools: {tool_calls_made}, Results: {len(tool_results)}")
        
        if error:
            session_logger.error(f"Round {round_number} error: {error}")
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of all rounds executed"""
        return {
            "total_rounds": len(self.round_results),
            "max_rounds": self.max_rounds,
            "total_tool_calls": sum(r.tool_calls_made for r in self.round_results),
            "total_tokens": self.total_tokens,
            "errors": [r.error for r in self.round_results if r.error],
            "success": all(r.error is None for r in self.round_results)
        }
    
    def has_errors(self) -> bool:
        """Check if any round had errors"""
        return any(r.error for r in self.round_results)
    
    def get_last_round_result(self) -> Optional[RoundResult]:
        """Get the result of the last completed round"""
        return self.round_results[-1] if self.round_results else None