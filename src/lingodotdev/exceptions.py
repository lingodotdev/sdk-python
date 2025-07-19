"""
Custom exception hierarchy for the Lingo.dev Python SDK

This module provides comprehensive error handling with structured exceptions
that include context, suggestions, and proper error classification.
"""

import time
from typing import Any, Dict, List, Optional, Union
from .types import ErrorContext, RetryContext


class LingoDevError(Exception):
    """
    Base exception for all Lingo.dev SDK errors
    
    Provides structured error information with context and timestamps
    for better debugging and error handling.
    """
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.suggestions = suggestions or []
        self.timestamp = time.time()
        
        # Add error context
        self.context: ErrorContext = {
            "timestamp": self.timestamp,
        }
    
    def __str__(self) -> str:
        """Enhanced string representation with context"""
        base_msg = self.message
        
        if self.suggestions:
            suggestions_text = "\n".join(f"  • {suggestion}" for suggestion in self.suggestions)
            base_msg += f"\n\nSuggestions:\n{suggestions_text}"
        
        if self.details:
            # Only show non-sensitive details
            safe_details = {k: v for k, v in self.details.items() 
                          if k not in ['api_key', 'authorization', 'password']}
            if safe_details:
                base_msg += f"\n\nDetails: {safe_details}"
        
        return base_msg
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details,
            "suggestions": self.suggestions,
            "context": self.context,
        }


class LingoDevAPIError(LingoDevError):
    """
    API-related errors from the Lingo.dev service
    
    Includes HTTP status codes, response details, and request context
    for comprehensive API error handling.
    """
    
    def __init__(
        self, 
        message: str, 
        status_code: int, 
        response_text: str = "", 
        request_details: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        # Generate appropriate suggestions based on status code
        auto_suggestions = self._generate_suggestions(status_code, response_text)
        all_suggestions = (suggestions or []) + auto_suggestions
        
        super().__init__(message, details, all_suggestions)
        
        self.status_code = status_code
        self.response_text = response_text
        self.request_details = request_details or {}
        
        # Add API-specific context
        self.context.update({
            "status_code": status_code,
            "method": request_details.get("method") if request_details else None,
            "url": request_details.get("url") if request_details else None,
        })
    
    def _generate_suggestions(self, status_code: int, response_text: str) -> List[str]:
        """Generate helpful suggestions based on the error"""
        suggestions = []
        
        if status_code == 401:
            suggestions.extend([
                "Check that your API key is correct and properly formatted",
                "Ensure the API key includes the 'api_' prefix",
                "Verify that your API key hasn't expired",
                "Make sure you're using the correct API endpoint"
            ])
        elif status_code == 403:
            suggestions.extend([
                "Check if your API key has the required permissions",
                "Verify that your account has access to the requested feature",
                "Contact support if you believe this is an error"
            ])
        elif status_code == 429:
            suggestions.extend([
                "You've hit the rate limit - wait before making more requests",
                "Consider implementing exponential backoff in your retry logic",
                "Check if you can optimize your request patterns"
            ])
        elif 500 <= status_code < 600:
            suggestions.extend([
                "This is a server error - try again in a few moments",
                "If the problem persists, check the Lingo.dev status page",
                "Consider implementing retry logic for transient failures"
            ])
        elif status_code == 400:
            # Handle case where response_text might be a Mock object
            try:
                response_text_str = str(response_text).lower()
                if "locale" in response_text_str:
                    suggestions.append("Check that your locale codes are valid (e.g., 'en', 'es', 'fr')")
                if "format" in response_text_str:
                    suggestions.append("Verify that your request data is properly formatted")
            except (TypeError, AttributeError):
                # If response_text is not a string or causes issues, skip specific suggestions
                suggestions.append("Check your request parameters and data format")
        
        return suggestions
    
    @property
    def is_retryable(self) -> bool:
        """Check if this error type should be retried"""
        # Retry server errors and rate limiting
        return self.status_code in {429, 500, 502, 503, 504}
    
    @property
    def is_client_error(self) -> bool:
        """Check if this is a client error (4xx)"""
        return 400 <= self.status_code < 500
    
    @property
    def is_server_error(self) -> bool:
        """Check if this is a server error (5xx)"""
        return 500 <= self.status_code < 600


class LingoDevNetworkError(LingoDevError):
    """
    Network-related errors (connection issues, timeouts, etc.)
    
    Wraps underlying network exceptions with additional context
    and suggestions for resolution.
    """
    
    def __init__(
        self, 
        message: str, 
        original_error: Exception, 
        request_details: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        # Generate network-specific suggestions
        suggestions = self._generate_network_suggestions(original_error)
        
        super().__init__(message, details, suggestions)
        
        self.original_error = original_error
        self.request_details = request_details or {}
        
        # Add network-specific context
        self.context.update({
            "original_error_type": type(original_error).__name__,
            "url": request_details.get("url") if request_details else None,
        })
    
    def _generate_network_suggestions(self, original_error: Exception) -> List[str]:
        """Generate suggestions based on the network error type"""
        error_type = type(original_error).__name__
        suggestions = []
        
        if "timeout" in error_type.lower() or "timeout" in str(original_error).lower():
            suggestions.extend([
                "The request timed out - check your internet connection",
                "Consider increasing the timeout value in your configuration",
                "Try again as this might be a temporary network issue"
            ])
        elif "connection" in error_type.lower() or "connection" in str(original_error).lower():
            suggestions.extend([
                "Unable to connect to the API - check your internet connection",
                "Verify that the API URL is correct",
                "Check if there are any firewall or proxy issues",
                "Try again as this might be a temporary connectivity issue"
            ])
        elif "ssl" in error_type.lower() or "certificate" in str(original_error).lower():
            suggestions.extend([
                "SSL/TLS certificate verification failed",
                "Check your system's certificate store",
                "Verify that your system clock is correct"
            ])
        else:
            suggestions.extend([
                "A network error occurred - check your internet connection",
                "Try again as this might be a temporary issue",
                "If the problem persists, check your network configuration"
            ])
        
        return suggestions
    
    @property
    def is_retryable(self) -> bool:
        """Network errors are generally retryable"""
        return True


class LingoDevRetryExhaustedError(LingoDevError):
    """
    Raised when all retry attempts have been exhausted
    
    Includes detailed information about retry attempts and the final error
    that caused the failure.
    """
    
    def __init__(
        self, 
        message: str, 
        retry_context: RetryContext,
        last_error: Exception,
        details: Optional[Dict[str, Any]] = None
    ):
        suggestions = [
            f"All {retry_context['max_attempts']} retry attempts failed",
            "Check your network connection and API configuration",
            "Consider increasing the retry limit or backoff time",
            "If this persists, there may be a service outage"
        ]
        
        super().__init__(message, details, suggestions)
        
        self.retry_context = retry_context
        self.last_error = last_error
        
        # Add retry-specific context
        self.context.update({
            "retry_attempt": retry_context["attempt"],
            "total_attempts": retry_context["max_attempts"],
            "total_elapsed": retry_context["total_elapsed"],
        })
    
    @property
    def total_attempts(self) -> int:
        """Total number of retry attempts made"""
        return self.retry_context["attempt"]
    
    @property
    def total_elapsed_time(self) -> float:
        """Total time elapsed during all retry attempts"""
        return self.retry_context["total_elapsed"]


class LingoDevValidationError(LingoDevError):
    """
    Input validation errors for parameters, configuration, etc.
    
    Provides specific guidance on how to fix validation issues.
    """
    
    def __init__(
        self, 
        message: str, 
        field_name: Optional[str] = None,
        invalid_value: Any = None,
        valid_examples: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        suggestions = []
        
        if field_name and valid_examples:
            examples_text = "', '".join(valid_examples)
            suggestions.append(f"Valid {field_name} examples: '{examples_text}'")
        
        if field_name:
            suggestions.append(f"Check the '{field_name}' parameter in your request")
        
        suggestions.append("Refer to the API documentation for valid parameter formats")
        
        super().__init__(message, details, suggestions)
        
        self.field_name = field_name
        self.invalid_value = invalid_value
        self.valid_examples = valid_examples or []
        
        # Add validation-specific context
        if field_name:
            self.context.update({
                "field_name": field_name,
                "invalid_value": str(invalid_value) if invalid_value is not None else None,
            })


class LingoDevConfigurationError(LingoDevError):
    """
    Configuration-related errors (invalid settings, missing required config, etc.)
    
    Helps users identify and fix configuration issues.
    """
    
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        suggestions = []
        
        if config_key:
            suggestions.append(f"Check the '{config_key}' configuration setting")
        
        suggestions.extend([
            "Verify your engine configuration parameters",
            "Ensure all required configuration values are provided",
            "Check the documentation for valid configuration options"
        ])
        
        super().__init__(message, details, suggestions)
        
        self.config_key = config_key
        
        if config_key:
            self.context.update({
                "config_key": config_key,
            })


class LingoDevTimeoutError(LingoDevNetworkError):
    """
    Specific timeout error with timeout-focused suggestions
    """
    
    def __init__(
        self, 
        message: str, 
        timeout_duration: float,
        original_error: Exception,
        request_details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, original_error, request_details)
        
        self.timeout_duration = timeout_duration
        
        # Override with timeout-specific suggestions
        self.suggestions = [
            f"Request timed out after {timeout_duration} seconds",
            "Consider increasing the timeout value in your configuration",
            "Check your network connection speed",
            "Large requests may need longer timeout values",
            "Try breaking large requests into smaller chunks"
        ]
        
        self.context.update({
            "timeout_duration": timeout_duration,
        })


# Utility functions for error handling
def create_api_error_from_response(
    response, 
    request_details: Optional[Dict[str, Any]] = None
) -> LingoDevAPIError:
    """
    Create an appropriate API error from an HTTP response
    
    Args:
        response: HTTP response object
        request_details: Optional request context
        
    Returns:
        LingoDevAPIError with appropriate message and context
    """
    status_code = response.status_code
    
    try:
        response_text = response.text
        # Handle case where response.text is a Mock or callable
        if callable(response_text):
            response_text = response_text()
    except Exception:
        response_text = "Unable to read response"
    
    # Create appropriate error message
    if status_code == 401:
        message = "Authentication failed - invalid or expired API key"
    elif status_code == 403:
        message = "Access forbidden - insufficient permissions"
    elif status_code == 404:
        message = "API endpoint not found"
    elif status_code == 429:
        message = "Rate limit exceeded - too many requests"
    elif 500 <= status_code < 600:
        message = f"Server error ({status_code}) - service temporarily unavailable"
    else:
        message = f"API request failed with status {status_code}"
    
    return LingoDevAPIError(
        message=message,
        status_code=status_code,
        response_text=response_text,
        request_details=request_details
    )


def create_network_error_from_exception(
    original_error: Exception,
    request_details: Optional[Dict[str, Any]] = None
) -> LingoDevNetworkError:
    """
    Create an appropriate network error from an exception
    
    Args:
        original_error: The original network exception
        request_details: Optional request context
        
    Returns:
        LingoDevNetworkError with appropriate message and context
    """
    error_type = type(original_error).__name__
    error_str = str(original_error)
    
    if "timeout" in error_type.lower() or "timeout" in error_str.lower():
        message = "Request timed out - network or server response too slow"
    elif "connection" in error_type.lower():
        message = "Connection failed - unable to reach the API server"
    elif "ssl" in error_type.lower() or "ssl" in error_str.lower() or "certificate" in error_str.lower():
        message = "SSL/TLS error - certificate verification failed"
    else:
        message = f"Network error occurred: {error_str}"
    
    return LingoDevNetworkError(
        message=message,
        original_error=original_error,
        request_details=request_details
    )


# Export all exception classes
__all__ = [
    # Base exception
    "LingoDevError",
    
    # Specific exception types
    "LingoDevAPIError",
    "LingoDevNetworkError", 
    "LingoDevRetryExhaustedError",
    "LingoDevValidationError",
    "LingoDevConfigurationError",
    "LingoDevTimeoutError",
    
    # Utility functions
    "create_api_error_from_response",
    "create_network_error_from_exception",
]