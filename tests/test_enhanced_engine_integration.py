"""
Integration tests for the enhanced engine configuration
"""

import pytest
from unittest.mock import Mock, patch

from lingodotdev import LingoDotDevEngine
from lingodotdev.models import EnhancedEngineConfig, RetryConfiguration
from lingodotdev.exceptions import LingoDevConfigurationError, LingoDevRetryExhaustedError


class TestEnhancedEngineIntegration:
    """Test the integration of enhanced configuration with the engine"""

    def test_engine_with_enhanced_config_dict(self):
        """Test engine initialization with enhanced configuration dictionary"""
        config = {
            'api_key': 'test_key_12345',
            'api_url': 'https://api.test.com',
            'timeout': 45.0,
            'batch_size': 50,
            'retry_config': {
                'max_retries': 5,
                'backoff_factor': 1.0,
                'jitter': False
            }
        }
        
        engine = LingoDotDevEngine(config)
        
        # Verify configuration is properly set
        assert engine.config.api_key == 'test_key_12345'
        assert engine.config.api_url == 'https://api.test.com'
        assert engine.config.timeout == 45.0
        assert engine.config.batch_size == 50
        assert engine.config.retry_config.max_retries == 5
        assert engine.config.retry_config.backoff_factor == 1.0
        assert engine.config.retry_config.jitter is False
        
        # Verify retry handler is initialized
        assert engine.retry_handler is not None
        assert engine.retry_handler.config.max_retries == 5

    def test_engine_with_pydantic_config(self):
        """Test engine initialization with Pydantic configuration object"""
        retry_config = RetryConfiguration(max_retries=3, backoff_factor=0.5)
        config = EnhancedEngineConfig(
            api_key='test_key_12345',
            timeout=60.0,
            retry_config=retry_config
        )
        
        engine = LingoDotDevEngine(config)
        
        # Verify configuration is properly set
        assert engine.config.api_key == 'test_key_12345'
        assert engine.config.timeout == 60.0
        assert engine.config.retry_config.max_retries == 3
        assert engine.config.retry_config.backoff_factor == 0.5
        
        # Verify retry handler is initialized
        assert engine.retry_handler is not None

    def test_engine_with_disabled_retry(self):
        """Test engine initialization with retry disabled"""
        config = {
            'api_key': 'test_key_12345',
            'retry_config': None
        }
        
        engine = LingoDotDevEngine(config)
        
        # Verify retry is disabled
        assert engine.config.retry_config is None
        assert engine.retry_handler is None

    def test_engine_with_invalid_config(self):
        """Test engine initialization with invalid configuration"""
        config = {
            'api_key': '',  # Invalid empty API key
            'timeout': -5.0,  # Invalid negative timeout
        }
        
        with pytest.raises(LingoDevConfigurationError) as exc_info:
            LingoDotDevEngine(config)
        
        error = exc_info.value
        assert "Invalid engine configuration" in error.message
        assert error.details["provided_config"] == config

    def test_backward_compatibility_with_old_config(self):
        """Test that old configuration format still works"""
        # Old style configuration (minimal)
        old_config = {
            'api_key': 'test_key_12345'
        }
        
        engine = LingoDotDevEngine(old_config)
        
        # Should use default values
        assert engine.config.api_key == 'test_key_12345'
        assert engine.config.api_url == 'https://engine.lingo.dev'
        assert engine.config.timeout == 30.0
        assert engine.config.batch_size == 25
        assert engine.config.retry_config is not None  # Default retry config
        assert engine.retry_handler is not None

    @patch("lingodotdev.engine.requests.Session.post")
    def test_retry_integration_in_api_calls(self, mock_post):
        """Test that retry logic is properly integrated into API calls"""
        # Configure engine with custom retry settings
        config = {
            'api_key': 'test_key_12345',
            'retry_config': {
                'max_retries': 2,
                'backoff_factor': 0.1,  # Fast for testing
                'jitter': False
            }
        }
        
        engine = LingoDotDevEngine(config)
        
        # Mock a server error response
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.reason = "Internal Server Error"
        mock_response.text = "Server error"
        mock_post.return_value = mock_response
        
        # Should retry and then fail with LingoDevRetryExhaustedError
        with pytest.raises(LingoDevRetryExhaustedError) as exc_info:
            engine.localize_text("Hello", {"target_locale": "es"})
        
        # Verify retry attempts
        error = exc_info.value
        assert error.total_attempts == 2  # Should have tried 2 times
        assert mock_post.call_count == 2  # Should have made 2 API calls

    def test_timeout_configuration(self):
        """Test that timeout configuration is properly applied"""
        config = {
            'api_key': 'test_key_12345',
            'timeout': 120.0
        }
        
        engine = LingoDotDevEngine(config)
        
        # Verify timeout is set in configuration
        assert engine.config.timeout == 120.0
        
        # The timeout should be applied to session requests
        # (This is tested indirectly through the session configuration)

    def test_configuration_validation_messages(self):
        """Test that configuration validation provides helpful error messages"""
        test_cases = [
            {
                'config': {'api_key': 'short'},
                'expected_error': 'API key appears to be too short'
            },
            {
                'config': {'api_key': 'test_key_12345', 'api_url': 'invalid_url'},
                'expected_error': 'API URL must be a valid HTTP/HTTPS URL'
            },
            {
                'config': {'api_key': 'test_key_12345', 'batch_size': 0},
                'expected_error': 'Input should be greater than or equal to 1'
            },
            {
                'config': {'api_key': 'test_key_12345', 'timeout': 0.5},
                'expected_error': 'Input should be greater than or equal to 1'
            }
        ]
        
        for test_case in test_cases:
            with pytest.raises(LingoDevConfigurationError) as exc_info:
                LingoDotDevEngine(test_case['config'])
            
            error_message = str(exc_info.value)
            assert test_case['expected_error'] in error_message

    def test_retry_configuration_validation(self):
        """Test retry configuration validation"""
        config = {
            'api_key': 'test_key_12345',
            'retry_config': {
                'max_retries': -1,  # Invalid
                'backoff_factor': 5.0,  # Invalid (too high)
            }
        }
        
        with pytest.raises(LingoDevConfigurationError):
            LingoDotDevEngine(config)

    def test_configuration_with_environment_like_usage(self):
        """Test configuration that mimics environment variable usage"""
        # Simulate loading from environment variables
        config = {
            'api_key': 'api_prod_key_12345',
            'api_url': 'https://prod-api.lingo.dev',
            'timeout': 60.0,
            'batch_size': 100,
            'ideal_batch_item_size': 1000,
            'retry_config': {
                'max_retries': 5,
                'backoff_factor': 1.5,
                'max_backoff': 120.0,
                'jitter': True,
                'retry_statuses': [429, 500, 502, 503, 504]
            }
        }
        
        engine = LingoDotDevEngine(config)
        
        # Verify all configuration is properly applied
        assert engine.config.api_key == 'api_prod_key_12345'
        assert engine.config.api_url == 'https://prod-api.lingo.dev'
        assert engine.config.timeout == 60.0
        assert engine.config.batch_size == 100
        assert engine.config.ideal_batch_item_size == 1000
        
        # Verify retry configuration
        retry_config = engine.config.retry_config
        assert retry_config.max_retries == 5
        assert retry_config.backoff_factor == 1.5
        assert retry_config.max_backoff == 120.0
        assert retry_config.jitter is True
        assert retry_config.retry_statuses == {429, 500, 502, 503, 504}
        
        # Verify retry handler is properly configured
        assert engine.retry_handler is not None
        assert engine.retry_handler.config.max_retries == 5

    def test_mixed_configuration_types(self):
        """Test mixing different configuration approaches"""
        # Create retry config as Pydantic model
        retry_config = RetryConfiguration(
            max_retries=4,
            backoff_factor=0.8,
            jitter=False
        )
        
        # Use it in dictionary config
        config = {
            'api_key': 'test_key_12345',
            'timeout': 45.0,
            'retry_config': retry_config  # Pydantic model in dict
        }
        
        engine = LingoDotDevEngine(config)
        
        # Should work seamlessly
        assert engine.config.timeout == 45.0
        assert engine.config.retry_config.max_retries == 4
        assert engine.config.retry_config.backoff_factor == 0.8
        assert engine.config.retry_config.jitter is False