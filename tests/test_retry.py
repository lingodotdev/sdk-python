"""
Tests for the retry handler implementation
"""

import asyncio
import time
import pytest
from unittest.mock import Mock, patch, call
from typing import List

from lingodotdev.retry import (
    RetryHandler,
    AsyncRetryHandler,
    with_retry,
    with_async_retry,
)
from lingodotdev.models import RetryConfiguration
from lingodotdev.exceptions import (
    LingoDevError,
    LingoDevAPIError,
    LingoDevNetworkError,
    LingoDevRetryExhaustedError,
)


class TestRetryConfiguration:
    """Test the RetryConfiguration model"""

    def test_default_configuration(self):
        """Test default retry configuration values"""
        config = RetryConfiguration()
        
        assert config.max_retries == 3
        assert config.backoff_factor == 0.5
        assert config.retry_statuses == {429, 500, 502, 503, 504}
        assert config.max_backoff == 60.0
        assert config.jitter is True

    def test_custom_configuration(self):
        """Test custom retry configuration"""
        config = RetryConfiguration(
            max_retries=5,
            backoff_factor=1.0,
            retry_statuses={500, 502, 503},
            max_backoff=120.0,
            jitter=False
        )
        
        assert config.max_retries == 5
        assert config.backoff_factor == 1.0
        assert config.retry_statuses == {500, 502, 503}
        assert config.max_backoff == 120.0
        assert config.jitter is False


class TestRetryHandler:
    """Test the synchronous RetryHandler class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = RetryConfiguration(
            max_retries=3,
            backoff_factor=0.1,  # Small for faster tests
            max_backoff=1.0,
            jitter=False  # Disable for predictable tests
        )
        self.handler = RetryHandler(self.config)

    def test_should_retry_api_errors(self):
        """Test retry decision for API errors"""
        # Retryable API errors
        retryable_error = LingoDevAPIError("Server error", 500)
        assert self.handler.should_retry(retryable_error, 1)
        
        rate_limit_error = LingoDevAPIError("Rate limited", 429)
        assert self.handler.should_retry(rate_limit_error, 1)
        
        # Non-retryable API errors
        auth_error = LingoDevAPIError("Unauthorized", 401)
        assert not self.handler.should_retry(auth_error, 1)
        
        not_found_error = LingoDevAPIError("Not found", 404)
        assert not self.handler.should_retry(not_found_error, 1)

    def test_should_retry_network_errors(self):
        """Test retry decision for network errors"""
        network_error = LingoDevNetworkError("Connection failed", ConnectionError())
        assert self.handler.should_retry(network_error, 1)

    def test_should_retry_max_attempts(self):
        """Test that retry is disabled when max attempts reached"""
        retryable_error = LingoDevAPIError("Server error", 500)
        
        # Should retry on early attempts
        assert self.handler.should_retry(retryable_error, 1)
        assert self.handler.should_retry(retryable_error, 2)
        
        # Should not retry when max attempts reached
        assert not self.handler.should_retry(retryable_error, 3)

    def test_calculate_backoff_exponential(self):
        """Test exponential backoff calculation"""
        # Test exponential growth
        backoff1 = self.handler.calculate_backoff(1)
        backoff2 = self.handler.calculate_backoff(2)
        backoff3 = self.handler.calculate_backoff(3)
        
        assert backoff1 == 0.1  # 0.1 * (2^0) = 0.1
        assert backoff2 == 0.2  # 0.1 * (2^1) = 0.2
        assert backoff3 == 0.4  # 0.1 * (2^2) = 0.4

    def test_calculate_backoff_max_limit(self):
        """Test backoff maximum limit"""
        # Use a config with low max_backoff for testing (within valid range)
        config = RetryConfiguration(backoff_factor=2.0, max_backoff=5.0, jitter=False)
        handler = RetryHandler(config)
        
        # High attempt should be capped at max_backoff
        backoff = handler.calculate_backoff(10)
        assert backoff == 5.0

    def test_calculate_backoff_with_jitter(self):
        """Test backoff with jitter"""
        config = RetryConfiguration(backoff_factor=1.0, jitter=True)
        handler = RetryHandler(config)
        
        # With jitter, results should vary
        backoffs = [handler.calculate_backoff(1) for _ in range(10)]
        
        # All should be >= base backoff (1.0)
        assert all(b >= 1.0 for b in backoffs)
        
        # Should have some variation (not all identical)
        assert len(set(backoffs)) > 1

    def test_execute_with_retry_success_first_attempt(self):
        """Test successful execution on first attempt"""
        mock_func = Mock(return_value="success")
        
        result = self.handler.execute_with_retry(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")

    def test_execute_with_retry_success_after_retries(self):
        """Test successful execution after some retries"""
        mock_func = Mock()
        mock_func.side_effect = [
            LingoDevAPIError("Server error", 500),
            LingoDevAPIError("Server error", 500),
            "success"
        ]
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = self.handler.execute_with_retry(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 3

    def test_execute_with_retry_exhausted(self):
        """Test retry exhaustion"""
        mock_func = Mock()
        mock_func.side_effect = LingoDevAPIError("Server error", 500)
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(LingoDevRetryExhaustedError) as exc_info:
                self.handler.execute_with_retry(mock_func)
        
        error = exc_info.value
        assert error.total_attempts == 3
        assert error.retry_context["max_attempts"] == 3
        assert len(error.retry_context["retry_history"]) == 3
        assert mock_func.call_count == 3

    def test_execute_with_retry_non_retryable_error(self):
        """Test that non-retryable errors are not retried"""
        mock_func = Mock()
        mock_func.side_effect = LingoDevAPIError("Unauthorized", 401)
        
        with pytest.raises(LingoDevRetryExhaustedError) as exc_info:
            self.handler.execute_with_retry(mock_func)
        
        error = exc_info.value
        assert error.total_attempts == 1  # Only one attempt
        assert error.retry_context["attempt"] == 1  # Check context instead
        assert mock_func.call_count == 1

    def test_execute_with_retry_callback(self):
        """Test retry callback functionality"""
        mock_func = Mock()
        mock_func.side_effect = [
            LingoDevAPIError("Server error", 500),
            "success"
        ]
        
        callback_calls = []
        def retry_callback(attempt, exception, backoff_time):
            callback_calls.append((attempt, type(exception).__name__, backoff_time))
        
        with patch('time.sleep'):
            result = self.handler.execute_with_retry(mock_func, retry_callback=retry_callback)
        
        assert result == "success"
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 1  # First attempt failed
        assert callback_calls[0][1] == "LingoDevAPIError"
        assert callback_calls[0][2] == 0.1  # Expected backoff time

    def test_execute_with_retry_converts_exceptions(self):
        """Test that non-LingoDevError exceptions are converted"""
        mock_func = Mock()
        mock_func.side_effect = ConnectionError("Connection failed")
        
        with patch('time.sleep'):
            with pytest.raises(LingoDevRetryExhaustedError) as exc_info:
                self.handler.execute_with_retry(mock_func)
        
        # Should have converted ConnectionError to LingoDevNetworkError
        error = exc_info.value
        assert isinstance(error.last_error, LingoDevNetworkError)

    @patch('lingodotdev.retry.time.sleep')
    def test_execute_with_retry_timing(self, mock_sleep):
        """Test that retry timing works correctly"""
        mock_func = Mock()
        mock_func.side_effect = [
            LingoDevAPIError("Server error", 500),
            LingoDevAPIError("Server error", 500),
            "success"
        ]
        
        result = self.handler.execute_with_retry(mock_func)
        
        assert result == "success"
        # Should have slept twice (after first and second failures)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls([call(0.1), call(0.2)])


class TestAsyncRetryHandler:
    """Test the asynchronous AsyncRetryHandler class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = RetryConfiguration(
            max_retries=3,
            backoff_factor=0.1,  # Small for faster tests
            max_backoff=1.0,
            jitter=False  # Disable for predictable tests
        )
        self.handler = AsyncRetryHandler(self.config)

    def test_should_retry_same_as_sync(self):
        """Test that async retry logic matches sync logic"""
        sync_handler = RetryHandler(self.config)
        
        test_cases = [
            (LingoDevAPIError("Server error", 500), 1, True),
            (LingoDevAPIError("Unauthorized", 401), 1, False),
            (LingoDevNetworkError("Connection failed", ConnectionError()), 1, True),
            (LingoDevAPIError("Server error", 500), 3, False),  # Max attempts
        ]
        
        for exception, attempt, expected in test_cases:
            sync_result = sync_handler.should_retry(exception, attempt)
            async_result = self.handler.should_retry(exception, attempt)
            assert sync_result == async_result == expected

    def test_calculate_backoff_same_as_sync(self):
        """Test that async backoff calculation matches sync"""
        sync_handler = RetryHandler(self.config)
        
        for attempt in range(1, 6):
            sync_backoff = sync_handler.calculate_backoff(attempt)
            async_backoff = self.handler.calculate_backoff(attempt)
            assert sync_backoff == async_backoff

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_first_attempt(self):
        """Test successful async execution on first attempt"""
        async def mock_func(arg1, kwarg1=None):
            return f"success-{arg1}-{kwarg1}"
        
        result = await self.handler.execute_with_retry(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success-arg1-value1"

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_after_retries(self):
        """Test successful async execution after some retries"""
        call_count = 0
        
        async def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise LingoDevAPIError("Server error", 500)
            return "success"
        
        with patch('asyncio.sleep'):  # Mock async sleep
            result = await self.handler.execute_with_retry(mock_func)
        
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_exhausted(self):
        """Test async retry exhaustion"""
        async def mock_func():
            raise LingoDevAPIError("Server error", 500)
        
        with patch('asyncio.sleep'):  # Mock async sleep
            with pytest.raises(LingoDevRetryExhaustedError) as exc_info:
                await self.handler.execute_with_retry(mock_func)
        
        error = exc_info.value
        assert error.total_attempts == 3
        assert error.retry_context["max_attempts"] == 3
        assert len(error.retry_context["retry_history"]) == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_callback(self):
        """Test async retry callback functionality"""
        call_count = 0
        
        async def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise LingoDevAPIError("Server error", 500)
            return "success"
        
        callback_calls = []
        async def retry_callback(attempt, exception, backoff_time):
            callback_calls.append((attempt, type(exception).__name__, backoff_time))
        
        with patch('asyncio.sleep'):
            result = await self.handler.execute_with_retry(mock_func, retry_callback=retry_callback)
        
        assert result == "success"
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 1
        assert callback_calls[0][1] == "LingoDevAPIError"

    @pytest.mark.asyncio
    async def test_execute_with_retry_converts_exceptions(self):
        """Test that async non-LingoDevError exceptions are converted"""
        async def mock_func():
            raise ConnectionError("Connection failed")
        
        with patch('asyncio.sleep'):
            with pytest.raises(LingoDevRetryExhaustedError) as exc_info:
                await self.handler.execute_with_retry(mock_func)
        
        error = exc_info.value
        assert isinstance(error.last_error, LingoDevNetworkError)

    @pytest.mark.asyncio
    @patch('asyncio.sleep')
    async def test_execute_with_retry_timing(self, mock_sleep):
        """Test that async retry timing works correctly"""
        call_count = 0
        
        async def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise LingoDevAPIError("Server error", 500)
            return "success"
        
        result = await self.handler.execute_with_retry(mock_func)
        
        assert result == "success"
        # Should have slept twice (after first and second failures)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls([call(0.1), call(0.2)])


class TestRetryDecorators:
    """Test the retry decorators"""

    def test_with_retry_decorator(self):
        """Test the @with_retry decorator"""
        config = RetryConfiguration(max_retries=2, backoff_factor=0.1, jitter=False)
        
        call_count = 0
        
        @with_retry(config)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise LingoDevAPIError("Server error", 500)
            return "success"
        
        with patch('time.sleep'):
            result = test_func()
        
        assert result == "success"
        assert call_count == 2

    def test_with_retry_decorator_preserves_metadata(self):
        """Test that decorator preserves function metadata"""
        @with_retry()
        def test_func(arg1: str, arg2: int = 5) -> str:
            """Test function docstring"""
            return f"{arg1}-{arg2}"
        
        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test function docstring"
        assert hasattr(test_func, '__annotations__')

    @pytest.mark.asyncio
    async def test_with_async_retry_decorator(self):
        """Test the @with_async_retry decorator"""
        config = RetryConfiguration(max_retries=2, backoff_factor=0.1, jitter=False)
        
        call_count = 0
        
        @with_async_retry(config)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise LingoDevAPIError("Server error", 500)
            return "success"
        
        with patch('asyncio.sleep'):
            result = await test_func()
        
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_with_async_retry_decorator_preserves_metadata(self):
        """Test that async decorator preserves function metadata"""
        @with_async_retry()
        async def test_func(arg1: str, arg2: int = 5) -> str:
            """Async test function docstring"""
            return f"{arg1}-{arg2}"
        
        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Async test function docstring"
        assert hasattr(test_func, '__annotations__')


class TestRetryIntegration:
    """Integration tests for retry functionality"""

    def test_retry_with_requests_exceptions(self):
        """Test retry with actual requests exceptions"""
        try:
            import requests
        except ImportError:
            pytest.skip("requests not available")
        
        handler = RetryHandler()
        
        # Test that requests exceptions are handled
        connection_error = requests.exceptions.ConnectionError("Connection failed")
        assert handler.should_retry(connection_error, 1)
        
        timeout_error = requests.exceptions.Timeout("Request timed out")
        assert handler.should_retry(timeout_error, 1)
        
        # Test HTTP errors with different status codes
        mock_response = Mock()
        mock_response.status_code = 500
        http_error = requests.exceptions.HTTPError(response=mock_response)
        assert handler.should_retry(http_error, 1)
        
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError(response=mock_response)
        assert not handler.should_retry(http_error, 1)

    @pytest.mark.asyncio
    async def test_async_retry_with_aiohttp_exceptions(self):
        """Test async retry with aiohttp exceptions"""
        try:
            import aiohttp
        except ImportError:
            pytest.skip("aiohttp not available")
        
        handler = AsyncRetryHandler()
        
        # Test that aiohttp exceptions are handled
        connection_error = aiohttp.ClientConnectionError("Connection failed")
        assert handler.should_retry(connection_error, 1)
        
        timeout_error = aiohttp.ServerTimeoutError("Server timeout")
        assert handler.should_retry(timeout_error, 1)
        
        # Test response errors with different status codes
        response_error_500 = aiohttp.ClientResponseError(
            request_info=Mock(), history=(), status=500
        )
        assert handler.should_retry(response_error_500, 1)
        
        response_error_404 = aiohttp.ClientResponseError(
            request_info=Mock(), history=(), status=404
        )
        assert not handler.should_retry(response_error_404, 1)

    def test_retry_context_information(self):
        """Test that retry context contains comprehensive information"""
        handler = RetryHandler(RetryConfiguration(max_retries=2))
        
        def failing_func():
            raise LingoDevAPIError("Server error", 500)
        
        with patch('time.sleep'):
            with pytest.raises(LingoDevRetryExhaustedError) as exc_info:
                handler.execute_with_retry(failing_func)
        
        error = exc_info.value
        context = error.retry_context
        
        # Check context structure
        assert context["attempt"] == 2
        assert context["max_attempts"] == 2
        assert context["last_exception"] == "LingoDevAPIError"
        assert context["total_elapsed"] >= 0  # Allow zero elapsed time in tests
        assert len(context["retry_history"]) == 2
        
        # Check retry history details
        for i, record in enumerate(context["retry_history"]):
            assert record["attempt"] == i + 1
            assert record["exception_type"] == "LingoDevAPIError"
            assert "Server error" in record["exception_message"]  # Message includes suggestions
            assert "timestamp" in record
            assert "elapsed" in record
            if i < len(context["retry_history"]) - 1:  # Not the last attempt
                assert "backoff_time" in record

    def test_retry_handler_logging(self):
        """Test that retry handler logs appropriately"""
        handler = RetryHandler(RetryConfiguration(max_retries=2))
        
        def failing_func():
            raise LingoDevAPIError("Server error", 500)
        
        with patch('time.sleep'):
            with patch.object(handler.logger, 'warning') as mock_warning:
                with patch.object(handler.logger, 'error') as mock_error:
                    with pytest.raises(LingoDevRetryExhaustedError):
                        handler.execute_with_retry(failing_func)
        
        # Should log warnings for retry attempts (only 1 warning since the second attempt fails immediately)
        assert mock_warning.call_count == 1
        
        # Should log error when retries exhausted
        assert mock_error.call_count == 1

    def test_default_retry_handler(self):
        """Test retry handler with default configuration"""
        handler = RetryHandler()  # No config provided
        
        assert handler.config.max_retries == 3
        assert handler.config.backoff_factor == 0.5
        assert handler.config.jitter is True

    @pytest.mark.asyncio
    async def test_default_async_retry_handler(self):
        """Test async retry handler with default configuration"""
        handler = AsyncRetryHandler()  # No config provided
        
        assert handler.config.max_retries == 3
        assert handler.config.backoff_factor == 0.5
        assert handler.config.jitter is True


class TestRetryEdgeCases:
    """Test edge cases and error conditions"""

    def test_retry_callback_exception(self):
        """Test that callback exceptions don't break retry logic"""
        handler = RetryHandler(RetryConfiguration(max_retries=2))
        
        call_count = 0
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise LingoDevAPIError("Server error", 500)
            return "success"
        
        def failing_callback(attempt, exception, backoff_time):
            raise ValueError("Callback failed")
        
        with patch('time.sleep'):
            with patch.object(handler.logger, 'warning') as mock_warning:
                result = handler.execute_with_retry(test_func, retry_callback=failing_callback)
        
        assert result == "success"
        # Should log callback failure
        mock_warning.assert_called()

    @pytest.mark.asyncio
    async def test_async_retry_callback_exception(self):
        """Test that async callback exceptions don't break retry logic"""
        handler = AsyncRetryHandler(RetryConfiguration(max_retries=2))
        
        call_count = 0
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise LingoDevAPIError("Server error", 500)
            return "success"
        
        async def failing_callback(attempt, exception, backoff_time):
            raise ValueError("Async callback failed")
        
        with patch('asyncio.sleep'):
            with patch.object(handler.logger, 'warning') as mock_warning:
                result = await handler.execute_with_retry(test_func, retry_callback=failing_callback)
        
        assert result == "success"
        # Should log callback failure
        mock_warning.assert_called()

    def test_zero_max_retries(self):
        """Test behavior with zero max retries"""
        config = RetryConfiguration(max_retries=0)
        handler = RetryHandler(config)
        
        def failing_func():
            raise LingoDevAPIError("Server error", 500)
        
        with pytest.raises(LingoDevRetryExhaustedError) as exc_info:
            handler.execute_with_retry(failing_func)
        
        error = exc_info.value
        assert error.total_attempts == 1  # Should still try once
        assert error.retry_context["max_attempts"] == 1  # max(1, 0) = 1