"""
Tests for the LingoDotDevEngine class
"""

import pytest
from unittest.mock import Mock, patch

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
        )
        assert config.api_key == "test_key"
        assert config.api_url == "https://api.test.com"
        assert config.batch_size == 50
        assert config.ideal_batch_item_size == 500

    def test_default_values(self):
        """Test default configuration values"""
        config = EngineConfig(api_key="test_key")
        assert config.api_url == "https://engine.lingo.dev"
        assert config.batch_size == 25
        assert config.ideal_batch_item_size == 250

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


class TestLingoDotDevEngine:
    """Test the LingoDotDevEngine class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            "api_key": "test_api_key",
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
        assert "Authorization" in self.engine.session.headers
        assert self.engine.session.headers["Authorization"] == "Bearer test_api_key"

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

    @patch("lingodotdev.engine.requests.Session.post")
    def test_localize_chunk_success(self, mock_post):
        """Test successful chunk localization"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"data": {"key": "translated_value"}}
        mock_post.return_value = mock_response

        result = self.engine._localize_chunk(
            "en", "es", {"data": {"key": "value"}}, "workflow_id", False
        )

        assert result == {"key": "translated_value"}
        mock_post.assert_called_once()

    @patch("lingodotdev.engine.requests.Session.post")
    def test_localize_chunk_server_error(self, mock_post):
        """Test server error handling in chunk localization"""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.reason = "Internal Server Error"
        mock_response.text = "Server error details"
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="Server error"):
            self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, "workflow_id", False
            )

    @patch("lingodotdev.engine.requests.Session.post")
    def test_localize_chunk_bad_request(self, mock_post):
        """Test bad request handling in chunk localization"""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.reason = "Bad Request"
        mock_post.return_value = mock_response

        with pytest.raises(ValueError, match="Invalid request \\(400\\)"):
            self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, "workflow_id", False
            )

    @patch("lingodotdev.engine.requests.Session.post")
    def test_localize_chunk_streaming_error(self, mock_post):
        """Test streaming error handling in chunk localization"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"error": "Streaming error occurred"}
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="Streaming error occurred"):
            self.engine._localize_chunk(
                "en", "es", {"data": {"key": "value"}}, "workflow_id", False
            )

    @patch("lingodotdev.engine.LingoDotDevEngine._localize_raw")
    def test_localize_text(self, mock_localize_raw):
        """Test text localization"""
        mock_localize_raw.return_value = {"text": "translated_text"}

        result = self.engine.localize_text(
            "hello world", {"source_locale": "en", "target_locale": "es"}
        )

        assert result == "translated_text"
        mock_localize_raw.assert_called_once()

    @patch("lingodotdev.engine.LingoDotDevEngine._localize_raw")
    def test_localize_object(self, mock_localize_raw):
        """Test object localization"""
        mock_localize_raw.return_value = {"greeting": "hola", "farewell": "adiós"}

        result = self.engine.localize_object(
            {"greeting": "hello", "farewell": "goodbye"},
            {"source_locale": "en", "target_locale": "es"},
        )

        assert result == {"greeting": "hola", "farewell": "adiós"}
        mock_localize_raw.assert_called_once()

    @patch("lingodotdev.engine.LingoDotDevEngine.localize_text")
    def test_batch_localize_text(self, mock_localize_text):
        """Test batch text localization"""
        mock_localize_text.side_effect = ["hola", "bonjour"]

        result = self.engine.batch_localize_text(
            "hello",
            {"source_locale": "en", "target_locales": ["es", "fr"], "fast": True},
        )

        assert result == ["hola", "bonjour"]
        assert mock_localize_text.call_count == 2

    def test_batch_localize_text_missing_target_locales(self):
        """Test batch text localization with missing target_locales"""
        with pytest.raises(ValueError, match="target_locales is required"):
            self.engine.batch_localize_text("hello", {"source_locale": "en"})

    @patch("lingodotdev.engine.LingoDotDevEngine._localize_raw")
    def test_localize_chat(self, mock_localize_raw):
        """Test chat localization"""
        mock_localize_raw.return_value = {
            "chat": [
                {"name": "Alice", "text": "hola"},
                {"name": "Bob", "text": "adiós"},
            ]
        }

        chat = [{"name": "Alice", "text": "hello"}, {"name": "Bob", "text": "goodbye"}]

        result = self.engine.localize_chat(
            chat, {"source_locale": "en", "target_locale": "es"}
        )

        expected = [{"name": "Alice", "text": "hola"}, {"name": "Bob", "text": "adiós"}]

        assert result == expected
        mock_localize_raw.assert_called_once()

    def test_localize_chat_invalid_format(self):
        """Test chat localization with invalid message format"""
        invalid_chat = [{"name": "Alice"}]  # Missing 'text' key

        with pytest.raises(
            ValueError, match="Each chat message must have 'name' and 'text' properties"
        ):
            self.engine.localize_chat(
                invalid_chat, {"source_locale": "en", "target_locale": "es"}
            )

    @patch("lingodotdev.engine.requests.Session.post")
    def test_recognize_locale_success(self, mock_post):
        """Test successful locale recognition"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"locale": "es"}
        mock_post.return_value = mock_response

        result = self.engine.recognize_locale("Hola mundo")

        assert result == "es"
        mock_post.assert_called_once()

    def test_recognize_locale_empty_text(self):
        """Test locale recognition with empty text"""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            self.engine.recognize_locale("   ")

    @patch("lingodotdev.engine.requests.Session.post")
    def test_recognize_locale_server_error(self, mock_post):
        """Test locale recognition with server error"""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.reason = "Internal Server Error"
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="Server error"):
            self.engine.recognize_locale("Hello world")

    @patch("lingodotdev.engine.requests.Session.post")
    def test_whoami_success(self, mock_post):
        """Test successful whoami request"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "email": "test@example.com",
            "id": "user_123",
        }
        mock_post.return_value = mock_response

        result = self.engine.whoami()

        assert result == {"email": "test@example.com", "id": "user_123"}
        mock_post.assert_called_once()

    @patch("lingodotdev.engine.requests.Session.post")
    def test_whoami_unauthenticated(self, mock_post):
        """Test whoami request when unauthenticated"""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        result = self.engine.whoami()

        assert result is None

    @patch("lingodotdev.engine.requests.Session.post")
    def test_whoami_server_error(self, mock_post):
        """Test whoami request with server error"""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.reason = "Internal Server Error"
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="Server error"):
            self.engine.whoami()

    @patch("lingodotdev.engine.requests.Session.post")
    def test_whoami_no_email(self, mock_post):
        """Test whoami request with no email in response"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        result = self.engine.whoami()

        assert result is None


class TestIntegration:
    """Integration tests with mocked HTTP responses"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = {"api_key": "test_api_key", "api_url": "https://api.test.com"}
        self.engine = LingoDotDevEngine(self.config)

    @patch("lingodotdev.engine.requests.Session.post")
    def test_full_localization_workflow(self, mock_post):
        """Test full localization workflow"""
        # Mock the API response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "data": {"greeting": "hola", "farewell": "adiós"}
        }
        mock_post.return_value = mock_response

        # Test object localization
        result = self.engine.localize_object(
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
