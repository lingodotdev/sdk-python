"""
Tests for the enhanced exception hierarchy
"""

import time
import pytest
from unittest.mock import Mock

from lingodotdev.exceptions import (
    LingoDevError,
    LingoDevAPIError,
    LingoDevNetworkError,
    LingoDevRetryExhaustedError,
    LingoDevValidationError,
    LingoDevConfigurationError,
    LingoDevTimeoutError,
    create_api_error_from_response,
    create_network_error_from_exception,
)
from lingodotdev.types import RetryContext


class TestLingoDevError:
    """Test the base LingoDevError class"""

    def test_basic_error(self):
        """Test basic error creation"""
        error = LingoDevError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.details == {}
        assert error.suggestions == []
        assert isinstance(error.timestamp, float)
        assert error.timestamp <= time.time()

    def test_error_with_details(self):
        """Test error with additional details"""
        details = {"request_id": "123", "user_id": "456"}
        error = LingoDevError("Test error", details=details)
        
        assert error.details == details
        assert "Details: {'request_id': '123', 'user_id': '456'}" in str(error)

    def test_error_with_suggestions(self):
        """Test error with suggestions"""
        suggestions = ["Try again", "Check your configuration"]
        error = LingoDevError("Test error", suggestions=suggestions)
        
        assert error.suggestions == suggestions
        error_str = str(error)
        assert "Suggestions:" in error_str
        assert "• Try again" in error_str
        assert "• Check your configuration" in error_str

    def test_error_with_sensitive_details(self):
        """Test that sensitive details are filtered from string representation"""
        details = {
            "api_key": "secret_key",
            "authorization": "Bearer token",
            "password": "secret",
            "safe_info": "visible"
        }
        error = LingoDevError("Test error", details=details)
        
        error_str = str(error)
        assert "secret_key" not in error_str
        assert "Bearer token" not in error_str
        assert "secret" not in error_str
        assert "safe_info" in error_str

    def test_to_dict(self):
        """Test error serialization to dictionary"""
        details = {"key": "value"}
        suggestions = ["suggestion1", "suggestion2"]
        error = LingoDevError("Test error", details=details, suggestions=suggestions)
        
        error_dict = error.to_dict()
        
        assert error_dict["error_type"] == "LingoDevError"
        assert error_dict["message"] == "Test error"
        assert error_dict["details"] == details
        assert error_dict["suggestions"] == suggestions
        assert "timestamp" in error_dict
        assert "context" in error_dict


class TestLingoDevAPIError:
    """Test the LingoDevAPIError class"""

    def test_api_error_basic(self):
        """Test basic API error creation"""
        error = LingoDevAPIError("API failed", 500, "Internal Server Error")
        
        assert error.status_code == 500
        assert error.response_text == "Internal Server Error"
        assert error.message == "API failed"

    def test_api_error_401_suggestions(self):
        """Test that 401 errors get appropriate suggestions"""
        error = LingoDevAPIError("Unauthorized", 401, "Invalid credentials")
        
        suggestions = error.suggestions
        assert any("API key" in suggestion for suggestion in suggestions)
        assert any("api_" in suggestion for suggestion in suggestions)

    def test_api_error_429_suggestions(self):
        """Test that 429 errors get rate limit suggestions"""
        error = LingoDevAPIError("Rate limited", 429, "Too many requests")
        
        suggestions = error.suggestions
        assert any("rate limit" in suggestion.lower() for suggestion in suggestions)
        assert any("backoff" in suggestion.lower() for suggestion in suggestions)

    def test_api_error_500_suggestions(self):
        """Test that 5xx errors get server error suggestions"""
        error = LingoDevAPIError("Server error", 503, "Service unavailable")
        
        suggestions = error.suggestions
        assert any("server error" in suggestion.lower() for suggestion in suggestions)
        assert any("try again" in suggestion.lower() for suggestion in suggestions)

    def test_api_error_400_locale_suggestions(self):
        """Test that 400 errors with locale issues get specific suggestions"""
        error = LingoDevAPIError("Bad request", 400, "Invalid locale code")
        
        suggestions = error.suggestions
        assert any("locale" in suggestion.lower() for suggestion in suggestions)

    def test_is_retryable(self):
        """Test retryable error detection"""
        # Retryable errors
        assert LingoDevAPIError("Rate limited", 429, "").is_retryable
        assert LingoDevAPIError("Server error", 500, "").is_retryable
        assert LingoDevAPIError("Bad gateway", 502, "").is_retryable
        assert LingoDevAPIError("Service unavailable", 503, "").is_retryable
        assert LingoDevAPIError("Gateway timeout", 504, "").is_retryable
        
        # Non-retryable errors
        assert not LingoDevAPIError("Bad request", 400, "").is_retryable
        assert not LingoDevAPIError("Unauthorized", 401, "").is_retryable
        assert not LingoDevAPIError("Not found", 404, "").is_retryable

    def test_is_client_error(self):
        """Test client error detection"""
        assert LingoDevAPIError("Bad request", 400, "").is_client_error
        assert LingoDevAPIError("Unauthorized", 401, "").is_client_error
        assert LingoDevAPIError("Not found", 404, "").is_client_error
        assert not LingoDevAPIError("Server error", 500, "").is_client_error

    def test_is_server_error(self):
        """Test server error detection"""
        assert LingoDevAPIError("Server error", 500, "").is_server_error
        assert LingoDevAPIError("Bad gateway", 502, "").is_server_error
        assert not LingoDevAPIError("Bad request", 400, "").is_server_error

    def test_with_request_details(self):
        """Test API error with request details"""
        request_details = {
            "method": "POST",
            "url": "https://api.example.com/test",
            "headers": {"Content-Type": "application/json"}
        }
        
        error = LingoDevAPIError(
            "API failed", 
            500, 
            "Server error",
            request_details=request_details
        )
        
        assert error.request_details == request_details
        assert error.context["method"] == "POST"
        assert error.context["url"] == "https://api.example.com/test"


class TestLingoDevNetworkError:
    """Test the LingoDevNetworkError class"""

    def test_network_error_basic(self):
        """Test basic network error creation"""
        original_error = ConnectionError("Connection failed")
        error = LingoDevNetworkError("Network issue", original_error)
        
        assert error.original_error == original_error
        assert error.message == "Network issue"
        assert error.is_retryable

    def test_timeout_suggestions(self):
        """Test timeout-specific suggestions"""
        original_error = TimeoutError("Request timed out")
        error = LingoDevNetworkError("Timeout occurred", original_error)
        
        suggestions = error.suggestions
        assert any("timeout" in suggestion.lower() for suggestion in suggestions)
        assert any("connection" in suggestion.lower() for suggestion in suggestions)

    def test_connection_suggestions(self):
        """Test connection-specific suggestions"""
        original_error = ConnectionError("Connection refused")
        error = LingoDevNetworkError("Connection failed", original_error)
        
        suggestions = error.suggestions
        assert any("connection" in suggestion.lower() for suggestion in suggestions)
        assert any("internet" in suggestion.lower() for suggestion in suggestions)

    def test_ssl_suggestions(self):
        """Test SSL-specific suggestions"""
        original_error = Exception("SSL certificate verification failed")
        error = LingoDevNetworkError("SSL error", original_error)
        
        suggestions = error.suggestions
        assert any("ssl" in suggestion.lower() or "certificate" in suggestion.lower() 
                  for suggestion in suggestions)

    def test_with_request_details(self):
        """Test network error with request details"""
        original_error = ConnectionError("Connection failed")
        request_details = {"url": "https://api.example.com/test"}
        
        error = LingoDevNetworkError(
            "Network issue", 
            original_error,
            request_details=request_details
        )
        
        assert error.request_details == request_details
        assert error.context["url"] == "https://api.example.com/test"


class TestLingoDevRetryExhaustedError:
    """Test the LingoDevRetryExhaustedError class"""

    def test_retry_exhausted_error(self):
        """Test retry exhausted error creation"""
        retry_context: RetryContext = {
            "attempt": 3,
            "max_attempts": 3,
            "last_exception": "ConnectionError",
            "total_elapsed": 45.5,
            "next_backoff": 0.0,
            "retry_history": []
        }
        
        last_error = ConnectionError("Final connection error")
        error = LingoDevRetryExhaustedError(
            "All retries failed", 
            retry_context, 
            last_error
        )
        
        assert error.retry_context == retry_context
        assert error.last_error == last_error
        assert error.total_attempts == 3
        assert error.total_elapsed_time == 45.5
        
        # Check suggestions mention retry attempts
        suggestions = error.suggestions
        assert any("3 retry attempts" in suggestion for suggestion in suggestions)

    def test_context_information(self):
        """Test that retry context is properly included"""
        retry_context: RetryContext = {
            "attempt": 5,
            "max_attempts": 5,
            "last_exception": "TimeoutError",
            "total_elapsed": 120.0,
            "next_backoff": 0.0,
            "retry_history": []
        }
        
        error = LingoDevRetryExhaustedError(
            "Retries exhausted", 
            retry_context, 
            TimeoutError("Timeout")
        )
        
        assert error.context["retry_attempt"] == 5
        assert error.context["total_attempts"] == 5
        assert error.context["total_elapsed"] == 120.0


class TestLingoDevValidationError:
    """Test the LingoDevValidationError class"""

    def test_validation_error_basic(self):
        """Test basic validation error"""
        error = LingoDevValidationError("Invalid parameter")
        
        assert error.message == "Invalid parameter"
        assert error.field_name is None
        assert error.invalid_value is None

    def test_validation_error_with_field(self):
        """Test validation error with field information"""
        error = LingoDevValidationError(
            "Invalid locale code",
            field_name="target_locale",
            invalid_value="invalid_code",
            valid_examples=["en", "es", "fr"]
        )
        
        assert error.field_name == "target_locale"
        assert error.invalid_value == "invalid_code"
        assert error.valid_examples == ["en", "es", "fr"]
        
        # Check suggestions include examples
        suggestions = error.suggestions
        assert any("en" in suggestion and "es" in suggestion for suggestion in suggestions)

    def test_validation_error_context(self):
        """Test validation error context"""
        error = LingoDevValidationError(
            "Invalid value",
            field_name="batch_size",
            invalid_value=0
        )
        
        assert error.context["field_name"] == "batch_size"
        assert error.context["invalid_value"] == "0"


class TestLingoDevConfigurationError:
    """Test the LingoDevConfigurationError class"""

    def test_configuration_error_basic(self):
        """Test basic configuration error"""
        error = LingoDevConfigurationError("Invalid configuration")
        
        assert error.message == "Invalid configuration"
        assert error.config_key is None

    def test_configuration_error_with_key(self):
        """Test configuration error with specific key"""
        error = LingoDevConfigurationError(
            "Invalid API key format",
            config_key="api_key"
        )
        
        assert error.config_key == "api_key"
        assert error.context["config_key"] == "api_key"
        
        # Check suggestions mention the config key
        suggestions = error.suggestions
        assert any("api_key" in suggestion for suggestion in suggestions)


class TestLingoDevTimeoutError:
    """Test the LingoDevTimeoutError class"""

    def test_timeout_error(self):
        """Test timeout error creation"""
        original_error = TimeoutError("Request timed out")
        error = LingoDevTimeoutError(
            "Operation timed out",
            timeout_duration=30.0,
            original_error=original_error
        )
        
        assert error.timeout_duration == 30.0
        assert error.original_error == original_error
        assert error.context["timeout_duration"] == 30.0
        
        # Check timeout-specific suggestions
        suggestions = error.suggestions
        assert any("30" in suggestion for suggestion in suggestions)
        assert any("timeout" in suggestion.lower() for suggestion in suggestions)


class TestUtilityFunctions:
    """Test utility functions for creating errors"""

    def test_create_api_error_from_response(self):
        """Test creating API error from HTTP response"""
        # Mock response object
        response = Mock()
        response.status_code = 401
        response.text = "Unauthorized access"
        
        request_details = {"method": "POST", "url": "https://api.test.com"}
        
        error = create_api_error_from_response(response, request_details)
        
        assert isinstance(error, LingoDevAPIError)
        assert error.status_code == 401
        assert error.response_text == "Unauthorized access"
        assert "Authentication failed" in error.message
        assert error.request_details == request_details

    def test_create_api_error_different_status_codes(self):
        """Test API error creation for different status codes"""
        test_cases = [
            (401, "Authentication failed"),
            (403, "Access forbidden"),
            (404, "API endpoint not found"),
            (429, "Rate limit exceeded"),
            (500, "Server error"),
            (418, "API request failed with status 418")  # Generic case
        ]
        
        for status_code, expected_message_part in test_cases:
            response = Mock()
            response.status_code = status_code
            response.text = f"Status {status_code} response"
            
            error = create_api_error_from_response(response)
            assert expected_message_part in error.message

    def test_create_network_error_from_exception(self):
        """Test creating network error from exception"""
        original_error = ConnectionError("Connection refused")
        request_details = {"url": "https://api.test.com"}
        
        error = create_network_error_from_exception(original_error, request_details)
        
        assert isinstance(error, LingoDevNetworkError)
        assert error.original_error == original_error
        assert "Connection failed" in error.message
        assert error.request_details == request_details

    def test_create_network_error_different_types(self):
        """Test network error creation for different exception types"""
        test_cases = [
            (TimeoutError("Timeout"), "Request timed out"),
            (ConnectionError("Connection failed"), "Connection failed"),
            (Exception("SSL error"), "SSL/TLS error"),
            (ValueError("Some other error"), "Network error occurred")
        ]
        
        for original_error, expected_message_part in test_cases:
            error = create_network_error_from_exception(original_error)
            assert expected_message_part in error.message

    def test_create_api_error_response_read_failure(self):
        """Test API error creation when response text can't be read"""
        response = Mock()
        response.status_code = 500
        response.text = Mock(side_effect=Exception("Can't read response"))
        
        error = create_api_error_from_response(response)
        
        assert error.response_text == "Unable to read response"


class TestErrorInheritance:
    """Test that error inheritance works correctly"""

    def test_all_errors_inherit_from_base(self):
        """Test that all custom errors inherit from LingoDevError"""
        errors = [
            LingoDevAPIError("test", 500),
            LingoDevNetworkError("test", Exception()),
            LingoDevRetryExhaustedError("test", {"attempt": 1, "max_attempts": 1, "last_exception": "test", "total_elapsed": 1.0, "next_backoff": 0.0, "retry_history": []}, Exception()),
            LingoDevValidationError("test"),
            LingoDevConfigurationError("test"),
            LingoDevTimeoutError("test", 30.0, TimeoutError()),
        ]
        
        for error in errors:
            assert isinstance(error, LingoDevError)
            assert isinstance(error, Exception)

    def test_error_catching(self):
        """Test that errors can be caught by base class"""
        try:
            raise LingoDevAPIError("API error", 500)
        except LingoDevError as e:
            assert isinstance(e, LingoDevAPIError)
            assert e.message == "API error"

    def test_specific_error_catching(self):
        """Test that specific errors can be caught individually"""
        try:
            raise LingoDevValidationError("Validation failed")
        except LingoDevValidationError as e:
            assert e.message == "Validation failed"
        except LingoDevError:
            pytest.fail("Should have caught specific ValidationError")


class TestErrorIntegration:
    """Test error integration with the broader system"""

    def test_error_serialization(self):
        """Test that errors can be properly serialized"""
        error = LingoDevAPIError(
            "API failed",
            500,
            "Server error",
            request_details={"method": "POST"},
            details={"request_id": "123"}
        )
        
        error_dict = error.to_dict()
        
        # Should be JSON serializable
        import json
        json_str = json.dumps(error_dict, default=str)
        assert "LingoDevAPIError" in json_str
        assert "API failed" in json_str

    def test_error_logging_format(self):
        """Test that errors format well for logging"""
        error = LingoDevValidationError(
            "Invalid locale code",
            field_name="target_locale",
            invalid_value="xyz",
            valid_examples=["en", "es", "fr"]
        )
        
        error_str = str(error)
        
        # Should contain all important information
        assert "Invalid locale code" in error_str
        assert "Suggestions:" in error_str
        assert "en" in error_str
        assert "target_locale" in error_str