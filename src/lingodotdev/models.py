"""
Enhanced Pydantic models for the Lingo.dev Python SDK

This module provides comprehensive data validation and configuration models
using Pydantic v2 with backward compatibility for Python 3.8+.
"""

from typing import Any, Dict, List, Optional, Set, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
import time


class RetryConfiguration(BaseModel):
    """Configuration model for retry behavior with comprehensive validation"""
    
    model_config = ConfigDict(
        # Allow extra fields for future extensibility
        extra='forbid',
        # Validate assignment to catch runtime errors
        validate_assignment=True,
        # Use enum values for better serialization
        use_enum_values=True
    )
    
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts"
    )
    
    backoff_factor: float = Field(
        default=0.5,
        ge=0.1,
        le=2.0,
        description="Exponential backoff multiplier"
    )
    
    retry_statuses: Set[int] = Field(
        default={429, 500, 502, 503, 504},
        description="HTTP status codes that should trigger retries"
    )
    
    max_backoff: float = Field(
        default=60.0,
        ge=1.0,
        le=300.0,
        description="Maximum backoff time in seconds"
    )
    
    jitter: bool = Field(
        default=True,
        description="Whether to add random jitter to backoff times"
    )
    
    @field_validator("retry_statuses")
    @classmethod
    def validate_retry_statuses(cls, v: Set[int]) -> Set[int]:
        """Validate that retry status codes are valid HTTP status codes"""
        valid_statuses = set(range(400, 600))  # 4xx and 5xx status codes
        invalid_statuses = v - valid_statuses
        if invalid_statuses:
            raise ValueError(
                f"Invalid HTTP status codes for retry: {invalid_statuses}. "
                f"Only 4xx and 5xx status codes are allowed."
            )
        return v


class EnhancedEngineConfig(BaseModel):
    """Enhanced configuration model for the LingoDotDevEngine"""
    
    model_config = ConfigDict(
        extra='forbid',
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    api_key: str = Field(
        description="Lingo.dev API key",
        min_length=1
    )
    
    api_url: str = Field(
        default="https://engine.lingo.dev",
        description="Base URL for the Lingo.dev API"
    )
    
    batch_size: int = Field(
        default=25,
        ge=1,
        le=250,
        description="Maximum number of items per batch"
    )
    
    ideal_batch_item_size: int = Field(
        default=250,
        ge=1,
        le=2500,
        description="Ideal number of words per batch item"
    )
    
    timeout: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Request timeout in seconds"
    )
    
    retry_config: Optional[RetryConfiguration] = Field(
        default_factory=RetryConfiguration,
        description="Retry configuration (None to disable retries)"
    )
    
    @field_validator("api_url")
    @classmethod
    def validate_api_url(cls, v: str) -> str:
        """Validate that API URL is a valid HTTP/HTTPS URL"""
        if not v.startswith(("http://", "https://")):
            raise ValueError(
                "API URL must be a valid HTTP/HTTPS URL. "
                f"Got: {v}"
            )
        return v.rstrip('/')  # Remove trailing slash for consistency
    
    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format and provide helpful error messages"""
        if not v or v.isspace():
            raise ValueError(
                "API key cannot be empty. "
                "Please provide a valid Lingo.dev API key."
            )
        
        # Basic format validation (adjust based on actual API key format)
        if len(v) < 10:
            raise ValueError(
                "API key appears to be too short. "
                "Please check that you have provided the complete API key."
            )
        
        return v


class LocalizationParams(BaseModel):
    """Enhanced parameters model for localization requests"""
    
    model_config = ConfigDict(
        extra='forbid',
        validate_assignment=True
    )
    
    source_locale: Optional[str] = Field(
        default=None,
        description="Source language code (e.g., 'en')"
    )
    
    target_locale: str = Field(
        description="Target language code (e.g., 'es')",
        min_length=1
    )
    
    fast: Optional[bool] = Field(
        default=None,
        description="Enable fast processing mode"
    )
    
    reference: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None,
        description="Reference translations for consistency"
    )
    
    @field_validator("source_locale", "target_locale")
    @classmethod
    def validate_locale_codes(cls, v: Optional[str]) -> Optional[str]:
        """Validate locale code format"""
        if v is None:
            return v
        
        if not v or v.isspace():
            raise ValueError("Locale code cannot be empty")
        
        # Basic locale code validation (2-5 characters, letters and hyphens)
        if not (2 <= len(v) <= 5) or not all(c.isalpha() or c == '-' for c in v):
            raise ValueError(
                f"Invalid locale code format: '{v}'. "
                "Locale codes should be 2-5 characters (e.g., 'en', 'es', 'en-US')"
            )
        
        return v.lower()  # Normalize to lowercase


class BatchLocalizationParams(BaseModel):
    """Enhanced parameters model for batch localization requests"""
    
    model_config = ConfigDict(
        extra='forbid',
        validate_assignment=True
    )
    
    source_locale: Optional[str] = Field(
        default=None,
        description="Source language code (e.g., 'en')"
    )
    
    target_locales: List[str] = Field(
        description="List of target language codes",
        min_length=1
    )
    
    fast: Optional[bool] = Field(
        default=None,
        description="Enable fast processing mode"
    )
    
    reference: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None,
        description="Reference translations for consistency"
    )
    
    @field_validator("source_locale")
    @classmethod
    def validate_source_locale(cls, v: Optional[str]) -> Optional[str]:
        """Validate source locale code format"""
        return LocalizationParams.validate_locale_codes(v)
    
    @field_validator("target_locales")
    @classmethod
    def validate_target_locales(cls, v: List[str]) -> List[str]:
        """Validate target locale codes and check for duplicates"""
        if not v:
            raise ValueError("At least one target locale must be specified")
        
        # Validate each locale code
        validated_locales = []
        for locale in v:
            validated_locale = LocalizationParams.validate_locale_codes(locale)
            if validated_locale:
                validated_locales.append(validated_locale)
        
        # Check for duplicates
        if len(validated_locales) != len(set(validated_locales)):
            duplicates = [x for x in validated_locales if validated_locales.count(x) > 1]
            raise ValueError(f"Duplicate target locales found: {list(set(duplicates))}")
        
        return validated_locales


class ChatMessageModel(BaseModel):
    """Enhanced model for chat message validation"""
    
    model_config = ConfigDict(
        extra='forbid',
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    name: str = Field(
        description="Speaker name",
        min_length=1,
        max_length=100
    )
    
    text: str = Field(
        description="Message text",
        min_length=1
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate speaker name"""
        if not v or v.isspace():
            raise ValueError("Speaker name cannot be empty")
        return v
    
    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate message text"""
        if not v or v.isspace():
            raise ValueError("Message text cannot be empty")
        return v


class ErrorInfo(BaseModel):
    """Model for structured error information"""
    
    model_config = ConfigDict(
        extra='allow',  # Allow extra fields for extensibility
        validate_assignment=True
    )
    
    message: str = Field(description="Error message")
    error_type: str = Field(description="Error type/category")
    timestamp: float = Field(default_factory=time.time, description="Error timestamp")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    
    # Optional fields for API errors
    status_code: Optional[int] = Field(default=None, description="HTTP status code")
    response_text: Optional[str] = Field(default=None, description="API response text")
    
    # Optional fields for retry errors
    retry_attempts: Optional[int] = Field(default=None, description="Number of retry attempts made")
    total_elapsed: Optional[float] = Field(default=None, description="Total time elapsed during retries")


# Export all models
__all__ = [
    "RetryConfiguration",
    "EnhancedEngineConfig", 
    "LocalizationParams",
    "BatchLocalizationParams",
    "ChatMessageModel",
    "ErrorInfo",
]