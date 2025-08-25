import pytest
import os
from unittest.mock import patch, mock_open
from config import Config


class TestConfig:
    """Test Config class"""
    
    @patch.dict(os.environ, {}, clear=True)
    def test_default_values(self):
        """Test Config with default values when no environment variables are set"""
        # Clear any cached config and re-import to get fresh defaults
        with patch('config.load_dotenv'):
            from config import Config
            config = Config()
            
            assert config.LLM_PROVIDER == "anthropic"
            assert config.ANTHROPIC_API_KEY == ""
            assert config.ANTHROPIC_MODEL == "claude-3-5-haiku-20241022"
            assert config.GEMINI_API_KEY == ""
            assert config.GEMINI_MODEL == "gemini-1.5-flash"
            assert config.EMBEDDING_MODEL == "all-MiniLM-L6-v2"
            assert config.CHUNK_SIZE == 800
            assert config.CHUNK_OVERLAP == 100
            assert config.MAX_RESULTS == 5
            assert config.MAX_HISTORY == 2
            assert config.CHROMA_PATH == "./chroma_db"
    
    @patch.dict(os.environ, {
        "LLM_PROVIDER": "gemini",
        "ANTHROPIC_API_KEY": "test_anthropic_key",
        "GEMINI_API_KEY": "test_gemini_key"
    })
    def test_environment_variable_override(self):
        """Test Config uses environment variables when available"""
        with patch('config.load_dotenv'):
            from config import Config
            config = Config()
            
            assert config.LLM_PROVIDER == "gemini"
            assert config.ANTHROPIC_API_KEY == "test_anthropic_key"
            assert config.GEMINI_API_KEY == "test_gemini_key"
            # Other values should remain defaults
            assert config.ANTHROPIC_MODEL == "claude-3-5-haiku-20241022"
            assert config.GEMINI_MODEL == "gemini-1.5-flash"
    
    @patch.dict(os.environ, {"LLM_PROVIDER": "anthropic"})
    def test_anthropic_provider_setting(self):
        """Test Config with Anthropic provider setting"""
        with patch('config.load_dotenv'):
            from config import Config
            config = Config()
            
            assert config.LLM_PROVIDER == "anthropic"
    
    @patch.dict(os.environ, {"LLM_PROVIDER": "gemini"})
    def test_gemini_provider_setting(self):
        """Test Config with Gemini provider setting"""
        with patch('config.load_dotenv'):
            from config import Config
            config = Config()
            
            assert config.LLM_PROVIDER == "gemini"
    
    @patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "sk-test-anthropic-key-12345",
        "GEMINI_API_KEY": "test-gemini-key-67890"
    })
    def test_api_keys_from_env(self):
        """Test API keys are loaded from environment"""
        with patch('config.load_dotenv'):
            from config import Config
            config = Config()
            
            assert config.ANTHROPIC_API_KEY == "sk-test-anthropic-key-12345"
            assert config.GEMINI_API_KEY == "test-gemini-key-67890"
    
    @patch.dict(os.environ, {
        "EMBEDDING_MODEL": "all-mpnet-base-v2",
        "CHUNK_SIZE": "1000",
        "CHUNK_OVERLAP": "200",
        "MAX_RESULTS": "10",
        "MAX_HISTORY": "5",
        "CHROMA_PATH": "/custom/path/chroma"
    })
    def test_custom_processing_settings(self):
        """Test custom processing settings from environment"""
        with patch('config.load_dotenv'):
            from config import Config
            config = Config()
            
            assert config.EMBEDDING_MODEL == "all-mpnet-base-v2"
            assert config.CHUNK_SIZE == 1000  # Should be converted to int
            assert config.CHUNK_OVERLAP == 200  # Should be converted to int
            assert config.MAX_RESULTS == 10  # Should be converted to int
            assert config.MAX_HISTORY == 5  # Should be converted to int
            assert config.CHROMA_PATH == "/custom/path/chroma"
    
    @patch('config.load_dotenv')
    def test_dotenv_loading(self, mock_load_dotenv):
        """Test that dotenv.load_dotenv is called during import"""
        # Re-import to trigger the load_dotenv call
        import importlib
        import config
        importlib.reload(config)
        
        mock_load_dotenv.assert_called_once()
    
    def test_config_is_dataclass(self):
        """Test that Config is properly defined as a dataclass"""
        from config import Config
        config = Config()
        
        # Dataclasses should have these attributes
        assert hasattr(config, '__dataclass_fields__')
        assert hasattr(config, '__dataclass_params__')
    
    def test_config_fields_types(self):
        """Test that Config fields have correct types"""
        from config import Config
        fields = Config.__dataclass_fields__
        
        assert fields['LLM_PROVIDER'].type == str
        assert fields['ANTHROPIC_API_KEY'].type == str
        assert fields['ANTHROPIC_MODEL'].type == str
        assert fields['GEMINI_API_KEY'].type == str
        assert fields['GEMINI_MODEL'].type == str
        assert fields['EMBEDDING_MODEL'].type == str
        assert fields['CHUNK_SIZE'].type == int
        assert fields['CHUNK_OVERLAP'].type == int
        assert fields['MAX_RESULTS'].type == int
        assert fields['MAX_HISTORY'].type == int
        assert fields['CHROMA_PATH'].type == str
    
    @patch.dict(os.environ, {
        "ANTHROPIC_MODEL": "claude-3-opus-20240229",
        "GEMINI_MODEL": "gemini-pro"
    })
    def test_custom_model_names(self):
        """Test custom model names from environment"""
        with patch('config.load_dotenv'):
            from config import Config
            config = Config()
            
            assert config.ANTHROPIC_MODEL == "claude-3-opus-20240229"
            assert config.GEMINI_MODEL == "gemini-pro"
    
    def test_global_config_instance(self):
        """Test that global config instance is available"""
        from config import config
        
        assert config is not None
        assert isinstance(config, Config)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_empty_api_keys_default(self):
        """Test that empty API keys don't cause issues"""
        with patch('config.load_dotenv'):
            from config import Config
            config = Config()
            
            assert config.ANTHROPIC_API_KEY == ""
            assert config.GEMINI_API_KEY == ""
            # Config should still be valid
            assert config.LLM_PROVIDER == "anthropic"
    
    @patch.dict(os.environ, {"LLM_PROVIDER": "ANTHROPIC"})
    def test_case_sensitivity_env_vars(self):
        """Test that environment variables are case sensitive"""
        with patch('config.load_dotenv'):
            from config import Config
            config = Config()
            
            # Should get the exact value, not normalized
            assert config.LLM_PROVIDER == "ANTHROPIC"
    
    def test_config_immutability_attempt(self):
        """Test that config fields can be modified (dataclass is mutable by default)"""
        from config import Config
        config = Config()
        
        # Dataclass fields should be modifiable unless frozen=True
        original_provider = config.LLM_PROVIDER
        config.LLM_PROVIDER = "test_provider"
        assert config.LLM_PROVIDER == "test_provider"
        
        # Reset for other tests
        config.LLM_PROVIDER = original_provider
    
    @patch.dict(os.environ, {
        "CHUNK_SIZE": "not_a_number",
        "MAX_RESULTS": "invalid_int"
    })
    def test_invalid_integer_env_vars(self):
        """Test behavior with invalid integer environment variables"""
        with patch('config.load_dotenv'):
            # This should not raise an exception during Config creation
            # because dataclass field defaults are used when os.getenv returns non-int
            from config import Config
            
            # The dataclass will try to convert, but os.getenv returns string
            # and int() will be called on the non-numeric string
            with pytest.raises(ValueError):
                Config()
    
    @patch.dict(os.environ, {
        "CHUNK_SIZE": "1500",
        "CHUNK_OVERLAP": "0",  # Edge case: zero overlap
        "MAX_RESULTS": "1",    # Edge case: minimal results
        "MAX_HISTORY": "0"     # Edge case: no history
    })
    def test_edge_case_values(self):
        """Test edge case values for numeric settings"""
        with patch('config.load_dotenv'):
            from config import Config
            config = Config()
            
            assert config.CHUNK_SIZE == 1500
            assert config.CHUNK_OVERLAP == 0
            assert config.MAX_RESULTS == 1
            assert config.MAX_HISTORY == 0
    
    @patch.dict(os.environ, {"CHROMA_PATH": ""})
    def test_empty_chroma_path(self):
        """Test empty CHROMA_PATH environment variable"""
        with patch('config.load_dotenv'):
            from config import Config
            config = Config()
            
            # Should get empty string, not default
            assert config.CHROMA_PATH == ""
    
    @patch('builtins.open', new_callable=mock_open, read_data="LLM_PROVIDER=gemini\nANTHROPIC_API_KEY=test_key\n")
    @patch('config.load_dotenv')
    def test_dotenv_file_content(self, mock_load_dotenv, mock_file):
        """Test that .env file loading works correctly"""
        # This is more of an integration test to verify load_dotenv behavior
        from config import Config
        
        # Verify load_dotenv was called (it's called during module import)
        mock_load_dotenv.assert_called()