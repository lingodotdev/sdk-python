"""
Retry handler implementation for the Lingo.dev Python SDK

This module provides comprehensive retry logic with exponential backoff,
jitter, and intelligent error classification for both sync and async operations.
"""

import asyncio
import random
import time
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar, Union
from .types import RetryContext
from .exceptions import (
    LingoDevError,
    LingoDevAPIError,
    LingoDevNetworkError,
    LingoDevRetryExhaustedError,
    create_api_error_from_response,
    create_network_error_from_exception,
)
from .models import RetryConfiguration

# Type variables for generic retry functions
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

# Set up logging
logger = logging.getLogger(__name__)


class RetryHandler:
    """
    Handles retry logic with exponential backoff for synchronous operations
    
    Provides intelligent retry decisions based on error types, configurable
    backoff strategies, and comprehensive retry context tracking.
    """
    
    def __init__(self, config: Optional[RetryConfiguration] = None):
        """
        Initialize retry handler with configuration
        
        Args:
            config: Retry configuration, uses defaults if None
        """
        self.config = config or RetryConfiguration()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if an exception should trigger a retry
        
        Args:
            exception: The exception that occurred
            attempt: Current attempt number (1-based)
            
        Returns:
            True if the operation should be retried
        """
        # Don't retry if we've reached max attempts (attempt is 1-based)
        if attempt >= self.config.max_retries:
            return False
        
        # Check if it's a retryable LingoDevError
        if isinstance(exception, LingoDevAPIError):
            return exception.is_retryable
        
        if isinstance(exception, LingoDevNetworkError):
            return exception.is_retryable
        
        # Handle requests library exceptions
        try:
            import requests
            if isinstance(exception, requests.exceptions.RequestException):
                # Retry on connection errors, timeouts, and server errors
                if isinstance(exception, (
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.ConnectTimeout,
                    requests.exceptions.ReadTimeout
                )):
                    return True
                
                # Check HTTP status codes for HTTPError
                if isinstance(exception, requests.exceptions.HTTPError):
                    if hasattr(exception, 'response') and exception.response:
                        status_code = exception.response.status_code
                        return status_code in self.config.retry_statuses
                
                return False
        except ImportError:
            pass
        
        # Handle standard Python exceptions
        if isinstance(exception, (ConnectionError, TimeoutError)):
            return True
        
        # Don't retry other exceptions by default
        return False
    
    def calculate_backoff(self, attempt: int) -> float:
        """
        Calculate backoff time with exponential backoff and optional jitter
        
        Args:
            attempt: Current attempt number (1-based)
            
        Returns:
            Backoff time in seconds
        """
        # Calculate exponential backoff: backoff_factor * (2 ^ (attempt - 1))
        backoff = self.config.backoff_factor * (2 ** (attempt - 1))
        
        # Apply maximum backoff limit
        backoff = min(backoff, self.config.max_backoff)
        
        # Add jitter if enabled
        if self.config.jitter:
            # Add random jitter up to 25% of the backoff time
            jitter = backoff * 0.25 * random.random()
            backoff += jitter
        
        return backoff
    
    def execute_with_retry(
        self,
        func: Callable[..., T],
        *args,
        retry_callback: Optional[Callable[[int, Exception, float], None]] = None,
        **kwargs
    ) -> T:
        """
        Execute a function with retry logic
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            retry_callback: Optional callback for retry events
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function execution
            
        Raises:
            LingoDevRetryExhaustedError: When all retry attempts are exhausted
        """
        retry_history: List[Dict[str, Any]] = []
        start_time = time.time()
        
        max_attempts = max(1, self.config.max_retries)  # Ensure at least 1 attempt
        for attempt in range(1, max_attempts + 1):
            try:
                self.logger.debug(f"Executing function (attempt {attempt}/{max_attempts})")
                result = func(*args, **kwargs)
                
                # Log successful execution after retries
                if attempt > 1:
                    elapsed = time.time() - start_time
                    self.logger.info(
                        f"Function succeeded on attempt {attempt}/{self.config.max_retries} "
                        f"after {elapsed:.2f}s"
                    )
                
                return result
                
            except Exception as e:
                attempt_time = time.time()
                elapsed = attempt_time - start_time
                
                # Convert to appropriate LingoDevError if needed
                if not isinstance(e, LingoDevError):
                    if hasattr(e, 'response'):  # HTTP error
                        e = create_api_error_from_response(e.response)
                    else:  # Network or other error
                        e = create_network_error_from_exception(e)
                
                # Record retry attempt
                retry_record = {
                    "attempt": attempt,
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                    "timestamp": attempt_time,
                    "elapsed": elapsed,
                }
                retry_history.append(retry_record)
                
                # Check if we should retry
                should_retry = self.should_retry(e, attempt)
                
                if not should_retry or attempt >= max_attempts:
                    # Create retry context for the final error
                    retry_context: RetryContext = {
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "last_exception": type(e).__name__,
                        "total_elapsed": elapsed,
                        "next_backoff": 0.0,
                        "retry_history": retry_history,
                    }
                    
                    self.logger.error(
                        f"All retry attempts exhausted. Final attempt {attempt}/{max_attempts}, "
                        f"total elapsed: {elapsed:.2f}s"
                    )
                    
                    raise LingoDevRetryExhaustedError(
                        f"Operation failed after {attempt} attempts over {elapsed:.2f}s",
                        retry_context,
                        e
                    )
                
                # Calculate backoff time
                backoff_time = self.calculate_backoff(attempt)
                retry_record["backoff_time"] = backoff_time
                
                self.logger.warning(
                    f"Attempt {attempt}/{max_attempts} failed: {e}. "
                    f"Retrying in {backoff_time:.2f}s"
                )
                
                # Call retry callback if provided
                if retry_callback:
                    try:
                        retry_callback(attempt, e, backoff_time)
                    except Exception as callback_error:
                        self.logger.warning(f"Retry callback failed: {callback_error}")
                
                # Wait before retrying
                time.sleep(backoff_time)
        
        # This should never be reached due to the logic above, but just in case
        raise RuntimeError("Unexpected end of retry loop")


class AsyncRetryHandler:
    """
    Handles retry logic with exponential backoff for asynchronous operations
    
    Provides the same retry capabilities as RetryHandler but for async/await
    operations with proper asyncio integration.
    """
    
    def __init__(self, config: Optional[RetryConfiguration] = None):
        """
        Initialize async retry handler with configuration
        
        Args:
            config: Retry configuration, uses defaults if None
        """
        self.config = config or RetryConfiguration()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if an exception should trigger a retry (same logic as sync version)
        
        Args:
            exception: The exception that occurred
            attempt: Current attempt number (1-based)
            
        Returns:
            True if the operation should be retried
        """
        # Don't retry if we've reached max attempts (attempt is 1-based)
        if attempt >= self.config.max_retries:
            return False
        
        # Check if it's a retryable LingoDevError
        if isinstance(exception, LingoDevAPIError):
            return exception.is_retryable
        
        if isinstance(exception, LingoDevNetworkError):
            return exception.is_retryable
        
        # Handle aiohttp exceptions
        try:
            import aiohttp
            if isinstance(exception, aiohttp.ClientError):
                # Retry on connection errors and timeouts
                if isinstance(exception, (
                    aiohttp.ClientConnectionError,
                    aiohttp.ClientTimeout,
                    aiohttp.ServerTimeoutError,
                    aiohttp.ClientConnectorError
                )):
                    return True
                
                # Check HTTP status codes for ClientResponseError
                if isinstance(exception, aiohttp.ClientResponseError):
                    return exception.status in self.config.retry_statuses
                
                return False
        except ImportError:
            pass
        
        # Handle requests library exceptions (in case they're used in async context)
        try:
            import requests
            if isinstance(exception, requests.exceptions.RequestException):
                if isinstance(exception, (
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.ConnectTimeout,
                    requests.exceptions.ReadTimeout
                )):
                    return True
                
                if isinstance(exception, requests.exceptions.HTTPError):
                    if hasattr(exception, 'response') and exception.response:
                        status_code = exception.response.status_code
                        return status_code in self.config.retry_statuses
                
                return False
        except ImportError:
            pass
        
        # Handle standard Python exceptions
        if isinstance(exception, (ConnectionError, TimeoutError)):
            return True
        
        return False
    
    def calculate_backoff(self, attempt: int) -> float:
        """
        Calculate backoff time (same logic as sync version)
        
        Args:
            attempt: Current attempt number (1-based)
            
        Returns:
            Backoff time in seconds
        """
        backoff = self.config.backoff_factor * (2 ** (attempt - 1))
        backoff = min(backoff, self.config.max_backoff)
        
        if self.config.jitter:
            jitter = backoff * 0.25 * random.random()
            backoff += jitter
        
        return backoff
    
    async def execute_with_retry(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        retry_callback: Optional[Callable[[int, Exception, float], Awaitable[None]]] = None,
        **kwargs
    ) -> T:
        """
        Execute an async function with retry logic
        
        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            retry_callback: Optional async callback for retry events
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function execution
            
        Raises:
            LingoDevRetryExhaustedError: When all retry attempts are exhausted
        """
        retry_history: List[Dict[str, Any]] = []
        start_time = time.time()
        
        max_attempts = max(1, self.config.max_retries)  # Ensure at least 1 attempt
        for attempt in range(1, max_attempts + 1):
            try:
                self.logger.debug(f"Executing async function (attempt {attempt}/{max_attempts})")
                result = await func(*args, **kwargs)
                
                # Log successful execution after retries
                if attempt > 1:
                    elapsed = time.time() - start_time
                    self.logger.info(
                        f"Async function succeeded on attempt {attempt}/{self.config.max_retries} "
                        f"after {elapsed:.2f}s"
                    )
                
                return result
                
            except Exception as e:
                attempt_time = time.time()
                elapsed = attempt_time - start_time
                
                # Convert to appropriate LingoDevError if needed
                if not isinstance(e, LingoDevError):
                    # Handle aiohttp responses
                    if hasattr(e, 'status') and hasattr(e, 'message'):  # aiohttp error
                        # Create a mock response-like object for aiohttp errors
                        mock_response = type('MockResponse', (), {
                            'status_code': getattr(e, 'status', 500),
                            'text': str(e)
                        })()
                        e = create_api_error_from_response(mock_response)
                    elif hasattr(e, 'response'):  # requests error
                        e = create_api_error_from_response(e.response)
                    else:  # Network or other error
                        e = create_network_error_from_exception(e)
                
                # Record retry attempt
                retry_record = {
                    "attempt": attempt,
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                    "timestamp": attempt_time,
                    "elapsed": elapsed,
                }
                retry_history.append(retry_record)
                
                # Check if we should retry
                should_retry = self.should_retry(e, attempt)
                
                if not should_retry or attempt >= max_attempts:
                    # Create retry context for the final error
                    retry_context: RetryContext = {
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "last_exception": type(e).__name__,
                        "total_elapsed": elapsed,
                        "next_backoff": 0.0,
                        "retry_history": retry_history,
                    }
                    
                    self.logger.error(
                        f"All async retry attempts exhausted. Final attempt {attempt}/{max_attempts}, "
                        f"total elapsed: {elapsed:.2f}s"
                    )
                    
                    raise LingoDevRetryExhaustedError(
                        f"Async operation failed after {attempt} attempts over {elapsed:.2f}s",
                        retry_context,
                        e
                    )
                
                # Calculate backoff time
                backoff_time = self.calculate_backoff(attempt)
                retry_record["backoff_time"] = backoff_time
                
                self.logger.warning(
                    f"Async attempt {attempt}/{max_attempts} failed: {e}. "
                    f"Retrying in {backoff_time:.2f}s"
                )
                
                # Call retry callback if provided
                if retry_callback:
                    try:
                        await retry_callback(attempt, e, backoff_time)
                    except Exception as callback_error:
                        self.logger.warning(f"Async retry callback failed: {callback_error}")
                
                # Wait before retrying (async sleep)
                await asyncio.sleep(backoff_time)
        
        # This should never be reached due to the logic above, but just in case
        raise RuntimeError("Unexpected end of async retry loop")


# Utility functions for easy retry decoration
def with_retry(
    config: Optional[RetryConfiguration] = None,
    retry_callback: Optional[Callable[[int, Exception, float], None]] = None
) -> Callable[[F], F]:
    """
    Decorator to add retry logic to a function
    
    Args:
        config: Retry configuration
        retry_callback: Optional callback for retry events
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: F) -> F:
        retry_handler = RetryHandler(config)
        
        def wrapper(*args, **kwargs):
            return retry_handler.execute_with_retry(
                func, *args, retry_callback=retry_callback, **kwargs
            )
        
        # Preserve function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__annotations__ = getattr(func, '__annotations__', {})
        
        return wrapper  # type: ignore
    
    return decorator


def with_async_retry(
    config: Optional[RetryConfiguration] = None,
    retry_callback: Optional[Callable[[int, Exception, float], Awaitable[None]]] = None
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator to add retry logic to an async function
    
    Args:
        config: Retry configuration
        retry_callback: Optional async callback for retry events
        
    Returns:
        Decorated async function with retry logic
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        retry_handler = AsyncRetryHandler(config)
        
        async def wrapper(*args, **kwargs) -> T:
            return await retry_handler.execute_with_retry(
                func, *args, retry_callback=retry_callback, **kwargs
            )
        
        # Preserve function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__annotations__ = getattr(func, '__annotations__', {})
        
        return wrapper
    
    return decorator


# Export all retry components
__all__ = [
    "RetryHandler",
    "AsyncRetryHandler",
    "with_retry",
    "with_async_retry",
]