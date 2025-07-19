"""
Tests for AsyncHTTPClient component

This module tests the async HTTP client functionality including session management,
error handling, retry integration, and proper resource cleanup.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

import aiohttp

from src.lingodotdev.async_client import AsyncHTTPClient, create_async_client
from src.lingodotdev.models import EnhancedEngineConfig, RetryConfiguration
from src.lingodotdev.exceptions import (
    LingoDevAPIError,
    LingoDevNetworkError,
    LingoDevTimeoutError,
)


@pytest.fixture
def basic_config():
    """Basic configuration for testing"""
    return EnhancedEngineConfig(
        api_key="test-api-key-12345",
        api_url="https://test.lingo.dev",
        timeout=10.0,
        retry_config=None  # Disable retries for basic tests
    )


@pytest.fixture
def config_with_retry():
    """Configuration with retry enabled"""
    return EnhancedEngineConfig(
        api_key="test-api-key-12345",
        api_url="https://test.lingo.dev",
        timeout=10.0,
        retry_config=RetryConfiguration(
            max_retries=2,
            backoff_factor=0.1,
            max_backoff=1.0
        )
    )


class TestAsyncHTTPClient:
    """Test cases for AsyncHTTPClient"""
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, basic_config):
        """Test client initialization with configuration"""
        client = AsyncHTTPClient(basic_config)
        
        assert client.config == basic_config
        assert client._session is None
        assert not client.is_closed
        assert client.retry_handler is None  # No retry config
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_client_with_retry_config(self, config_with_retry):
        """Test client initialization with retry configuration"""
        client = AsyncHTTPClient(config_with_retry)
        
        assert client.config == config_with_retry
        assert client.retry_handler is not None
        assert client.retry_handler.config.max_retries == 2
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_context_manager(self, basic_config):
        """Test async context manager functionality"""
        async with AsyncHTTPClient(basic_config) as client:
            assert not client.is_closed
            assert client._session is not None
            assert not client._session.closed
        
        # Client should be closed after context exit
        assert client.is_closed
    
    @pytest.mark.asyncio
    async def test_session_creation(self, basic_config):
        """Test HTTP session creation and configuration"""
        client = AsyncHTTPClient(basic_config)
        
        await client._ensure_session()
        
        assert client._session is not None
        assert not client._session.closed
        
        # Check session configuration
        assert client._session.timeout.total == basic_config.timeout
        assert "Authorization" in client._session.headers
        assert client._session.headers["Authorization"] == f"Bearer {basic_config.api_key}"
        assert client._session.headers["Content-Type"] == "application/json; charset=utf-8"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_session_reuse(self, basic_config):
        """Test that session is reused when not closed"""
        client = AsyncHTTPClient(basic_config)
        
        await client._ensure_session()
        first_session = client._session
        
        await client._ensure_session()
        second_session = client._session
        
        assert first_session is second_session
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_session_recreation_after_close(self, basic_config):
        """Test that session is recreated after being closed"""
        client = AsyncHTTPClient(basic_config)
        
        await client._ensure_session()
        first_session = client._session
        
        await client.close()
        
        await client._ensure_session()
        second_session = client._session
        
        assert first_session is not second_session
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_successful_post_request(self, basic_config):
        """Test successful POST request"""
        client = AsyncHTTPClient(basic_config)
        
        # Mock successful response
        mock_response_data = {"data": {"result": "success"}}
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Create mock response
            mock_response = AsyncMock()
            mock_response.ok = True
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_response.headers = {"Content-Type": "application/json"}
            
            # Configure mock to return our response
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Make request
            request_data = {"test": "data"}
            result = await client.post("/test", request_data)
            
            assert result == mock_response_data
            
            # Verify request was made correctly
            mock_post.assert_called_once_with(
                "https://test.lingo.dev/test",
                json=request_data
            )
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, basic_config):
        """Test API error handling for HTTP errors"""
        client = AsyncHTTPClient(basic_config)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Create mock error response
            mock_response = AsyncMock()
            mock_response.ok = False
            mock_response.status = 400
            mock_response.reason = "Bad Request"
            mock_response.text = AsyncMock(return_value='{"error": "Invalid request"}')
            mock_response.headers = {"Content-Type": "application/json"}
            
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Make request and expect error
            with pytest.raises(LingoDevAPIError) as exc_info:
                await client.post("/test", {"test": "data"})
            
            error = exc_info.value
            assert error.status_code == 400
            assert "API request failed" in str(error)
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, basic_config):
        """Test network error handling"""
        client = AsyncHTTPClient(basic_config)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Simulate connection error
            mock_post.side_effect = aiohttp.ClientConnectionError("Connection failed")
            
            with pytest.raises(LingoDevNetworkError) as exc_info:
                await client.post("/test", {"test": "data"})
            
            error = exc_info.value
            assert "Connection error" in str(error)
            assert isinstance(error.original_error, aiohttp.ClientConnectionError)
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, basic_config):
        """Test timeout error handling"""
        client = AsyncHTTPClient(basic_config)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Simulate timeout
            mock_post.side_effect = asyncio.TimeoutError("Request timed out")
            
            with pytest.raises(LingoDevTimeoutError) as exc_info:
                await client.post("/test", {"test": "data"})
            
            error = exc_info.value
            assert "timed out" in str(error)
            assert error.timeout_duration == basic_config.timeout
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_invalid_json_response(self, basic_config):
        """Test handling of invalid JSON responses"""
        client = AsyncHTTPClient(basic_config)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Create mock response with invalid JSON
            mock_response = AsyncMock()
            mock_response.ok = True
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="invalid json")
            mock_response.json = AsyncMock(side_effect=json.JSONDecodeError("Invalid JSON", "doc", 0))
            mock_response.headers = {"Content-Type": "application/json"}
            
            mock_post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(LingoDevAPIError) as exc_info:
                await client.post("/test", {"test": "data"})
            
            error = exc_info.value
            assert "Invalid JSON response" in str(error)
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_retry_integration(self, config_with_retry):
        """Test integration with retry handler"""
        client = AsyncHTTPClient(config_with_retry)
        
        call_count = 0
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count < 2:  # Fail first attempt
                    raise aiohttp.ClientConnectionError("Connection failed")
                else:  # Succeed on second attempt
                    mock_response = AsyncMock()
                    mock_response.ok = True
                    mock_response.status = 200
                    mock_response.text = AsyncMock(return_value='{"success": true}')
                    mock_response.json = AsyncMock(return_value={"success": True})
                    mock_response.headers = {"Content-Type": "application/json"}
                    
                    # Create a proper async context manager mock
                    async_context = AsyncMock()
                    async_context.__aenter__ = AsyncMock(return_value=mock_response)
                    async_context.__aexit__ = AsyncMock(return_value=None)
                    return async_context
            
            mock_post.side_effect = side_effect
            
            # Should succeed after retry
            result = await client.post("/test", {"test": "data"})
            assert result == {"success": True}
            assert call_count == 2  # First attempt failed, second succeeded
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_health_check(self, basic_config):
        """Test health check functionality"""
        client = AsyncHTTPClient(basic_config)
        
        # Should be healthy after initialization
        assert await client.health_check()
        
        # Should be unhealthy after closing
        await client.close()
        assert not await client.health_check()
    
    @pytest.mark.asyncio
    async def test_close_cleanup(self, basic_config):
        """Test proper cleanup on close"""
        client = AsyncHTTPClient(basic_config)
        
        await client._ensure_session()
        assert not client.is_closed
        assert client._session is not None
        
        await client.close()
        assert client.is_closed
        assert client._session.closed
    
    @pytest.mark.asyncio
    async def test_multiple_close_calls(self, basic_config):
        """Test that multiple close calls don't cause errors"""
        client = AsyncHTTPClient(basic_config)
        
        await client._ensure_session()
        
        # Multiple close calls should not raise errors
        await client.close()
        await client.close()
        await client.close()
        
        assert client.is_closed


class TestCreateAsyncClient:
    """Test cases for create_async_client utility function"""
    
    @pytest.mark.asyncio
    async def test_create_async_client(self, basic_config):
        """Test create_async_client utility function"""
        client = await create_async_client(basic_config)
        
        assert isinstance(client, AsyncHTTPClient)
        assert client.config == basic_config
        assert not client.is_closed
        assert client._session is not None
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_create_async_client_with_retry(self, config_with_retry):
        """Test create_async_client with retry configuration"""
        client = await create_async_client(config_with_retry)
        
        assert isinstance(client, AsyncHTTPClient)
        assert client.retry_handler is not None
        assert client.retry_handler.config.max_retries == 2
        
        await client.close()


class TestAsyncClientIntegration:
    """Integration tests for AsyncHTTPClient"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, basic_config):
        """Test handling of concurrent requests"""
        client = AsyncHTTPClient(basic_config)
        
        # Mock multiple successful responses
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.ok = True
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"result": "success"}')
            mock_response.json = AsyncMock(return_value={"result": "success"})
            mock_response.headers = {"Content-Type": "application/json"}
            
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Make concurrent requests
            tasks = [
                client.post(f"/test{i}", {"data": i})
                for i in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All requests should succeed
            assert len(results) == 5
            assert all(result == {"result": "success"} for result in results)
            
            # Should have made 5 requests
            assert mock_post.call_count == 5
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_session_persistence_across_requests(self, basic_config):
        """Test that session persists across multiple requests"""
        client = AsyncHTTPClient(basic_config)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.ok = True
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"result": "success"}')
            mock_response.json = AsyncMock(return_value={"result": "success"})
            mock_response.headers = {"Content-Type": "application/json"}
            
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Make multiple sequential requests
            await client.post("/test1", {"data": 1})
            first_session = client._session
            
            await client.post("/test2", {"data": 2})
            second_session = client._session
            
            # Session should be the same
            assert first_session is second_session
            assert mock_post.call_count == 2
        
        await client.close()


if __name__ == "__main__":
    pytest.main([__file__])