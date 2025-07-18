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
]
