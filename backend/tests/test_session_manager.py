import pytest
from session_manager import SessionManager, Message


@pytest.fixture
def session_manager():
    """Create SessionManager instance for testing"""
    return SessionManager(max_history=3)


class TestMessage:
    """Test Message dataclass"""
    
    def test_message_creation(self):
        """Test creating Message instance"""
        msg = Message(role="user", content="Hello world")
        
        assert msg.role == "user"
        assert msg.content == "Hello world"
    
    def test_message_equality(self):
        """Test Message equality comparison"""
        msg1 = Message(role="user", content="Hello")
        msg2 = Message(role="user", content="Hello")
        msg3 = Message(role="assistant", content="Hello")
        
        assert msg1 == msg2
        assert msg1 != msg3


class TestSessionManager:
    """Test SessionManager class"""
    
    def test_init(self):
        """Test SessionManager initialization"""
        sm = SessionManager(max_history=5)
        
        assert sm.max_history == 5
        assert sm.sessions == {}
        assert sm.session_counter == 0
    
    def test_init_default_max_history(self):
        """Test SessionManager with default max_history"""
        sm = SessionManager()
        
        assert sm.max_history == 5
    
    def test_create_session(self, session_manager):
        """Test creating new session"""
        session_id = session_manager.create_session()
        
        assert session_id == "session_1"
        assert session_id in session_manager.sessions
        assert session_manager.sessions[session_id] == []
        assert session_manager.session_counter == 1
    
    def test_create_multiple_sessions(self, session_manager):
        """Test creating multiple sessions"""
        session1 = session_manager.create_session()
        session2 = session_manager.create_session()
        session3 = session_manager.create_session()
        
        assert session1 == "session_1"
        assert session2 == "session_2" 
        assert session3 == "session_3"
        assert len(session_manager.sessions) == 3
        assert session_manager.session_counter == 3
    
    def test_add_message_to_existing_session(self, session_manager):
        """Test adding message to existing session"""
        session_id = session_manager.create_session()
        
        session_manager.add_message(session_id, "user", "Hello")
        
        assert len(session_manager.sessions[session_id]) == 1
        msg = session_manager.sessions[session_id][0]
        assert msg.role == "user"
        assert msg.content == "Hello"
    
    def test_add_message_to_nonexistent_session(self, session_manager):
        """Test adding message to nonexistent session creates it"""
        session_manager.add_message("new_session", "user", "Hello")
        
        assert "new_session" in session_manager.sessions
        assert len(session_manager.sessions["new_session"]) == 1
    
    def test_add_multiple_messages(self, session_manager):
        """Test adding multiple messages to session"""
        session_id = session_manager.create_session()
        
        session_manager.add_message(session_id, "user", "Hello")
        session_manager.add_message(session_id, "assistant", "Hi there!")
        session_manager.add_message(session_id, "user", "How are you?")
        
        messages = session_manager.sessions[session_id]
        assert len(messages) == 3
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert messages[2].role == "user"
    
    def test_add_message_history_limit(self, session_manager):
        """Test message history limit enforcement"""
        session_id = session_manager.create_session()
        
        # Add more messages than the limit (max_history=3, so limit is 3*2=6)
        for i in range(10):
            session_manager.add_message(session_id, "user", f"Message {i}")
        
        messages = session_manager.sessions[session_id]
        # Should keep only the last 6 messages (max_history * 2)
        assert len(messages) == 6
        assert messages[0].content == "Message 4"  # First kept message
        assert messages[-1].content == "Message 9"  # Last message
    
    def test_add_exchange(self, session_manager):
        """Test adding complete user-assistant exchange"""
        session_id = session_manager.create_session()
        
        session_manager.add_exchange(session_id, "What is Python?", "Python is a programming language.")
        
        messages = session_manager.sessions[session_id]
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "What is Python?"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Python is a programming language."
    
    def test_get_conversation_history_valid_session(self, session_manager):
        """Test getting conversation history for valid session"""
        session_id = session_manager.create_session()
        session_manager.add_message(session_id, "user", "Hello")
        session_manager.add_message(session_id, "assistant", "Hi there!")
        
        history = session_manager.get_conversation_history(session_id)
        
        expected = "User: Hello\nAssistant: Hi there!"
        assert history == expected
    
    def test_get_conversation_history_empty_session(self, session_manager):
        """Test getting conversation history for empty session"""
        session_id = session_manager.create_session()
        
        history = session_manager.get_conversation_history(session_id)
        
        assert history is None
    
    def test_get_conversation_history_nonexistent_session(self, session_manager):
        """Test getting conversation history for nonexistent session"""
        history = session_manager.get_conversation_history("nonexistent")
        
        assert history is None
    
    def test_get_conversation_history_none_session_id(self, session_manager):
        """Test getting conversation history with None session_id"""
        history = session_manager.get_conversation_history(None)
        
        assert history is None
    
    def test_get_conversation_history_formatting(self, session_manager):
        """Test conversation history formatting"""
        session_id = session_manager.create_session()
        session_manager.add_message(session_id, "user", "Question 1")
        session_manager.add_message(session_id, "assistant", "Answer 1")
        session_manager.add_message(session_id, "user", "Question 2")
        session_manager.add_message(session_id, "assistant", "Answer 2")
        
        history = session_manager.get_conversation_history(session_id)
        
        expected = "User: Question 1\nAssistant: Answer 1\nUser: Question 2\nAssistant: Answer 2"
        assert history == expected
    
    def test_clear_session_existing(self, session_manager):
        """Test clearing existing session"""
        session_id = session_manager.create_session()
        session_manager.add_message(session_id, "user", "Hello")
        session_manager.add_message(session_id, "assistant", "Hi!")
        
        # Verify messages exist
        assert len(session_manager.sessions[session_id]) == 2
        
        session_manager.clear_session(session_id)
        
        # Session should still exist but be empty
        assert session_id in session_manager.sessions
        assert len(session_manager.sessions[session_id]) == 0
    
    def test_clear_session_nonexistent(self, session_manager):
        """Test clearing nonexistent session"""
        # Should not raise an error
        session_manager.clear_session("nonexistent")
    
    def test_session_isolation(self, session_manager):
        """Test that sessions are isolated from each other"""
        session1 = session_manager.create_session()
        session2 = session_manager.create_session()
        
        session_manager.add_message(session1, "user", "Message for session 1")
        session_manager.add_message(session2, "user", "Message for session 2")
        
        assert len(session_manager.sessions[session1]) == 1
        assert len(session_manager.sessions[session2]) == 1
        assert session_manager.sessions[session1][0].content == "Message for session 1"
        assert session_manager.sessions[session2][0].content == "Message for session 2"
    
    def test_history_limit_calculation(self):
        """Test history limit calculation with different max_history values"""
        sm1 = SessionManager(max_history=1)
        sm2 = SessionManager(max_history=10)
        
        session1 = sm1.create_session()
        session2 = sm2.create_session()
        
        # Add many messages to both sessions
        for i in range(20):
            sm1.add_message(session1, "user", f"Msg {i}")
            sm2.add_message(session2, "user", f"Msg {i}")
        
        # Session 1 should keep only 2 messages (max_history=1 * 2)
        assert len(sm1.sessions[session1]) == 2
        
        # Session 2 should keep 20 messages (max_history=10 * 2)
        assert len(sm2.sessions[session2]) == 20
    
    def test_message_content_preservation(self, session_manager):
        """Test that message content is preserved exactly"""
        session_id = session_manager.create_session()
        
        # Test with various content types
        test_messages = [
            ("user", "Simple message"),
            ("assistant", "Message with\nnewlines\nand\ttabs"),
            ("user", "Message with special chars: !@#$%^&*()"),
            ("assistant", ""),  # Empty message
            ("user", "   Message with whitespace   "),
        ]
        
        for role, content in test_messages:
            session_manager.add_message(session_id, role, content)
        
        messages = session_manager.sessions[session_id]
        for i, (expected_role, expected_content) in enumerate(test_messages):
            assert messages[i].role == expected_role
            assert messages[i].content == expected_content
    
    def test_concurrent_session_operations(self, session_manager):
        """Test concurrent operations on different sessions"""
        sessions = []
        
        # Create multiple sessions
        for i in range(5):
            session_id = session_manager.create_session()
            sessions.append(session_id)
        
        # Add messages to all sessions
        for i, session_id in enumerate(sessions):
            session_manager.add_message(session_id, "user", f"Message from session {i}")
        
        # Verify all sessions have their messages
        for i, session_id in enumerate(sessions):
            messages = session_manager.sessions[session_id]
            assert len(messages) == 1
            assert messages[0].content == f"Message from session {i}"
    
    def test_edge_case_empty_strings(self, session_manager):
        """Test edge cases with empty strings"""
        session_id = session_manager.create_session()
        
        # Add message with empty content
        session_manager.add_message(session_id, "user", "")
        session_manager.add_message(session_id, "assistant", "")
        
        # Should still create messages
        messages = session_manager.sessions[session_id]
        assert len(messages) == 2
        assert messages[0].content == ""
        assert messages[1].content == ""
        
        # History should still work
        history = session_manager.get_conversation_history(session_id)
        assert history == "User: \nAssistant: "