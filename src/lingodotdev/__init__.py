"""
Lingo.dev Python SDK

A powerful localization engine that supports various content types including
plain text, objects, chat sequences, and HTML documents.

Enhanced with comprehensive type safety, async/await support, and robust error handling.
"""

__version__ = "1.0.4"

from .engine import LingoDotDevEngine

# Import types for public API (optional, for advanced users)
from .types import (
    LocalizationRequest,
    BatchLocalizationRequest,
    ChatMessage,
    RetryConfig,
    EngineConfigDict,
    ProgressCallback,
    SimpleProgressCallback,
)

from .models import (
    EnhancedEngineConfig,
    LocalizationParams,
    BatchLocalizationParams,
    ChatMessageModel,
    RetryConfiguration,
)

# Import exceptions for public API
from .exceptions import (
    LingoDevError,
    LingoDevAPIError,
    LingoDevNetworkError,
    LingoDevRetryExhaustedError,
    LingoDevValidationError,
    LingoDevConfigurationError,
    LingoDevTimeoutError,
)

# Import retry components for public API
from .retry import (
    RetryHandler,
    AsyncRetryHandler,
    with_retry,
    with_async_retry,
)

# Import async client for public API
from .async_client import (
    AsyncHTTPClient,
    create_async_client,
)

# Main public API - maintain backward compatibility
__all__ = [
    # Core engine class
    "LingoDotDevEngine",
    
    # Type definitions (for advanced users who want type safety)
    "LocalizationRequest",
    "BatchLocalizationRequest", 
    "ChatMessage",
    "RetryConfig",
    "EngineConfigDict",
    "ProgressCallback",
    "SimpleProgressCallback",
    
    # Pydantic models (for advanced configuration)
    "EnhancedEngineConfig",
    "LocalizationParams", 
    "BatchLocalizationParams",
    "ChatMessageModel",
    "RetryConfiguration",
    
    # Exception classes
    "LingoDevError",
    "LingoDevAPIError", 
    "LingoDevNetworkError",
    "LingoDevRetryExhaustedError",
    "LingoDevValidationError",
    "LingoDevConfigurationError",
    "LingoDevTimeoutError",
    
    # Retry components
    "RetryHandler",
    "AsyncRetryHandler",
    "with_retry",
    "with_async_retry",
    
    # Async HTTP client
    "AsyncHTTPClient",
    "create_async_client",
]
