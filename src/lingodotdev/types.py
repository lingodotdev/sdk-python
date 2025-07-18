"""
Type definitions for the Lingo.dev Python SDK

This module provides comprehensive type definitions that are compatible
with Python 3.8+ using typing_extensions for backward compatibility.
"""

from typing import Any, Callable, Dict, List, Optional, Union
from typing_extensions import TypedDict, NotRequired, Protocol

# Type variables for generic support
from typing import TypeVar

T = TypeVar('T')

# Core API request/response types
class LocalizationRequest(TypedDict):
    """Type definition for localization request parameters"""
    source_locale: NotRequired[Optional[str]]
    target_locale: str
    fast: NotRequired[Optional[bool]]
    reference: NotRequired[Optional[Dict[str, Dict[str, Any]]]]


class BatchLocalizationRequest(TypedDict):
    """Type definition for batch localization request parameters"""
    source_locale: NotRequired[Optional[str]]
    target_locales: List[str]
    fast: NotRequired[Optional[bool]]
    reference: NotRequired[Optional[Dict[str, Dict[str, Any]]]]


class ChatMessage(TypedDict):
    """Type definition for chat message structure"""
    name: str
    text: str


# Configuration types
class RetryConfig(TypedDict):
    """Type definition for retry configuration"""
    max_retries: NotRequired[int]  # default: 3
    backoff_factor: NotRequired[float]  # default: 0.5
    retry_statuses: NotRequired[List[int]]  # default: [429, 500, 502, 503, 504]
    max_backoff: NotRequired[float]  # default: 60.0
    jitter: NotRequired[bool]  # default: True


class EngineConfigDict(TypedDict):
    """Type definition for engine configuration dictionary"""
    api_key: str
    api_url: NotRequired[str]
    batch_size: NotRequired[int]
    ideal_batch_item_size: NotRequired[int]
    timeout: NotRequired[float]
    retry_config: NotRequired[Union[RetryConfig, None]]


# Protocol definitions for callbacks
class ProgressCallback(Protocol):
    """Protocol for progress callback functions with chunk information"""
    def __call__(
        self, 
        progress: int, 
        source_chunk: Dict[str, str], 
        processed_chunk: Dict[str, str]
    ) -> None:
        """
        Progress callback with detailed chunk information
        
        Args:
            progress: Completion percentage (0-100)
            source_chunk: The source chunk being processed
            processed_chunk: The processed/translated chunk
        """
        ...


class SimpleProgressCallback(Protocol):
    """Protocol for simple progress callback functions"""
    def __call__(self, progress: int) -> None:
        """
        Simple progress callback
        
        Args:
            progress: Completion percentage (0-100)
        """
        ...


# API response types
class APIResponse(TypedDict):
    """Type definition for API response structure"""
    data: NotRequired[Optional[Dict[str, Any]]]
    error: NotRequired[Optional[str]]


class WhoAmIResponse(TypedDict):
    """Type definition for whoami API response"""
    email: str
    id: str


# Internal processing types
class ChunkRequest(TypedDict):
    """Type definition for internal chunk processing requests"""
    params: Dict[str, Any]
    locale: Dict[str, Optional[str]]
    data: Dict[str, Any]
    reference: NotRequired[Optional[Dict[str, Dict[str, Any]]]]


# Error context types
class ErrorContext(TypedDict):
    """Type definition for error context information"""
    timestamp: float
    request_id: NotRequired[Optional[str]]
    method: NotRequired[Optional[str]]
    url: NotRequired[Optional[str]]
    status_code: NotRequired[Optional[int]]
    retry_attempt: NotRequired[Optional[int]]
    total_attempts: NotRequired[Optional[int]]


class RetryContext(TypedDict):
    """Type definition for retry context information"""
    attempt: int
    max_attempts: int
    last_exception: str  # Exception type name
    total_elapsed: float
    next_backoff: float
    retry_history: List[Dict[str, Any]]


# Export all types for easy importing
__all__ = [
    # Request/Response types
    "LocalizationRequest",
    "BatchLocalizationRequest", 
    "ChatMessage",
    "APIResponse",
    "WhoAmIResponse",
    
    # Configuration types
    "RetryConfig",
    "EngineConfigDict",
    
    # Protocol types
    "ProgressCallback",
    "SimpleProgressCallback",
    
    # Internal types
    "ChunkRequest",
    "ErrorContext",
    "RetryContext",
    
    # Generic type variable
    "T",
]