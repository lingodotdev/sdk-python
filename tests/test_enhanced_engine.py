"""
Tests for the enhanced engine configuration and integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from lingodotdev import LingoDotDevEngine
from lingodotdev.models import EnhancedEngineConfig, RetryConfiguration
from lingodotdev.exceptions import (
    LingoDevConfigurationError,
    LingoDevAPIError,
    LingoDevNetworkError,
    LingoDevRetryExhaustedError,
)


class TestEnhancedEngineConfiguration:
    """Test the enhanced engine configuration system"""

    def test_backward_compatibility_dict_config(self):
        """Test that dictionary configuration still works"""
        config_dict = {
            "api_key": "test_api_key_12345",
            "api_url": "https://api.test.com",
            "batch_size": 50,
            "ideal_batch_item_size": 500,
        }
        
        engine = LingoDotDevEngine(config_dict)
        
        assert engine.config.api_key == "test_api_key_12345"
        assert engine.config.api_url == "https://api.test.com"
        assert engine.config.batch_size == 50
        assert engine.config.ideal_batch_item_size == 500
        assert engine.config.timeout == 30.0  # Default value
        assert engine.config.retry_config is not None  # Default retry config

    def test_enhanced_config_object(self):
        """Test using EnhancedEngineConfig object directly"""
        config = EnhancedEngineConfig(
            api_key="test_api_key_12345",
            api_url="https://api.test.com",
            timeout=60.0,
            retry_config=RetryConfiguration(max_retries=5)
        )
        
        engine = LingoDotDevEngine(config)
        
        assert engine.config.api_key == "test_api_key_12345"
        assert engine.config.timeout == 60.0
        assert engine.config.retry_config.max_retries == 5

    def test_retry_handler_initialization(self):
        """Test that retry handler is properly initialized"""
        config_dict = {
            "api_key": "test_api_key_12345",
            "retry_config": {
                "max_retries": 5,
                "backoff_factor": 1.0,
                "jitter": False
            }
        }
        
        engine = LingoDotDevEngine(config_dict)
        
        assert engine.retry_handler is not None
        assert engine.retry_handler.config.max_retries == 5
        assert engine.retry_handler.config.backoff_factor == 1.0
        assert engine.retry_handler.config.jitter is False

    def test_retry_handler_disabled(self):
        """Test that retry handler can be disabled"""
        config_dict = {
            "api_key": "test_api_key_12345",
            "retry_config": None
        }
        
        engine = LingoDotDevEngine(config_dict)
        
        assert engine.retry_handler is None

    def test_timeout_configuration(self):
        """Test that timeout is properly configured"""
        config_dict = {
            "api_key": "test_api_key_12345",
            "timeout": 45.0
        }
        
        engine = LingoDotDevEngine(config_dict)
        
        assert engine.config.timeout == 45.0
        # Verify timeout is applied to session
        with patch.object(engine.session, 'post') as mock_post:
            