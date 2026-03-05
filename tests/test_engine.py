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
            engine_id="my-engine",
            api_url="https://api.test.com",
            batch_size=50,
            ideal_batch_item_size=500,
        )
        assert config.api_key == "test_key"
        assert config.engine_id == "my-engine"
        assert config.api_url == "https://api.test.com"
        assert config.batch_size == 50
        assert config.ideal_batch_item_size == 500

    def test_default_values(self):
        """Test default configuration values"""
        config = EngineConfig(api_key="test_key", engine_id="my-engine")
        assert config.api_url == "https://api.lingo.dev"
        assert config.batch_size == 25
        assert config.ideal_batch_item_size == 250

    def test_engine_id_optional(self):
        """Test that engine_id is optional and defaults to None"""
        config = EngineConfig(api_key="test_key")
        assert config.engine_id is None

    def test_engine_id_empty_string_becomes_none(self):
        """Test that empty engine_id becomes None"""
        config = EngineConfig(api_key="test_key", engine_id="")
        assert config.engine_id is None

    def test_engine_id_whitespace_becomes_none(self):
        """Test that whitespace-only engine_id becomes None"""
        config = EngineConfig(api_key="test_key", engine_id="  ")
        assert config.engine_id is None

    def test_engine_id_stripped(self):
        """Test that engine_id is stripped of whitespace"""
        config = EngineConfig(api_key="test_key", engine_id=" eng_123 ")
        assert config.engine_id == "eng_123"

    def test_invalid_api_url(self):
        """Test invalid API URL validation"""
        with pytest.raises(ValueError, match="API URL must be a valid HTTP/HTTPS URL"):
            EngineConfig(api_key="test_key", engine_id="eng", api_url="invalid_url")

    def test_api_url_trailing_slash_stripped(self):
        """Test that trailing slash is stripped from api_url"""
        config = EngineConfig(
            api_key="test_key", engine_id="eng", api_url="https://custom.api.com/"
        )
        assert config.api_url == "https://custom.api.com"

    def test_invalid_batch_size(self):
        """Test invalid batch size validation"""
        with pytest.raises(ValueError):
            EngineConfig(api_key="test_key", engine_id="eng", batch_size=0)

        with pytest.raises(ValueError):
            EngineConfig(api_key="test_key", engine_id="eng", batch_size=300)

    def test_invalid_ideal_batch_item_size(self):
        """Test invalid ideal batch item size validation"""
        with pytest.raises(ValueError):
            EngineConfig(api_key="test_key", engine_id="eng", ideal_batch_item_size=0)

        with pytest.raises(ValueError):
            EngineConfig(
                api_key="test_key", engine_id="eng", ideal_batch_item_size=3000
            )


class TestErrorHandling:
    """Test error handling utilities for non-JSON responses (e.g., 502 HTML errors)"""

    def test_truncate_response_short_text(self):
        """Test that short responses are not truncated"""
        short_text = "Short error message"
        result = LingoDotDevEngine._truncate_response(short_text)
        assert result == short_text

    def test_truncate_response_long_text(self):
        """Test that long responses are truncated with ellipsis"""
        long_text = "x" * 300
        result = LingoDotDevEngine._truncate_response(long_text)
        assert len(result) == 203  # 200 chars + "..."
        assert result.endswith("...")

    def test_truncate_response_custom_max_length(self):
        """Test truncation with custom max length"""
        text = "x" * 100
        result = LingoDotDevEngine._truncate_response(text, max_length=50)
        assert len(result) == 53  # 50 chars + "..."
        assert result.endswith("...")

    def test_truncate_response_exact_length(self):
        """Test text exactly at max length is not truncated"""
        text = "x" * 200
        result = LingoDotDevEngine._truncate_response(text, max_length=200)
        assert result == text
        assert not result.endswith("...")

    def test_safe_parse_json_valid_json(self):
        """Test parsing valid JSON response"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {"data": "test"}

        result = LingoDotDevEngine._safe_parse_json(mock_response)
        assert result == {"data": "test"}

    def test_safe_parse_json_html_response(self):
        """Test handling HTML response (like 502 error page)"""
        import json as json_module

        # Use a large HTML body (>200 chars) to test truncation
        html_body = """<!DOCTYPE html>
<html>
<head><title>502 Bad Gateway</title></head>
<body>
<center><h1>502 Bad Gateway</h1></center>
<p>The server encountered a temporary error and could not complete your request.</p>
<p>Please try again in a few moments. If the problem persists, contact support.</p>
<hr><center>nginx/1.18.0 (Ubuntu)</center>
</body>
</html>"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.side_effect = json_module.JSONDecodeError(
            "Expecting value", html_body, 0
        )
        mock_response.text = html_body
        mock_response.status_code = 502

        with pytest.raises(RuntimeError) as exc_info:
            LingoDotDevEngine._safe_parse_json(mock_response)

        error_msg = str(exc_info.value)
        assert "Failed to parse API response as JSON" in error_msg
        assert "status 502" in error_msg
        assert "gateway or proxy error" in error_msg
        # Verify HTML is truncated (original is ~400 chars, should be truncated to 200 + ...)
        assert "..." in error_msg
        assert len(error_msg) < len(html_body) + 150

    def test_safe_parse_json_empty_response(self):
        """Test handling empty response body"""
        import json as json_module

        mock_response = Mock(spec=httpx.Response)
        mock_response.json.side_effect = json_module.JSONDecodeError(
            "Expecting value", "", 0
        )
        mock_response.text = ""
        mock_response.status_code = 500

        with pytest.raises(RuntimeError) as exc_info:
            LingoDotDevEngine._safe_parse_json(mock_response)

        assert "status 500" in str(exc_info.value)

    def test_safe_parse_json_malformed_json(self):
        """Test handling malformed JSON response"""
        import json as json_module

        mock_response = Mock(spec=httpx.Response)
        mock_response.json.side_effect = json_module.JSONDecodeError(
            "Expecting value", '{"data": incomplete', 8
        )
        mock_response.text = '{"data": incomplete'
        mock_response.status_code = 200

        with pytest.raises(RuntimeError) as exc_info:
            LingoDotDevEngine._safe_parse_json(mock_response)

        assert "Failed to parse API response as JSON" in str(exc_info.value)


@pytest.mark.asyncio
class TestErrorHandlingIntegration:
    """Integration tests for error handling with mocked HTTP responses"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            "api_key": "test_api_key",
            "engine_id": "test-engine",
            "api_url": "https://api.test.com",
        }
        self.engine = LingoDotDevEngine(self.config)

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_localize_chunk_502_html_response(self, mock_post):
        """Test that 502 with HTML body raises clean RuntimeError"""
        html_body = "<html><body><h1>502 Bad Gateway</h1></body></html>"
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 502
        mock_response.reason_phrase = "Bad Gateway"
        mock_response.text = html_body
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            await self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, False
            )

        error_msg = str(exc_info.value)
        assert "Server error (502)" in error_msg
        assert "Bad Gateway" in error_msg
        assert "temporary service issues" in error_msg

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_localize_chunk_success_but_html_response(self, mock_post):
        """Test handling when server returns 200 but with HTML body (edge case)"""
        import json as json_module

        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.side_effect = json_module.JSONDecodeError(
            "Expecting value", "<html>Unexpected HTML</html>", 0
        )
        mock_response.text = "<html>Unexpected HTML</html>"
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            await self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, False
            )

        assert "Failed to parse API response as JSON" in str(exc_info.value)

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_recognize_locale_502_html_response(self, mock_post):
        """Test recognize_locale handles 502 HTML gracefully"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 502
        mock_response.reason_phrase = "Bad Gateway"
        mock_response.text = "<html><body>502 Bad Gateway</body></html>"
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            await self.engine.recognize_locale("Hello world")

        error_msg = str(exc_info.value)
        assert "Server error (502)" in error_msg

    @patch("lingodotdev.engine.httpx.AsyncClient.get")
    async def test_whoami_502_html_response(self, mock_get):
        """Test whoami handles 502 HTML gracefully"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 502
        mock_response.reason_phrase = "Bad Gateway"
        mock_response.text = "<html><body>502 Bad Gateway</body></html>"
        mock_get.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            await self.engine.whoami()

        error_msg = str(exc_info.value)
        assert "Server error (502)" in error_msg

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_error_message_truncation_in_api_call(self, mock_post):
        """Test that large HTML error pages are truncated in error messages"""
        large_html = "<html>" + "x" * 1000 + "</html>"
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 503
        mock_response.reason_phrase = "Service Unavailable"
        mock_response.text = large_html
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            await self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, False
            )

        error_msg = str(exc_info.value)
        # Error message should be much shorter than the full HTML
        assert len(error_msg) < 500
        assert "..." in error_msg  # Truncation indicator


@pytest.mark.asyncio
class TestLingoDotDevEngine:
    """Test the LingoDotDevEngine class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            "api_key": "test_api_key",
            "engine_id": "test-engine",
            "api_url": "https://api.test.com",
            "batch_size": 10,
            "ideal_batch_item_size": 100,
        }
        self.engine = LingoDotDevEngine(self.config)

    def test_initialization(self):
        """Test engine initialization"""
        assert self.engine.config.api_key == "test_api_key"
        assert self.engine.config.api_url == "https://api.test.com"
        assert self.engine.config.batch_size == 10
        assert self.engine.config.ideal_batch_item_size == 100
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
        mock_response.json.return_value = {"data": {"key": "translated_value"}}
        mock_post.return_value = mock_response

        result = await self.engine._localize_chunk(
            "en", "es", {"data": {"key": "value"}}, False
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
                "en", "es", {"data": {"key": "value"}}, False
            )

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_localize_chunk_bad_request(self, mock_post):
        """Test bad request handling in chunk localization"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 400
        mock_response.reason_phrase = "Bad Request"
        mock_response.text = "Invalid parameters"
        mock_post.return_value = mock_response

        with pytest.raises(ValueError, match="Invalid request \\(400\\)"):
            await self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, False
            )

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_localize_chunk_streaming_error(self, mock_post):
        """Test streaming error handling in chunk localization"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {"error": "Streaming error occurred"}
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="Streaming error occurred"):
            await self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, False
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
        mock_response.text = "Server error details"
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="Server error"):
            await self.engine.recognize_locale("Hello world")

    @patch("lingodotdev.engine.httpx.AsyncClient.get")
    async def test_whoami_success(self, mock_get):
        """Test successful whoami request"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "email": "test@example.com",
            "id": "user_123",
        }
        mock_get.return_value = mock_response

        result = await self.engine.whoami()

        assert result == {"email": "test@example.com", "id": "user_123"}
        mock_get.assert_called_once()

    @patch("lingodotdev.engine.httpx.AsyncClient.get")
    async def test_whoami_unauthenticated(self, mock_get):
        """Test whoami request when unauthenticated"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = await self.engine.whoami()

        assert result is None

    @patch("lingodotdev.engine.httpx.AsyncClient.get")
    async def test_whoami_server_error(self, mock_get):
        """Test whoami request with server error"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"
        mock_response.text = "Server error details"
        mock_get.return_value = mock_response

        with pytest.raises(RuntimeError, match="Server error"):
            await self.engine.whoami()

    @patch("lingodotdev.engine.httpx.AsyncClient.get")
    async def test_whoami_no_email(self, mock_get):
        """Test whoami request with no email in response"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

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


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests with mocked HTTP responses"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            "api_key": "test_api_key",
            "engine_id": "my-engine-id",
        }
        self.engine = LingoDotDevEngine(self.config)

    def teardown_method(self):
        """Clean up engine client"""
        if self.engine._client and not self.engine._client.is_closed:
            asyncio.get_event_loop().run_until_complete(self.engine.close())

    def test_default_api_url(self):
        """Test that default api_url is api.lingo.dev"""
        assert self.engine.config.api_url == "https://api.lingo.dev"
        assert self.engine.config.engine_id == "my-engine-id"

    def test_explicit_api_url_preserved(self):
        """Test that explicit api_url is preserved"""
        engine = LingoDotDevEngine(
            {
                "api_key": "key",
                "engine_id": "eng",
                "api_url": "https://custom.api.com",
            }
        )
        assert engine.config.api_url == "https://custom.api.com"

    def test_session_id_generated(self):
        """Test that session_id is generated on init"""
        assert self.engine._session_id
        assert isinstance(self.engine._session_id, str)

    async def test_ensure_client_uses_x_api_key(self):
        """Test that engine uses X-API-Key header"""
        await self.engine._ensure_client()
        assert self.engine._client is not None
        assert self.engine._client.headers.get("x-api-key") == "test_api_key"
        assert "authorization" not in self.engine._client.headers
        await self.engine.close()

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_localize_chunk_url_and_body(self, mock_post):
        """Test localize chunk uses correct URL and body format"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {"data": {"key": "translated"}}
        mock_post.return_value = mock_response

        await self.engine._localize_chunk(
            "en",
            "es",
            {"data": {"key": "value"}, "reference": {"es": {"key": "ref"}}},
            True,
        )

        call_args = mock_post.call_args
        url = call_args[0][0]
        assert url == "https://api.lingo.dev/process/localize"

        body = call_args[1]["json"]
        assert body["sourceLocale"] == "en"
        assert body["targetLocale"] == "es"
        assert body["params"] == {"fast": True}
        assert body["data"] == {"key": "value"}
        assert body["sessionId"] == self.engine._session_id
        assert body["engineId"] == "my-engine-id"
        assert body["reference"] == {"es": {"key": "ref"}}

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_recognize_locale_url(self, mock_post):
        """Test recognize_locale uses correct URL"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {"locale": "es"}
        mock_post.return_value = mock_response

        await self.engine.recognize_locale("Hola mundo")

        url = mock_post.call_args[0][0]
        assert url == "https://api.lingo.dev/process/recognize"

    @patch("lingodotdev.engine.httpx.AsyncClient.get")
    async def test_whoami(self, mock_get):
        """Test whoami calls GET /users/me"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {"id": "usr_abc", "email": "user@example.com"}
        mock_get.return_value = mock_response

        result = await self.engine.whoami()

        assert result == {"email": "user@example.com", "id": "usr_abc"}
        url = mock_get.call_args[0][0]
        assert url == "https://api.lingo.dev/users/me"

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_full_localization_workflow(self, mock_post):
        """Test full localization workflow via localize_object"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {"data": {"greeting": "hola"}}
        mock_post.return_value = mock_response

        result = await self.engine.localize_object(
            {"greeting": "hello"},
            {"source_locale": "en", "target_locale": "es", "fast": True},
        )

        assert result == {"greeting": "hola"}

        call_args = mock_post.call_args
        url = call_args[0][0]
        assert url == "https://api.lingo.dev/process/localize"

        body = call_args[1]["json"]
        assert body["sourceLocale"] == "en"
        assert body["targetLocale"] == "es"
        assert body["engineId"] == "my-engine-id"
        assert "sessionId" in body

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_localize_without_engine_id(self, mock_post):
        """Test localization without engine_id omits engineId from body"""
        engine = LingoDotDevEngine({"api_key": "test_api_key"})

        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {"data": {"greeting": "hola"}}
        mock_post.return_value = mock_response

        result = await engine.localize_object(
            {"greeting": "hello"},
            {"source_locale": "en", "target_locale": "es", "fast": True},
        )

        assert result == {"greeting": "hola"}

        call_args = mock_post.call_args
        url = call_args[0][0]
        assert url == "https://api.lingo.dev/process/localize"

        body = call_args[1]["json"]
        assert "engineId" not in body
