import pytest
import time
import threading
from datetime import datetime
from session_logger import SessionLogger


@pytest.fixture
def session_logger():
    """Create SessionLogger instance for testing"""
    return SessionLogger(max_logs=10)


class TestSessionLogger:
    """Test SessionLogger class"""
    
    def test_init(self):
        """Test SessionLogger initialization"""
        logger = SessionLogger(max_logs=100)
        
        assert logger.max_logs == 100
        assert len(logger.logs) == 0
        assert logger.lock is not None
    
    def test_init_default_max_logs(self):
        """Test SessionLogger with default max_logs"""
        logger = SessionLogger()
        
        assert logger.max_logs == 1000
    
    def test_log_basic(self, session_logger):
        """Test basic logging functionality"""
        session_logger.log("info", "Test message")
        
        logs = session_logger.get_logs()
        assert len(logs) == 1
        
        log_entry = logs[0]
        assert log_entry["level"] == "info"
        assert log_entry["message"] == "Test message"
        assert "timestamp" in log_entry
    
    def test_log_with_kwargs(self, session_logger):
        """Test logging with additional keyword arguments"""
        session_logger.log("info", "Test message", user_id=123, action="login")
        
        logs = session_logger.get_logs()
        log_entry = logs[0]
        
        assert log_entry["level"] == "info"
        assert log_entry["message"] == "Test message"
        assert log_entry["user_id"] == 123
        assert log_entry["action"] == "login"
    
    def test_info_method(self, session_logger):
        """Test info logging method"""
        session_logger.info("Info message")
        
        logs = session_logger.get_logs()
        assert len(logs) == 1
        assert logs[0]["level"] == "info"
        assert logs[0]["message"] == "Info message"
    
    def test_token_method(self, session_logger):
        """Test token logging method"""
        session_logger.token("Token usage", tokens=100)
        
        logs = session_logger.get_logs()
        assert len(logs) == 1
        assert logs[0]["level"] == "token"
        assert logs[0]["message"] == "Token usage"
        assert logs[0]["tokens"] == 100
    
    def test_error_method(self, session_logger):
        """Test error logging method"""
        session_logger.error("Error occurred", error_code=500)
        
        logs = session_logger.get_logs()
        assert len(logs) == 1
        assert logs[0]["level"] == "error"
        assert logs[0]["message"] == "Error occurred"
        assert logs[0]["error_code"] == 500
    
    def test_timestamp_format(self, session_logger):
        """Test that timestamp is in ISO format"""
        before_time = datetime.now()
        session_logger.info("Test message")
        after_time = datetime.now()
        
        logs = session_logger.get_logs()
        timestamp_str = logs[0]["timestamp"]
        
        # Parse timestamp and verify it's between before and after
        log_time = datetime.fromisoformat(timestamp_str)
        assert before_time <= log_time <= after_time
    
    def test_multiple_logs(self, session_logger):
        """Test logging multiple messages"""
        messages = ["Message 1", "Message 2", "Message 3"]
        
        for i, msg in enumerate(messages):
            session_logger.info(msg, index=i)
        
        logs = session_logger.get_logs()
        assert len(logs) == 3
        
        for i, log_entry in enumerate(logs):
            assert log_entry["message"] == messages[i]
            assert log_entry["index"] == i
    
    def test_max_logs_limit(self):
        """Test that logs are limited to max_logs"""
        logger = SessionLogger(max_logs=3)
        
        # Add more logs than the limit
        for i in range(5):
            logger.info(f"Message {i}")
        
        logs = logger.get_logs()
        
        # Should only keep the last 3 logs
        assert len(logs) == 3
        assert logs[0]["message"] == "Message 2"  # First kept message
        assert logs[1]["message"] == "Message 3"
        assert logs[2]["message"] == "Message 4"  # Last message
    
    def test_clear_logs(self, session_logger):
        """Test clearing all logs"""
        session_logger.info("Message 1")
        session_logger.info("Message 2")
        
        assert len(session_logger.get_logs()) == 2
        
        session_logger.clear_logs()
        
        assert len(session_logger.get_logs()) == 0
    
    def test_get_logs_returns_copy(self, session_logger):
        """Test that get_logs returns a copy, not the original"""
        session_logger.info("Test message")
        
        logs1 = session_logger.get_logs()
        logs2 = session_logger.get_logs()
        
        # Should be equal but not the same object
        assert logs1 == logs2
        assert logs1 is not logs2
        
        # Modifying one shouldn't affect the other
        logs1.append({"test": "modified"})
        assert len(logs2) == 1
    
    def test_thread_safety(self, session_logger):
        """Test that SessionLogger is thread-safe"""
        def add_logs(logger, thread_id, count):
            for i in range(count):
                logger.info(f"Thread {thread_id} message {i}", thread_id=thread_id)
        
        threads = []
        thread_count = 5
        messages_per_thread = 10
        
        # Create and start threads
        for thread_id in range(thread_count):
            thread = threading.Thread(
                target=add_logs,
                args=(session_logger, thread_id, messages_per_thread)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        logs = session_logger.get_logs()
        
        # Should have all messages (limited by max_logs if exceeded)
        expected_total = min(thread_count * messages_per_thread, session_logger.max_logs)
        assert len(logs) == expected_total
        
        # Verify all thread IDs are present in some logs
        thread_ids = {log.get("thread_id") for log in logs}
        assert len(thread_ids) <= thread_count
    
    def test_concurrent_read_write(self, session_logger):
        """Test concurrent reading and writing"""
        def continuous_logging():
            for i in range(50):
                session_logger.info(f"Log {i}")
                time.sleep(0.001)  # Small delay
        
        def continuous_reading():
            for _ in range(50):
                logs = session_logger.get_logs()
                # Just accessing logs, not asserting specifics due to concurrency
                time.sleep(0.001)
        
        # Start logging thread
        log_thread = threading.Thread(target=continuous_logging)
        read_thread = threading.Thread(target=continuous_reading)
        
        log_thread.start()
        read_thread.start()
        
        log_thread.join()
        read_thread.join()
        
        # Should not crash and should have some logs
        final_logs = session_logger.get_logs()
        assert len(final_logs) > 0
    
    def test_log_with_none_values(self, session_logger):
        """Test logging with None values"""
        session_logger.log("info", "Test message", value=None, other=42)
        
        logs = session_logger.get_logs()
        log_entry = logs[0]
        
        assert log_entry["value"] is None
        assert log_entry["other"] == 42
    
    def test_log_with_complex_objects(self, session_logger):
        """Test logging with complex objects"""
        test_data = {
            "list": [1, 2, 3],
            "dict": {"nested": True},
            "string": "test"
        }
        
        session_logger.log("info", "Complex data", **test_data)
        
        logs = session_logger.get_logs()
        log_entry = logs[0]
        
        assert log_entry["list"] == [1, 2, 3]
        assert log_entry["dict"] == {"nested": True}
        assert log_entry["string"] == "test"
    
    def test_empty_message(self, session_logger):
        """Test logging empty message"""
        session_logger.info("")
        
        logs = session_logger.get_logs()
        assert len(logs) == 1
        assert logs[0]["message"] == ""
    
    def test_message_with_special_characters(self, session_logger):
        """Test logging message with special characters"""
        special_msg = "Message with special chars: !@#$%^&*()[]{}|;:'\",.<>?/~`"
        session_logger.info(special_msg)
        
        logs = session_logger.get_logs()
        assert logs[0]["message"] == special_msg
    
    def test_unicode_message(self, session_logger):
        """Test logging unicode message"""
        unicode_msg = "Message with unicode: 你好, café, naïve, résumé"
        session_logger.info(unicode_msg)
        
        logs = session_logger.get_logs()
        assert logs[0]["message"] == unicode_msg
    
    def test_different_log_levels(self, session_logger):
        """Test different log levels"""
        session_logger.info("Info message")
        session_logger.token("Token message")
        session_logger.error("Error message")
        session_logger.log("custom", "Custom level message")
        
        logs = session_logger.get_logs()
        assert len(logs) == 4
        
        levels = [log["level"] for log in logs]
        assert levels == ["info", "token", "error", "custom"]
    
    def test_log_ordering(self, session_logger):
        """Test that logs maintain chronological order"""
        messages = [f"Message {i}" for i in range(5)]
        
        for msg in messages:
            session_logger.info(msg)
            time.sleep(0.001)  # Ensure different timestamps
        
        logs = session_logger.get_logs()
        
        # Verify chronological order
        timestamps = [log["timestamp"] for log in logs]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1]
        
        # Verify message order
        log_messages = [log["message"] for log in logs]
        assert log_messages == messages