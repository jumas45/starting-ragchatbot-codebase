from typing import List, Dict, Any
from datetime import datetime
from collections import deque
import threading

class SessionLogger:
    """Thread-safe session logger that stores logs in memory for the current session"""
    
    def __init__(self, max_logs: int = 1000):
        self.max_logs = max_logs
        self.logs = deque(maxlen=max_logs)
        self.lock = threading.Lock()
    
    def log(self, level: str, message: str, **kwargs):
        """Add a log entry"""
        with self.lock:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message,
                **kwargs
            }
            self.logs.append(log_entry)
    
    def info(self, message: str, **kwargs):
        """Log an info message"""
        self.log("info", message, **kwargs)
    
    def token(self, message: str, **kwargs):
        """Log a token usage message"""
        self.log("token", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log an error message"""
        self.log("error", message, **kwargs)
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Get all logs as a list"""
        with self.lock:
            return list(self.logs)
    
    def clear_logs(self):
        """Clear all logs"""
        with self.lock:
            self.logs.clear()

# Global session logger instance
session_logger = SessionLogger()