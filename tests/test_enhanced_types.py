"""
Tests for enhanced type system and validation
"""

import pytest
from pydantic import ValidationError

from lingodotdev.models import (
    EnhancedEngineConfig,
    LocalizationParams,
    BatchLocalizationParams,
    ChatMessageModel,
    RetryConfiguration,
)
from lingodotdev.types import (
    LocalizationRequest,
    BatchLocalizationRequest,
    ChatMessage,
    RetryConfig,
    EngineConfigDict,
)


class TestEnhancedEngineConfig:
    """Test the enhanced engine configuration model"""

    def test_valid_config(self):
        """Test valid configuration"""
        config = EnhancedEngineConfig(
            api_key="test_api_key_12345",
            api_url="https://api.test.com",
            batch_size=50,
            ideal_batch_item_size=500,
            timeout=60.0,
        )
        assert config.api_key == "test_api_key_12345"
        assert config.api_url == "https://api.test.com"
        assert config.batch_size == 50
        assert config.ideal_batch_item_size == 500
        assert config.timeout == 60.0
        assert isinstance(config.retry_config, RetryConfiguration)

    def test_default_values(self):
        """Test default configuration values"""
        config = EnhancedEngineConfig(api_key="test_api_key_12345")
        assert config.api_url == "https://engine.lingo.dev"
        assert config.batch_size == 25
        assert config.ideal_batch_item_size == 250
        assert config.timeout == 30.0
        assert config.retry_config is not None

    def test_invalid_api_url(self):
        """Test invalid API URL validation"""
        with pytest.raises(ValidationError) as exc_info:
            EnhancedEngineConfig(api_key="test_key_12345", api_url="invalid_url")
        
        # Find the API URL validation error
        api_url_errors = [e for e in exc_info.value.errors() if e["loc"] == ("api_url",)]
        assert len(api_url_errors) > 0
        assert "API URL must be a valid HTTP/HTTPS URL" in api_url_errors[0]["msg"]

    def test_empty_api_key(self):
        """Test empty API key validation"""
        with pytest.raises(ValidationError) as exc_info:
            EnhancedEngineConfig(api_key="")
        
        # Check for either our custom message or Pydantic's built-in message
        error = exc_info.value.errors()[0]
        assert ("API key cannot be empty" in error["msg"] or 
                "String should have at least 1 character" in error["msg"])

    def test_short_api_key(self):
        """Test short API key validation"""
        with pytest.raises(ValidationError) as exc_info:
            EnhancedEngineConfig(api_key="short")
        
        error = exc_info.value.errors()[0]
        assert "API key appears to be too short" in error["msg"]

    def test_invalid_batch_size(self):
        """Test invalid batch size validation"""
        with pytest.raises(ValidationError):
            EnhancedEngineConfig(api_key="test_key_12345", batch_size=0)

        with pytest.raises(ValidationError):
            EnhancedEngineConfig(api_key="test_key_12345", batch_size=300)

    def test_invalid_timeout(self):
        """Test invalid timeout validation"""
        with pytest.raises(ValidationError):
            EnhancedEngineConfig(api_key="test_key_12345", timeout=0.5)

        with pytest.raises(ValidationError):
            EnhancedEngineConfig(api_key="test_key_12345", timeout=400.0)


class TestRetryConfiguration:
    """Test the retry configuration model"""

    def test_valid_retry_config(self):
        """Test valid retry configuration"""
        config = RetryConfiguration(
            max_retries=5,
            backoff_factor=1.0,
            retry_statuses={429, 500, 503},
            max_backoff=120.0,
            jitter=False,
        )
        assert config.max_retries == 5
        assert config.backoff_factor == 1.0
        assert config.retry_statuses == {429, 500, 503}
        assert config.max_backoff == 120.0
        assert config.jitter is False

    def test_default_retry_config(self):
        """Test default retry configuration values"""
        config = RetryConfiguration()
        assert config.max_retries == 3
        assert config.backoff_factor == 0.5
        assert config.retry_statuses == {429, 500, 502, 503, 504}
        assert config.max_backoff == 60.0
        assert config.jitter is True

    def test_invalid_retry_statuses(self):
        """Test invalid retry status codes"""
        with pytest.raises(ValidationError) as exc_info:
            RetryConfiguration(retry_statuses={200, 300, 500})
        
        error = exc_info.value.errors()[0]
        assert "Invalid HTTP status codes for retry" in error["msg"]

    def test_invalid_max_retries(self):
        """Test invalid max retries"""
        with pytest.raises(ValidationError):
            RetryConfiguration(max_retries=-1)

        with pytest.raises(ValidationError):
            RetryConfiguration(max_retries=15)

    def test_invalid_backoff_factor(self):
        """Test invalid backoff factor"""
        with pytest.raises(ValidationError):
            RetryConfiguration(backoff_factor=0.05)

        with pytest.raises(ValidationError):
            RetryConfiguration(backoff_factor=3.0)


class TestLocalizationParams:
    """Test the localization parameters model"""

    def test_valid_params(self):
        """Test valid localization parameters"""
        params = LocalizationParams(
            source_locale="en",
            target_locale="es",
            fast=True,
        )
        assert params.source_locale == "en"
        assert params.target_locale == "es"
        assert params.fast is True
        assert params.reference is None

    def test_locale_normalization(self):
        """Test locale code normalization"""
        params = LocalizationParams(
            source_locale="EN-US",
            target_locale="ES-MX",
        )
        assert params.source_locale == "en-us"
        assert params.target_locale == "es-mx"

    def test_invalid_locale_codes(self):
        """Test invalid locale code validation"""
        with pytest.raises(ValidationError):
            LocalizationParams(target_locale="")

        with pytest.raises(ValidationError):
            LocalizationParams(target_locale="invalid_locale_code")

        with pytest.raises(ValidationError):
            LocalizationParams(target_locale="123")

    def test_missing_target_locale(self):
        """Test missing target locale"""
        with pytest.raises(ValidationError):
            LocalizationParams()


class TestBatchLocalizationParams:
    """Test the batch localization parameters model"""

    def test_valid_batch_params(self):
        """Test valid batch localization parameters"""
        params = BatchLocalizationParams(
            source_locale="en",
            target_locales=["es", "fr", "de"],
            fast=True,
        )
        assert params.source_locale == "en"
        assert params.target_locales == ["es", "fr", "de"]
        assert params.fast is True

    def test_empty_target_locales(self):
        """Test empty target locales list"""
        with pytest.raises(ValidationError) as exc_info:
            BatchLocalizationParams(target_locales=[])
        
        # Check for either our custom message or Pydantic's built-in message
        error = exc_info.value.errors()[0]
        assert ("At least one target locale must be specified" in error["msg"] or 
                "List should have at least 1 item" in error["msg"])

    def test_duplicate_target_locales(self):
        """Test duplicate target locales"""
        with pytest.raises(ValidationError) as exc_info:
            BatchLocalizationParams(target_locales=["es", "fr", "es"])
        
        error = exc_info.value.errors()[0]
        assert "Duplicate target locales found" in error["msg"]

    def test_invalid_target_locales(self):
        """Test invalid target locale codes"""
        with pytest.raises(ValidationError):
            BatchLocalizationParams(target_locales=["es", "invalid_code"])


class TestChatMessageModel:
    """Test the chat message model"""

    def test_valid_chat_message(self):
        """Test valid chat message"""
        message = ChatMessageModel(name="Alice", text="Hello world!")
        assert message.name == "Alice"
        assert message.text == "Hello world!"

    def test_empty_name(self):
        """Test empty speaker name"""
        with pytest.raises(ValidationError):
            ChatMessageModel(name="", text="Hello")

        with pytest.raises(ValidationError):
            ChatMessageModel(name="   ", text="Hello")

    def test_empty_text(self):
        """Test empty message text"""
        with pytest.raises(ValidationError):
            ChatMessageModel(name="Alice", text="")

        with pytest.raises(ValidationError):
            ChatMessageModel(name="Alice", text="   ")

    def test_long_name(self):
        """Test very long speaker name"""
        long_name = "A" * 101  # Exceeds max_length=100
        with pytest.raises(ValidationError):
            ChatMessageModel(name=long_name, text="Hello")


class TestTypeDefinitions:
    """Test TypedDict type definitions"""

    def test_localization_request_typing(self):
        """Test LocalizationRequest TypedDict"""
        # This test mainly ensures the types are importable and usable
        request: LocalizationRequest = {
            "target_locale": "es",
            "source_locale": "en",
            "fast": True,
        }
        assert request["target_locale"] == "es"
        assert request["source_locale"] == "en"
        assert request["fast"] is True

    def test_batch_localization_request_typing(self):
        """Test BatchLocalizationRequest TypedDict"""
        request: BatchLocalizationRequest = {
            "target_locales": ["es", "fr"],
            "source_locale": "en",
        }
        assert request["target_locales"] == ["es", "fr"]
        assert request["source_locale"] == "en"

    def test_chat_message_typing(self):
        """Test ChatMessage TypedDict"""
        message: ChatMessage = {
            "name": "Alice",
            "text": "Hello world!",
        }
        assert message["name"] == "Alice"
        assert message["text"] == "Hello world!"

    def test_engine_config_dict_typing(self):
        """Test EngineConfigDict TypedDict"""
        config: EngineConfigDict = {
            "api_key": "test_key_12345",
            "api_url": "https://api.test.com",
            "timeout": 60.0,
        }
        assert config["api_key"] == "test_key_12345"
        assert config["api_url"] == "https://api.test.com"
        assert config["timeout"] == 60.0

    def test_retry_config_typing(self):
        """Test RetryConfig TypedDict"""
        config: RetryConfig = {
            "max_retries": 5,
            "backoff_factor": 1.0,
            "jitter": False,
        }
        assert config["max_retries"] == 5
        assert config["backoff_factor"] == 1.0
        assert config["jitter"] is False


class TestBackwardCompatibility:
    """Test that enhanced types maintain backward compatibility"""

    def test_dict_config_still_works(self):
        """Test that dictionary configuration still works"""
        # This should work without requiring Pydantic models
        config_dict = {
            "api_key": "test_key_12345",
            "api_url": "https://api.test.com",
            "batch_size": 50,
        }
        
        # Should be able to create EnhancedEngineConfig from dict
        config = EnhancedEngineConfig(**config_dict)
        assert config.api_key == "test_key_12345"
        assert config.api_url == "https://api.test.com"
        assert config.batch_size == 50

    def test_optional_fields_work(self):
        """Test that optional fields work as expected"""
        # Minimal configuration should work
        config = EnhancedEngineConfig(api_key="test_key_12345")
        assert config.api_key == "test_key_12345"
        assert config.retry_config is not None
        
        # Disabling retry should work
        config_no_retry = EnhancedEngineConfig(
            api_key="test_key_12345", 
            retry_config=None
        )
        assert config_no_retry.retry_config is None