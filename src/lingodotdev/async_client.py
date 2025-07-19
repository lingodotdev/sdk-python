"""
Async HTTP client implementation for the Lingo.dev Python SDK

This module provides an async HTTP client using aiohttp with proper session
management, error handling, and integration with the retry system.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import aiohttp

from .models import EnhancedEngineConfig
from .retry import AsyncRetryHandler
from .exceptions import (
    LingoDevAPIError,
    LingoDevNetworkError,
    LingoDevTimeoutError,
    create_api_error_from_response,
    create_network_error_from_exception,
)

logger = logging.getLogger(__name__)


class AsyncHTTPClient:
    """
    Async HTTP client for Lingo.dev API with session management and error handling
    
    Provides async HTTP operations with proper session lifecycle management,
    comprehensive error handling, and integration with the retry system.
    """
    
    def __init__(self, config: EnhancedEngineConfig):
        """
        Initialize async HTTP client with configuration
        
        Args:
            config: Enhanced engine configuration
        """
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._closed = False
        
        # Initialize async retry handler if retry is enabled
        self.retry_handler = None
        if self.config.retry_config:
            self.retry_handler = AsyncRetryHandler(self.config.retry_config)
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def __aenter__(self) -> "AsyncHTTPClient":
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_session(self) -> None:
        """
        Ensure that an aiohttp session is available and properly configured
        """
        if self._session is None or self._session.closed:
            # Configure timeout
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            # Configure headers
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {self.config.api_key}",
                "User-Agent": "lingodotdev-python-sdk/1.0.4",
            }
            
            # Create session with configuration
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                connector=aiohttp.TCPConnector(
                    # Enable connection pooling
                    limit=100,
                    limit_per_host=30,
                    # Enable keepalive
                    keepalive_timeout=30,
                    enable_cleanup_closed=True,
                ),
                # Configure JSON serialization
                json_serialize=json.dumps,
                # Raise for HTTP error status codes
                raise_for_status=False,  # We handle this manually for better error messages
            )
            
            self._closed = False
            self.logger.debug("Async HTTP session created")
    
    async def post(
        self, 
        endpoint: str, 
        json_data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make an async POST request to the API
        
        Args:
            endpoint: API endpoint (relative to base URL)
            json_data: JSON data to send in request body
            **kwargs: Additional arguments for aiohttp request
            
        Returns:
            JSON response data
            
        Raises:
            LingoDevAPIError: For API-related errors
            LingoDevNetworkError: For network-related errors
            LingoDevTimeoutError: For timeout errors
        """
        async def _make_request() -> Dict[str, Any]:
            """Internal function to make the actual request"""
            await self._ensure_session()
            
            if self._session is None:
                raise LingoDevNetworkError(
                    "Failed to create HTTP session",
                    RuntimeError("Session is None after initialization")
                )
            
            # Construct full URL
            url = urljoin(self.config.api_url, endpoint)
            
            try:
                self.logger.debug(f"Making async POST request to {url}")
                
                async with self._session.post(url, json=json_data, **kwargs) as response:
                    # Read response text for error handling
                    response_text = await response.text()
                    
                    # Handle HTTP errors
                    if not response.ok:
                        request_details = {
                            "method": "POST",
                            "url": url,
                            "status_code": response.status,
                            "headers": dict(response.headers),
                        }
                        
                        # Create a mock response object for compatibility with existing error handling
                        mock_response = type('MockResponse', (), {
                            'status_code': response.status,
                            'text': response_text,
                            'reason': response.reason,
                            'ok': response.ok,
                            'headers': response.headers,
                        })()
                        
                        raise create_api_error_from_response(mock_response, request_details)
                    
                    # Parse JSON response
                    try:
                        json_response = await response.json()
                        self.logger.debug(f"Received successful response from {url}")
                        return json_response
                    
                    except (aiohttp.ContentTypeError, json.JSONDecodeError) as e:
                        raise LingoDevAPIError(
                            f"Invalid JSON response from API: {str(e)}",
                            response.status,
                            response_text,
                            {
                                "method": "POST",
                                "url": url,
                                "content_type": response.headers.get("Content-Type", "unknown"),
                            }
                        )
            
            except asyncio.TimeoutError as e:
                raise LingoDevTimeoutError(
                    f"Request timed out after {self.config.timeout}s",
                    self.config.timeout,
                    e,
                    {"method": "POST", "url": url}
                )
            
            except aiohttp.ClientError as e:
                # Handle various aiohttp client errors
                request_details = {"method": "POST", "url": url}
                
                if isinstance(e, aiohttp.ClientConnectionError):
                    raise LingoDevNetworkError(
                        f"Connection error: {str(e)}",
                        e,
                        request_details
                    )
                elif isinstance(e, aiohttp.ClientTimeout):
                    raise LingoDevTimeoutError(
                        f"Request timed out: {str(e)}",
                        self.config.timeout,
                        e,
                        request_details
                    )
                else:
                    raise create_network_error_from_exception(e, request_details)
            
            except Exception as e:
                # Don't wrap our own exceptions
                if isinstance(e, (LingoDevAPIError, LingoDevNetworkError, LingoDevTimeoutError)):
                    raise
                
                # Handle any other unexpected errors
                request_details = {"method": "POST", "url": url}
                raise create_network_error_from_exception(e, request_details)
        
        # Use retry handler if available, otherwise execute directly
        if self.retry_handler:
            return await self.retry_handler.execute_with_retry(_make_request)
        else:
            return await _make_request()
    
    async def close(self) -> None:
        """
        Close the HTTP session and clean up resources
        """
        if self._session and not self._session.closed:
            await self._session.close()
            self.logger.debug("Async HTTP session closed")
        
        self._closed = True
    
    @property
    def is_closed(self) -> bool:
        """
        Check if the client is closed
        
        Returns:
            True if the client is closed
        """
        return self._closed or (self._session is not None and self._session.closed)
    
    async def health_check(self) -> bool:
        """
        Perform a health check to verify the client is working
        
        Returns:
            True if the client is healthy and can make requests
        """
        if self.is_closed:
            return False
            
        try:
            await self._ensure_session()
            return not self.is_closed
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return False


# Utility function for creating async HTTP client instances
async def create_async_client(config: EnhancedEngineConfig) -> AsyncHTTPClient:
    """
    Create and initialize an async HTTP client
    
    Args:
        config: Enhanced engine configuration
        
    Returns:
        Initialized AsyncHTTPClient instance
    """
    client = AsyncHTTPClient(config)
    await client._ensure_session()
    return client


# Export the main class
__all__ = [
    "AsyncHTTPClient",
    "create_async_client",
]