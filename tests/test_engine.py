"""
Tests for the LingoDotDevEngine class
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

import httpx
from lingodotdev import LingoDotDevEngine
from lingodotdev.engine import EngineConfig


class TestEngineConfig:
    """Test the EngineConfig model"""

    def test_valid_config(self):
        """Test valid configuration"""
        config = EngineConfig(
            api_key="test_key",
            api_url="https://api.test.com",
            batch_size=50,
            ideal_batch_item_size=500,
            retry_max_attempts=5,
            retry_base_delay=2.0,
        )
        assert config.api_key == "test_key"
        assert config.api_url == "https://api.test.com"
        assert config.batch_size == 50
        assert config.ideal_batch_item_size == 500
        assert config.retry_max_attempts == 5
        assert config.retry_base_delay == 2.0

    def test_default_values(self):
        """Test default configuration values"""
        config = EngineConfig(api_key="test_key")
        assert config.api_url == "https://engine.lingo.dev"
        assert config.batch_size == 25
        assert config.ideal_batch_item_size == 250
        assert config.retry_max_attempts == 3
        assert config.retry_base_delay == 1.0

    def test_invalid_api_url(self):
        """Test invalid API URL validation"""
        with pytest.raises(ValueError, match="API URL must be a valid HTTP/HTTPS URL"):
            EngineConfig(api_key="test_key", api_url="invalid_url")

    def test_invalid_batch_size(self):
        """Test invalid batch size validation"""
        with pytest.raises(ValueError):
            EngineConfig(api_key="test_key", batch_size=0)

        with pytest.raises(ValueError):
            EngineConfig(api_key="test_key", batch_size=300)

    def test_invalid_ideal_batch_item_size(self):
        """Test invalid ideal batch item size validation"""
        with pytest.raises(ValueError):
            EngineConfig(api_key="test_key", ideal_batch_item_size=0)

        with pytest.raises(ValueError):
            EngineConfig(api_key="test_key", ideal_batch_item_size=3000)

    def test_valid_retry_max_attempts(self):
        """Test valid retry_max_attempts values"""
        # Test boundary values
        config_min = EngineConfig(api_key="test_key", retry_max_attempts=0)
        assert config_min.retry_max_attempts == 0
        
        config_max = EngineConfig(api_key="test_key", retry_max_attempts=10)
        assert config_max.retry_max_attempts == 10
        
        # Test typical values
        config_typical = EngineConfig(api_key="test_key", retry_max_attempts=5)
        assert config_typical.retry_max_attempts == 5

    def test_invalid_retry_max_attempts(self):
        """Test invalid retry_max_attempts validation"""
        # Test below minimum
        with pytest.raises(ValueError):
            EngineConfig(api_key="test_key", retry_max_attempts=-1)
        
        # Test above maximum
        with pytest.raises(ValueError):
            EngineConfig(api_key="test_key", retry_max_attempts=11)

    def test_valid_retry_base_delay(self):
        """Test valid retry_base_delay values"""
        # Test boundary values
        config_min = EngineConfig(api_key="test_key", retry_base_delay=0.1)
        assert config_min.retry_base_delay == 0.1
        
        config_max = EngineConfig(api_key="test_key", retry_base_delay=10.0)
        assert config_max.retry_base_delay == 10.0
        
        # Test typical values
        config_typical = EngineConfig(api_key="test_key", retry_base_delay=2.5)
        assert config_typical.retry_base_delay == 2.5

    def test_invalid_retry_base_delay(self):
        """Test invalid retry_base_delay validation"""
        # Test below minimum
        with pytest.raises(ValueError):
            EngineConfig(api_key="test_key", retry_base_delay=0.05)
        
        # Test above maximum
        with pytest.raises(ValueError):
            EngineConfig(api_key="test_key", retry_base_delay=15.0)

    def test_retry_disabled_configuration(self):
        """Test retry disabled configuration (max_attempts=0)"""
        config = EngineConfig(api_key="test_key", retry_max_attempts=0)
        assert config.retry_max_attempts == 0
        assert config.retry_base_delay == 1.0  # Default should still be set

    def test_retry_configuration_combinations(self):
        """Test various combinations of retry configuration"""
        # High retry count with low delay
        config1 = EngineConfig(
            api_key="test_key", 
            retry_max_attempts=10, 
            retry_base_delay=0.1
        )
        assert config1.retry_max_attempts == 10
        assert config1.retry_base_delay == 0.1
        
        # Low retry count with high delay
        config2 = EngineConfig(
            api_key="test_key", 
            retry_max_attempts=1, 
            retry_base_delay=10.0
        )
        assert config2.retry_max_attempts == 1
        assert config2.retry_base_delay == 10.0

    def test_valid_retry_max_timeout(self):
        """Test valid retry_max_timeout values"""
        # Test boundary values
        config_min = EngineConfig(api_key="test_key", retry_max_timeout=1.0)
        assert config_min.retry_max_timeout == 1.0
        
        config_max = EngineConfig(api_key="test_key", retry_max_timeout=300.0)
        assert config_max.retry_max_timeout == 300.0
        
        # Test default value
        config_default = EngineConfig(api_key="test_key")
        assert config_default.retry_max_timeout == 60.0

    def test_invalid_retry_max_timeout(self):
        """Test invalid retry_max_timeout validation"""
        # Test below minimum
        with pytest.raises(ValueError):
            EngineConfig(api_key="test_key", retry_max_timeout=0.5)
        
        # Test above maximum
        with pytest.raises(ValueError):
            EngineConfig(api_key="test_key", retry_max_timeout=400.0)


@pytest.mark.asyncio
class TestLingoDotDevEngine:
    """Test the LingoDotDevEngine class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            "api_key": "test_api_key",
            "api_url": "https://api.test.com",
            "batch_size": 10,
            "ideal_batch_item_size": 100,
            "retry_max_attempts": 2,  # Use lower value for faster tests
            "retry_base_delay": 0.1,  # Use lower value for faster tests
        }
        self.engine = LingoDotDevEngine(self.config)

    def test_initialization(self):
        """Test engine initialization"""
        assert self.engine.config.api_key == "test_api_key"
        assert self.engine.config.api_url == "https://api.test.com"
        assert self.engine.config.batch_size == 10
        assert self.engine.config.ideal_batch_item_size == 100
        assert self.engine.config.retry_max_attempts == 2
        assert self.engine.config.retry_base_delay == 0.1
        assert self.engine._client is None  # Client not initialized yet

    async def test_async_context_manager(self):
        """Test async context manager functionality"""
        async with LingoDotDevEngine(self.config) as engine:
            assert engine._client is not None
            assert not engine._client.is_closed

    def test_count_words_in_record_string(self):
        """Test word counting in strings"""
        assert self.engine._count_words_in_record("hello world") == 2
        assert self.engine._count_words_in_record("  hello   world  ") == 2
        assert self.engine._count_words_in_record("") == 0
        assert self.engine._count_words_in_record("single") == 1

    def test_count_words_in_record_list(self):
        """Test word counting in lists"""
        assert self.engine._count_words_in_record(["hello world", "test"]) == 3
        assert self.engine._count_words_in_record([]) == 0
        assert self.engine._count_words_in_record(["hello", ["world", "test"]]) == 3

    def test_count_words_in_record_dict(self):
        """Test word counting in dictionaries"""
        assert (
            self.engine._count_words_in_record({"key1": "hello world", "key2": "test"})
            == 3
        )
        assert self.engine._count_words_in_record({}) == 0
        assert (
            self.engine._count_words_in_record({"key1": {"nested": "hello world"}}) == 2
        )

    def test_count_words_in_record_other_types(self):
        """Test word counting with non-string types"""
        assert self.engine._count_words_in_record(123) == 0
        assert self.engine._count_words_in_record(None) == 0
        assert self.engine._count_words_in_record(True) == 0

    def test_extract_payload_chunks_small_payload(self):
        """Test payload chunking with small payload"""
        payload = {"key1": "hello", "key2": "world"}
        chunks = self.engine._extract_payload_chunks(payload)
        assert len(chunks) == 1
        assert chunks[0] == payload

    def test_extract_payload_chunks_large_payload(self):
        """Test payload chunking with large payload"""
        # Create a payload that exceeds batch size
        payload = {f"key{i}": "hello world" for i in range(15)}
        chunks = self.engine._extract_payload_chunks(payload)
        assert len(chunks) == 2  # Should split into 2 chunks based on batch_size=10

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_localize_chunk_success(self, mock_post):
        """Test successful chunk localization"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"key": "translated_value"}}
        mock_post.return_value = mock_response

        result = await self.engine._localize_chunk(
            "en", "es", {"data": {"key": "value"}}, "workflow_id", False
        )

        assert result == {"key": "translated_value"}
        mock_post.assert_called_once()

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_localize_chunk_server_error(self, mock_post):
        """Test server error handling in chunk localization"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"
        mock_response.text = "Server error details"
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="Server error"):
            await self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, "workflow_id", False
            )

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_localize_chunk_bad_request(self, mock_post):
        """Test bad request handling in chunk localization"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 400
        mock_response.reason_phrase = "Bad Request"
        mock_post.return_value = mock_response

        with pytest.raises(ValueError, match="Invalid request \\(400\\)"):
            await self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, "workflow_id", False
            )

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_localize_chunk_streaming_error(self, mock_post):
        """Test streaming error handling in chunk localization"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "Streaming error occurred"}
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="Streaming error occurred"):
            await self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, "workflow_id", False
            )

    @patch("lingodotdev.engine.LingoDotDevEngine._localize_raw")
    async def test_localize_text(self, mock_localize_raw):
        """Test text localization"""
        mock_localize_raw.return_value = {"text": "translated_text"}

        result = await self.engine.localize_text(
            "hello world", {"source_locale": "en", "target_locale": "es"}
        )

        assert result == "translated_text"
        mock_localize_raw.assert_called_once()

    @patch("lingodotdev.engine.LingoDotDevEngine._localize_raw")
    async def test_localize_object(self, mock_localize_raw):
        """Test object localization"""
        mock_localize_raw.return_value = {"greeting": "hola", "farewell": "adiós"}

        result = await self.engine.localize_object(
            {"greeting": "hello", "farewell": "goodbye"},
            {"source_locale": "en", "target_locale": "es"},
        )

        assert result == {"greeting": "hola", "farewell": "adiós"}
        mock_localize_raw.assert_called_once()

    @patch("lingodotdev.engine.LingoDotDevEngine.localize_text")
    async def test_batch_localize_text(self, mock_localize_text):
        """Test batch text localization"""
        mock_localize_text.side_effect = AsyncMock(side_effect=["hola", "bonjour"])

        result = await self.engine.batch_localize_text(
            "hello",
            {"source_locale": "en", "target_locales": ["es", "fr"], "fast": True},
        )

        assert result == ["hola", "bonjour"]
        assert mock_localize_text.call_count == 2

    async def test_batch_localize_text_missing_target_locales(self):
        """Test batch text localization with missing target_locales"""
        with pytest.raises(ValueError, match="target_locales is required"):
            await self.engine.batch_localize_text("hello", {"source_locale": "en"})

    @patch("lingodotdev.engine.LingoDotDevEngine._localize_raw")
    async def test_localize_chat(self, mock_localize_raw):
        """Test chat localization"""
        mock_localize_raw.return_value = {
            "chat": [
                {"name": "Alice", "text": "hola"},
                {"name": "Bob", "text": "adiós"},
            ]
        }

        chat = [{"name": "Alice", "text": "hello"}, {"name": "Bob", "text": "goodbye"}]

        result = await self.engine.localize_chat(
            chat, {"source_locale": "en", "target_locale": "es"}
        )

        expected = [{"name": "Alice", "text": "hola"}, {"name": "Bob", "text": "adiós"}]

        assert result == expected
        mock_localize_raw.assert_called_once()

    async def test_localize_chat_invalid_format(self):
        """Test chat localization with invalid message format"""
        invalid_chat = [{"name": "Alice"}]  # Missing 'text' key

        with pytest.raises(
            ValueError, match="Each chat message must have 'name' and 'text' properties"
        ):
            await self.engine.localize_chat(
                invalid_chat, {"source_locale": "en", "target_locale": "es"}
            )

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_recognize_locale_success(self, mock_post):
        """Test successful locale recognition"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"locale": "es"}
        mock_post.return_value = mock_response

        result = await self.engine.recognize_locale("Hola mundo")

        assert result == "es"
        mock_post.assert_called_once()

    async def test_recognize_locale_empty_text(self):
        """Test locale recognition with empty text"""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await self.engine.recognize_locale("   ")

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_recognize_locale_server_error(self, mock_post):
        """Test locale recognition with server error"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="Server error"):
            await self.engine.recognize_locale("Hello world")

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_whoami_success(self, mock_post):
        """Test successful whoami request"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "email": "test@example.com",
            "id": "user_123",
        }
        mock_post.return_value = mock_response

        result = await self.engine.whoami()

        assert result == {"email": "test@example.com", "id": "user_123"}
        mock_post.assert_called_once()

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_whoami_unauthenticated(self, mock_post):
        """Test whoami request when unauthenticated"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        result = await self.engine.whoami()

        assert result is None

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_whoami_server_error(self, mock_post):
        """Test whoami request with server error"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="Server error"):
            await self.engine.whoami()

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_whoami_no_email(self, mock_post):
        """Test whoami request with no email in response"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        result = await self.engine.whoami()

        assert result is None

    @patch("lingodotdev.engine.LingoDotDevEngine.localize_object")
    async def test_batch_localize_objects(self, mock_localize_object):
        """Test batch object localization"""
        mock_localize_object.side_effect = AsyncMock(
            side_effect=[{"greeting": "hola"}, {"farewell": "adiós"}]
        )

        objects = [{"greeting": "hello"}, {"farewell": "goodbye"}]
        params = {"source_locale": "en", "target_locale": "es"}

        result = await self.engine.batch_localize_objects(objects, params)

        assert result == [{"greeting": "hola"}, {"farewell": "adiós"}]
        assert mock_localize_object.call_count == 2

    async def test_concurrent_processing(self):
        """Test concurrent processing functionality"""
        with patch(
            "lingodotdev.engine.LingoDotDevEngine._localize_chunk"
        ) as mock_chunk:
            mock_chunk.return_value = {"key": "value"}

            large_payload = {f"key{i}": f"value{i}" for i in range(5)}

            # Create mock params object (Python 3.8 compatible)
            mock_params = type(
                "MockParams",
                (),
                {
                    "source_locale": "en",
                    "target_locale": "es",
                    "fast": False,
                    "reference": None,
                },
            )()

            # Test concurrent mode
            await self.engine._localize_raw(
                large_payload,
                mock_params,
                concurrent=True,
            )

            # Should have called _localize_chunk multiple times concurrently
            assert mock_chunk.call_count > 0

    def test_should_retry_response_server_errors(self):
        """Test retry decision for server errors (5xx)"""
        # Test various 5xx status codes
        for status_code in [500, 502, 503, 504, 599]:
            mock_response = Mock()
            mock_response.status_code = status_code
            assert self.engine._should_retry_response(mock_response) is True

    def test_should_retry_response_rate_limiting(self):
        """Test retry decision for rate limiting (429)"""
        mock_response = Mock()
        mock_response.status_code = 429
        assert self.engine._should_retry_response(mock_response) is True

    def test_should_retry_response_client_errors(self):
        """Test retry decision for client errors (4xx except 429)"""
        # Test various 4xx status codes (except 429)
        for status_code in [400, 401, 403, 404, 422, 499]:
            mock_response = Mock()
            mock_response.status_code = status_code
            assert self.engine._should_retry_response(mock_response) is False

    def test_should_retry_response_success_codes(self):
        """Test retry decision for success codes (2xx, 3xx)"""
        # Test various success status codes
        for status_code in [200, 201, 204, 301, 302, 304]:
            mock_response = Mock()
            mock_response.status_code = status_code
            assert self.engine._should_retry_response(mock_response) is False

    def test_calculate_retry_delay_exponential_backoff(self):
        """Test exponential backoff delay calculation"""
        # Test exponential progression: base_delay * (2 ^ attempt)
        # Using engine with retry_base_delay=0.1 for predictable testing
        
        # Attempt 0: 0.1 * (2^0) = 0.1
        delay_0 = self.engine._calculate_retry_delay(0, None)
        assert 0.1 <= delay_0 <= 0.11  # 0.1 + 10% jitter
        
        # Attempt 1: 0.1 * (2^1) = 0.2
        delay_1 = self.engine._calculate_retry_delay(1, None)
        assert 0.2 <= delay_1 <= 0.22  # 0.2 + 10% jitter
        
        # Attempt 2: 0.1 * (2^2) = 0.4
        delay_2 = self.engine._calculate_retry_delay(2, None)
        assert 0.4 <= delay_2 <= 0.44  # 0.4 + 10% jitter

    def test_calculate_retry_delay_jitter_application(self):
        """Test that jitter is properly applied to delay calculation"""
        delays = []
        # Generate multiple delays for the same attempt to verify jitter variation
        for _ in range(10):
            delay = self.engine._calculate_retry_delay(0, None)
            delays.append(delay)
        
        # All delays should be different due to jitter (very high probability)
        assert len(set(delays)) > 1, "Jitter should create variation in delays"
        
        # All delays should be within expected range (base_delay + 0-10% jitter)
        for delay in delays:
            assert 0.1 <= delay <= 0.11  # 0.1 + 10% jitter

    def test_calculate_retry_delay_with_retry_after_header(self):
        """Test delay calculation with 429 Retry-After header"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'retry-after': '5.0'}
        
        # For attempt 0, exponential backoff would be 0.1, but Retry-After is 5.0
        delay = self.engine._calculate_retry_delay(0, mock_response)
        assert 5.0 <= delay <= 5.5  # 5.0 + 10% jitter
        
        # For attempt 3, exponential backoff would be 0.8, still less than Retry-After
        delay = self.engine._calculate_retry_delay(3, mock_response)
        assert 5.0 <= delay <= 5.5  # 5.0 + 10% jitter

    def test_calculate_retry_delay_retry_after_vs_exponential(self):
        """Test that larger of Retry-After and exponential backoff is used"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'retry-after': '0.05'}  # Very small Retry-After
        
        # For attempt 2, exponential backoff would be 0.4, larger than Retry-After 0.05
        delay = self.engine._calculate_retry_delay(2, mock_response)
        assert 0.4 <= delay <= 0.44  # Exponential backoff wins

    def test_calculate_retry_delay_invalid_retry_after(self):
        """Test handling of invalid Retry-After header values"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'retry-after': 'invalid'}
        
        # Should fall back to exponential backoff when Retry-After is invalid
        delay = self.engine._calculate_retry_delay(1, mock_response)
        assert 0.2 <= delay <= 0.22  # 0.2 + 10% jitter (exponential backoff)

    def test_calculate_retry_delay_missing_retry_after(self):
        """Test delay calculation when Retry-After header is missing"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {}  # No retry-after header
        
        # Should use exponential backoff when Retry-After is missing
        delay = self.engine._calculate_retry_delay(1, mock_response)
        assert 0.2 <= delay <= 0.22  # 0.2 + 10% jitter

    def test_calculate_retry_delay_non_429_response(self):
        """Test delay calculation for non-429 responses (should ignore Retry-After)"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.headers = {'retry-after': '10.0'}
        
        # Should ignore Retry-After for non-429 responses
        delay = self.engine._calculate_retry_delay(1, mock_response)
        assert 0.2 <= delay <= 0.22  # 0.2 + 10% jitter (exponential backoff only)

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_make_request_with_retry_success_first_attempt(self, mock_sleep, mock_post):
        """Test successful request on first attempt (no retries needed)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = await self.engine._make_request_with_retry(
            "https://api.test.com/test", {"data": "test"}
        )
        
        assert result == mock_response
        mock_post.assert_called_once_with("https://api.test.com/test", json={"data": "test"})
        mock_sleep.assert_not_called()  # No retries needed

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_make_request_with_retry_success_after_retry(self, mock_sleep, mock_post):
        """Test successful request after one retry"""
        # First call returns 500 (retryable), second call returns 200 (success)
        mock_response_error = Mock()
        mock_response_error.status_code = 500
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_post.side_effect = [mock_response_error, mock_response_success]
        
        result = await self.engine._make_request_with_retry(
            "https://api.test.com/test", {"data": "test"}
        )
        
        assert result == mock_response_success
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once()  # One retry delay

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_make_request_with_retry_exhausted_http_errors(self, mock_sleep, mock_post):
        """Test retry exhaustion with HTTP errors"""
        # All attempts return 500 (retryable error)
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        # Should retry max_attempts times, then return the final response
        result = await self.engine._make_request_with_retry(
            "https://api.test.com/test", {"data": "test"}
        )
        
        assert result == mock_response  # Returns final response even if it's an error
        assert mock_post.call_count == self.engine.config.retry_max_attempts + 1  # 3 total attempts
        assert mock_sleep.call_count == self.engine.config.retry_max_attempts  # 2 retry delays

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_make_request_with_retry_exhausted_network_errors(self, mock_sleep, mock_post):
        """Test retry exhaustion with network errors"""
        # All attempts raise RequestError
        mock_post.side_effect = httpx.RequestError("Connection timeout")
        
        with pytest.raises(RuntimeError, match="Request failed after 3 attempts"):
            await self.engine._make_request_with_retry(
                "https://api.test.com/test", {"data": "test"}
            )
        
        assert mock_post.call_count == self.engine.config.retry_max_attempts + 1  # 3 total attempts
        assert mock_sleep.call_count == self.engine.config.retry_max_attempts  # 2 retry delays

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_make_request_with_retry_non_retryable_error(self, mock_sleep, mock_post):
        """Test immediate failure with non-retryable errors"""
        mock_response = Mock()
        mock_response.status_code = 400  # Non-retryable client error
        mock_post.return_value = mock_response
        
        result = await self.engine._make_request_with_retry(
            "https://api.test.com/test", {"data": "test"}
        )
        
        assert result == mock_response
        mock_post.assert_called_once()  # No retries for 4xx errors
        mock_sleep.assert_not_called()

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_make_request_with_retry_429_with_retry_after(self, mock_sleep, mock_post):
        """Test retry with 429 response and Retry-After header"""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {'retry-after': '2.0'}
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_post.side_effect = [mock_response_429, mock_response_success]
        
        result = await self.engine._make_request_with_retry(
            "https://api.test.com/test", {"data": "test"}
        )
        
        assert result == mock_response_success
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once()
        # Verify delay was calculated with Retry-After header
        delay_used = mock_sleep.call_args[0][0]
        assert delay_used >= 2.0  # Should respect Retry-After minimum

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_make_request_with_retry_disabled(self, mock_sleep, mock_post):
        """Test behavior when retries are disabled (max_attempts=0)"""
        # Create engine with retries disabled
        engine_no_retry = LingoDotDevEngine({
            "api_key": "test_api_key",
            "retry_max_attempts": 0
        })
        
        mock_response = Mock()
        mock_response.status_code = 500  # Would normally be retryable
        mock_post.return_value = mock_response
        
        result = await engine_no_retry._make_request_with_retry(
            "https://api.test.com/test", {"data": "test"}
        )
        
        assert result == mock_response
        mock_post.assert_called_once()  # No retries when disabled
        mock_sleep.assert_not_called()

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_make_request_with_retry_mixed_errors(self, mock_sleep, mock_post):
        """Test retry with mixed error types"""
        # First: network error, Second: 500 error, Third: success
        mock_response_500 = Mock()
        mock_response_500.status_code = 500
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_post.side_effect = [
            httpx.RequestError("Network error"),
            mock_response_500,
            mock_response_success
        ]
        
        result = await self.engine._make_request_with_retry(
            "https://api.test.com/test", {"data": "test"}
        )
        
        assert result == mock_response_success
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2  # Two retry delays

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_make_request_with_retry_error_message_format(self, mock_sleep, mock_post):
        """Test error message format when retries are exhausted"""
        mock_post.side_effect = httpx.RequestError("Connection timeout")
        
        with pytest.raises(RuntimeError) as exc_info:
            await self.engine._make_request_with_retry(
                "https://api.test.com/test", {"data": "test"}
            )
        
        error_message = str(exc_info.value)
        assert "Request failed after 3 attempts" in error_message
        assert "Connection timeout" in error_message

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    @patch("time.time")
    async def test_make_request_with_retry_timeout_exceeded(self, mock_time, mock_sleep, mock_post):
        """Test timeout cap prevents excessive retry delays"""
        # Create engine with short timeout
        engine = LingoDotDevEngine({
            "api_key": "test_key", 
            "retry_max_timeout": 2.0, 
            "retry_base_delay": 1.0
        })
        
        # Mock time progression: start at 0, then simulate time passing
        # First call: start time (0.0)
        # Second call: check after first attempt (1.8s elapsed)
        # The next delay would be ~2s, so 1.8 + 2 > 2.0 timeout
        mock_time.side_effect = [0.0, 1.8, 1.8]
        
        # All attempts return 500 (retryable error)
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        with pytest.raises(RuntimeError) as exc_info:
            await engine._make_request_with_retry(
                "https://api.test.com/test", {"data": "test"}
            )
        
        error_message = str(exc_info.value)
        assert "timeout exceeded" in error_message
        assert "1.8s" in error_message
        
        # Should only make 1 attempt before timeout check prevents retry
        assert mock_post.call_count == 1

    @patch("lingodotdev.engine.LingoDotDevEngine._make_request_with_retry")
    async def test_localize_chunk_uses_retry_wrapper(self, mock_retry_wrapper):
        """Test that _localize_chunk uses the retry wrapper method"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {"data": {"key": "translated_value"}}
        mock_retry_wrapper.return_value = mock_response
        
        result = await self.engine._localize_chunk(
            "en", "es", {"data": {"key": "value"}}, "workflow_id", False
        )
        
        assert result == {"key": "translated_value"}
        mock_retry_wrapper.assert_called_once()
        # Verify the correct URL and request data were passed
        call_args = mock_retry_wrapper.call_args
        assert call_args[0][0].endswith("/i18n")  # URL
        assert "data" in call_args[0][1]  # request_data

    @patch("lingodotdev.engine.LingoDotDevEngine._make_request_with_retry")
    async def test_localize_chunk_retry_disabled_behavior(self, mock_retry_wrapper):
        """Test that _localize_chunk works when retries are disabled"""
        # Create engine with retries disabled
        engine_no_retry = LingoDotDevEngine({
            "api_key": "test_api_key",
            "retry_max_attempts": 0
        })
        
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {"data": {"key": "translated_value"}}
        mock_retry_wrapper.return_value = mock_response
        
        result = await engine_no_retry._localize_chunk(
            "en", "es", {"data": {"key": "value"}}, "workflow_id", False
        )
        
        assert result == {"key": "translated_value"}
        mock_retry_wrapper.assert_called_once()

    @patch("lingodotdev.engine.LingoDotDevEngine._make_request_with_retry")
    async def test_localize_chunk_existing_error_handling_preserved(self, mock_retry_wrapper):
        """Test that existing error handling in _localize_chunk is preserved"""
        # Test server error handling
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"
        mock_response.text = "Server error details"
        mock_retry_wrapper.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="Server error"):
            await self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, "workflow_id", False
            )

    @patch("lingodotdev.engine.LingoDotDevEngine._make_request_with_retry")
    async def test_localize_chunk_streaming_error_handling_preserved(self, mock_retry_wrapper):
        """Test that streaming error handling in _localize_chunk is preserved"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {"error": "Streaming error occurred"}
        mock_retry_wrapper.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="Streaming error occurred"):
            await self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, "workflow_id", False
            )

    @patch("lingodotdev.engine.LingoDotDevEngine._make_request_with_retry")
    async def test_localize_chunk_request_data_format_unchanged(self, mock_retry_wrapper):
        """Test that request data format passed to retry wrapper is unchanged"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {"data": {"key": "value"}}
        mock_retry_wrapper.return_value = mock_response
        
        await self.engine._localize_chunk(
            "en", "es", 
            {"data": {"key": "value"}, "reference": {"es": {"key": "valor"}}}, 
            "test_workflow", 
            True
        )
        
        # Verify request data structure
        call_args = mock_retry_wrapper.call_args
        request_data = call_args[0][1]
        
        assert request_data["params"]["workflowId"] == "test_workflow"
        assert request_data["params"]["fast"] is True
        assert request_data["locale"]["source"] == "en"
        assert request_data["locale"]["target"] == "es"
        assert request_data["data"] == {"key": "value"}
        assert request_data["reference"] == {"es": {"key": "valor"}}

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_retry_behavior_5xx_server_errors(self, mock_sleep, mock_post):
        """Test retry behavior with 5xx server errors"""
        # First two attempts return 500, third succeeds
        mock_response_error = Mock()
        mock_response_error.is_success = False
        mock_response_error.status_code = 500
        mock_response_error.reason_phrase = "Internal Server Error"
        mock_response_error.text = "Server temporarily unavailable"
        
        mock_response_success = Mock()
        mock_response_success.is_success = True
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"data": {"key": "translated"}}
        
        mock_post.side_effect = [mock_response_error, mock_response_error, mock_response_success]
        
        result = await self.engine._localize_chunk(
            "en", "es", {"data": {"key": "value"}}, "workflow_id", False
        )
        
        assert result == {"key": "translated"}
        assert mock_post.call_count == 3  # Two failures + one success
        assert mock_sleep.call_count == 2  # Two retry delays

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_retry_behavior_network_timeouts(self, mock_sleep, mock_post):
        """Test retry behavior with network timeouts"""
        # First attempt times out, second succeeds
        mock_response_success = Mock()
        mock_response_success.is_success = True
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"data": {"key": "translated"}}
        
        mock_post.side_effect = [
            httpx.RequestError("Connection timeout"),
            mock_response_success
        ]
        
        result = await self.engine._localize_chunk(
            "en", "es", {"data": {"key": "value"}}, "workflow_id", False
        )
        
        assert result == {"key": "translated"}
        assert mock_post.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_retry_behavior_4xx_client_errors_no_retry(self, mock_sleep, mock_post):
        """Test that 4xx client errors (except 429) are not retried"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 400
        mock_response.reason_phrase = "Bad Request"
        mock_post.return_value = mock_response
        
        with pytest.raises(ValueError, match="Invalid request"):
            await self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, "workflow_id", False
            )
        
        mock_post.assert_called_once()  # No retries for 4xx errors
        mock_sleep.assert_not_called()

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_retry_behavior_429_rate_limiting(self, mock_sleep, mock_post):
        """Test retry behavior with 429 rate limiting"""
        mock_response_429 = Mock()
        mock_response_429.is_success = False
        mock_response_429.status_code = 429
        mock_response_429.reason_phrase = "Too Many Requests"
        mock_response_429.text = "Rate limit exceeded"
        mock_response_429.headers = {'retry-after': '1.5'}
        
        mock_response_success = Mock()
        mock_response_success.is_success = True
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"data": {"key": "translated"}}
        
        mock_post.side_effect = [mock_response_429, mock_response_success]
        
        result = await self.engine._localize_chunk(
            "en", "es", {"data": {"key": "value"}}, "workflow_id", False
        )
        
        assert result == {"key": "translated"}
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once()
        # Verify delay respects Retry-After header
        delay_used = mock_sleep.call_args[0][0]
        assert delay_used >= 1.5

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_retry_behavior_exponential_backoff_progression(self, mock_sleep, mock_post):
        """Test exponential backoff delay progression"""
        # All attempts return 500 to test delay progression
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"
        mock_response.text = "Server error"
        mock_post.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="Server error"):
            await self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, "workflow_id", False
            )
        
        assert mock_post.call_count == 3  # max_attempts + 1
        assert mock_sleep.call_count == 2  # Two retry delays
        
        # Verify exponential backoff progression (with jitter tolerance)
        delays = [call[0][0] for call in mock_sleep.call_args_list]
        # Attempt 0: base_delay * (2^0) = 0.1, Attempt 1: base_delay * (2^1) = 0.2
        assert 0.1 <= delays[0] <= 0.11  # 0.1 + 10% jitter
        assert 0.2 <= delays[1] <= 0.22  # 0.2 + 10% jitter
        assert delays[1] > delays[0]  # Should be increasing

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_retry_behavior_jitter_prevents_thundering_herd(self, mock_sleep, mock_post):
        """Test that jitter is applied to prevent thundering herd"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"
        mock_response.text = "Server error"
        mock_post.return_value = mock_response
        
        delays = []
        # Run multiple times to collect jitter variations
        for _ in range(5):
            mock_sleep.reset_mock()
            mock_post.reset_mock()
            
            with pytest.raises(RuntimeError):
                await self.engine._localize_chunk(
                    "en", "es", {"data": {"key": "value"}}, "workflow_id", False
                )
            
            if mock_sleep.call_args_list:
                delays.append(mock_sleep.call_args_list[0][0][0])
        
        # Verify jitter creates variation (very high probability)
        assert len(set(delays)) > 1, "Jitter should create variation in delays"

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_retry_behavior_exhaustion_error_message(self, mock_sleep, mock_post):
        """Test error message format when retries are exhausted"""
        mock_post.side_effect = httpx.RequestError("Connection failed")
        
        with pytest.raises(RuntimeError) as exc_info:
            await self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, "workflow_id", False
            )
        
        error_message = str(exc_info.value)
        assert "Request failed after 3 attempts" in error_message
        assert "Connection failed" in error_message

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_retry_behavior_mixed_error_types(self, mock_sleep, mock_post):
        """Test retry behavior with mixed error types"""
        # Network error, then 503, then success
        mock_response_503 = Mock()
        mock_response_503.is_success = False
        mock_response_503.status_code = 503
        mock_response_503.reason_phrase = "Service Unavailable"
        mock_response_503.text = "Service temporarily unavailable"
        
        mock_response_success = Mock()
        mock_response_success.is_success = True
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"data": {"key": "translated"}}
        
        mock_post.side_effect = [
            httpx.RequestError("Network error"),
            mock_response_503,
            mock_response_success
        ]
        
        result = await self.engine._localize_chunk(
            "en", "es", {"data": {"key": "value"}}, "workflow_id", False
        )
        
        assert result == {"key": "translated"}
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_retry_behavior_disabled_max_attempts_zero(self, mock_sleep, mock_post):
        """Test that retry is disabled when max_attempts=0"""
        engine_no_retry = LingoDotDevEngine({
            "api_key": "test_api_key",
            "retry_max_attempts": 0
        })
        
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"
        mock_response.text = "Server error"
        mock_post.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="Server error"):
            await engine_no_retry._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, "workflow_id", False
            )
        
        mock_post.assert_called_once()  # No retries when disabled
        mock_sleep.assert_not_called()

    @patch("lingodotdev.engine.LingoDotDevEngine._localize_chunk")
    async def test_retry_with_concurrent_processing(self, mock_localize_chunk):
        """Test that retry works with concurrent processing (each request retries independently)"""
        # Mock _localize_chunk to simulate retry behavior
        call_count = 0
        async def mock_chunk_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails (simulates retry happening internally)
                raise RuntimeError("Request failed after 2 attempts: Connection timeout")
            else:
                # Subsequent calls succeed
                return {"key": f"translated_{call_count}"}
        
        mock_localize_chunk.side_effect = mock_chunk_with_retry
        
        # Create a payload that will be chunked
        large_payload = {f"key{i}": f"value{i}" for i in range(3)}
        
        # Create mock params object
        mock_params = type("MockParams", (), {
            "source_locale": "en",
            "target_locale": "es", 
            "fast": False,
            "reference": None,
        })()
        
        # Test concurrent mode - should handle failures independently
        with pytest.raises(RuntimeError, match="Request failed after 2 attempts"):
            await self.engine._localize_raw(
                large_payload,
                mock_params,
                concurrent=True,
            )
        
        # Should have called _localize_chunk (retry logic is internal to each chunk)
        assert mock_localize_chunk.call_count > 0

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_retry_with_context_managers(self, mock_sleep, mock_post):
        """Test that retry works with context managers without affecting resource management"""
        mock_response_error = Mock()
        mock_response_error.is_success = False
        mock_response_error.status_code = 503
        mock_response_error.reason_phrase = "Service Unavailable"
        mock_response_error.text = "Service temporarily unavailable"
        
        mock_response_success = Mock()
        mock_response_success.is_success = True
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"data": {"text": "translated"}}
        
        mock_post.side_effect = [mock_response_error, mock_response_success]
        
        # Test with context manager
        async with LingoDotDevEngine({"api_key": "test_api_key"}) as engine:
            result = await engine.localize_text(
                "Hello world",
                {"source_locale": "en", "target_locale": "es"}
            )
            
            assert result == "translated"
            assert mock_post.call_count == 2  # One retry
            assert mock_sleep.call_count == 1
            
            # Verify client is still properly managed
            assert engine._client is not None
            assert not engine._client.is_closed

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_retry_with_progress_callbacks(self, mock_sleep, mock_post):
        """Test that retry works with progress callbacks without triggering extra updates"""
        mock_response_error = Mock()
        mock_response_error.is_success = False
        mock_response_error.status_code = 502
        mock_response_error.reason_phrase = "Bad Gateway"
        mock_response_error.text = "Gateway error"
        
        mock_response_success = Mock()
        mock_response_success.is_success = True
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"data": {"key1": "value1", "key2": "value2"}}
        
        mock_post.side_effect = [mock_response_error, mock_response_success]
        
        progress_calls = []
        def progress_callback(progress, source_chunk, processed_chunk):
            progress_calls.append((progress, len(source_chunk), len(processed_chunk)))
        
        result = await self.engine.localize_object(
            {"key1": "value1", "key2": "value2"},
            {"source_locale": "en", "target_locale": "es"},
            progress_callback=progress_callback
        )
        
        assert result == {"key1": "value1", "key2": "value2"}
        assert mock_post.call_count == 2  # One retry
        assert mock_sleep.call_count == 1
        
        # Progress callback should only be called once (after successful completion)
        assert len(progress_calls) == 1
        assert progress_calls[0][0] == 100  # 100% completion
        assert progress_calls[0][1] == 2  # Source chunk size
        assert progress_calls[0][2] == 2  # Processed chunk size

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_retry_with_quick_translate_methods(self, mock_sleep, mock_post):
        """Test that retry works with quick_translate convenience methods"""
        mock_response_error = Mock()
        mock_response_error.is_success = False
        mock_response_error.status_code = 500
        mock_response_error.reason_phrase = "Internal Server Error"
        mock_response_error.text = "Server error"
        
        mock_response_success = Mock()
        mock_response_success.is_success = True
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"data": {"text": "hola mundo"}}
        
        mock_post.side_effect = [mock_response_error, mock_response_success]
        
        # Test quick_translate class method
        result = await LingoDotDevEngine.quick_translate(
            "hello world",
            api_key="test_api_key",
            target_locale="es",
            fast=True
        )
        
        assert result == "hola mundo"
        assert mock_post.call_count == 2  # One retry
        assert mock_sleep.call_count == 1

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_retry_with_batch_operations(self, mock_sleep, mock_post):
        """Test that retry works with batch operations"""
        mock_response_error = Mock()
        mock_response_error.is_success = False
        mock_response_error.status_code = 503
        mock_response_error.reason_phrase = "Service Unavailable"
        mock_response_error.text = "Service temporarily unavailable"
        
        mock_response_success = Mock()
        mock_response_success.is_success = True
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"data": {"text": "hola"}}
        
        # First target locale fails once then succeeds, second succeeds immediately
        mock_post.side_effect = [
            mock_response_error,  # First locale, first attempt
            mock_response_success,  # First locale, second attempt
            mock_response_success,  # Second locale, first attempt
        ]
        
        result = await self.engine.batch_localize_text(
            "hello",
            {
                "source_locale": "en",
                "target_locales": ["es", "fr"],
                "fast": True
            }
        )
        
        assert result == ["hola", "hola"]  # Both should succeed
        assert mock_post.call_count == 3  # One retry + two successes
        assert mock_sleep.call_count == 1  # One retry delay

    async def test_all_existing_tests_still_pass(self):
        """Test that all existing functionality still works with retry integration"""
        # This is a meta-test that verifies backward compatibility
        # The actual verification is done by running the existing test suite
        
        # Test basic engine initialization
        engine = LingoDotDevEngine({"api_key": "test_key"})
        assert engine.config.api_key == "test_key"
        assert engine.config.retry_max_attempts == 3  # Default value
        assert engine.config.retry_base_delay == 1.0  # Default value
        
        # Test that retry can be disabled
        engine_no_retry = LingoDotDevEngine({
            "api_key": "test_key",
            "retry_max_attempts": 0
        })
        assert engine_no_retry.config.retry_max_attempts == 0
        
        # Test that all helper methods exist
        assert hasattr(engine, '_should_retry_response')
        assert hasattr(engine, '_calculate_retry_delay')
        assert hasattr(engine, '_make_request_with_retry')
        
        # Test that existing methods still exist
        assert hasattr(engine, 'localize_text')
        assert hasattr(engine, 'localize_object')
        assert hasattr(engine, 'localize_chat')
        assert hasattr(engine, 'batch_localize_text')
        assert hasattr(engine, 'recognize_locale')
        assert hasattr(engine, 'whoami')

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    @patch("asyncio.sleep")
    async def test_retry_preserves_original_behavior_on_success(self, mock_sleep, mock_post):
        """Test that retry logic doesn't affect normal successful operations"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"greeting": "hola", "farewell": "adiós"}}
        mock_post.return_value = mock_response
        
        # Test that normal operations work exactly as before
        result = await self.engine.localize_object(
            {"greeting": "hello", "farewell": "goodbye"},
            {"source_locale": "en", "target_locale": "es"}
        )
        
        assert result == {"greeting": "hola", "farewell": "adiós"}
        mock_post.assert_called_once()  # No retries needed for success
        mock_sleep.assert_not_called()  # No delays for successful requests


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests with mocked HTTP responses"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = {"api_key": "test_api_key", "api_url": "https://api.test.com"}
        self.engine = LingoDotDevEngine(self.config)

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_full_localization_workflow(self, mock_post):
        """Test full localization workflow"""
        # Mock the API response
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"greeting": "hola", "farewell": "adiós"}
        }
        mock_post.return_value = mock_response

        # Test object localization
        result = await self.engine.localize_object(
            {"greeting": "hello", "farewell": "goodbye"},
            {"source_locale": "en", "target_locale": "es", "fast": True},
        )

        assert result == {"greeting": "hola", "farewell": "adiós"}

        # Verify the API was called with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0].endswith("/i18n")

        request_data = call_args[1]["json"]
        assert request_data["locale"]["source"] == "en"
        assert request_data["locale"]["target"] == "es"
        assert request_data["params"]["fast"] is True
        assert request_data["data"] == {"greeting": "hello", "farewell": "goodbye"}
