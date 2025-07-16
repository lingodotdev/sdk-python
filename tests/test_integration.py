"""
Integration tests for the LingoDotDevEngine
These tests can be run against a real API endpoint if provided
"""

import os
import pytest
from unittest.mock import patch

from lingodotdev import LingoDotDevEngine


# Skip integration tests if no API key is provided
pytestmark = pytest.mark.skipif(
    not os.getenv("LINGO_DEV_API_KEY"),
    reason="Integration tests require LINGO_DEV_API_KEY environment variable",
)


class TestRealAPIIntegration:
    """Integration tests against the real API"""

    def setup_method(self):
        """Set up test fixtures"""
        api_key = os.getenv("LINGO_DEV_API_KEY")
        if not api_key:
            pytest.skip("No API key provided")

        self.engine = LingoDotDevEngine(
            {
                "api_key": api_key,
                "api_url": os.getenv("LINGO_DEV_API_URL", "https://engine.lingo.dev"),
            }
        )

    def test_localize_text_real_api(self):
        """Test text localization against real API"""
        result = self.engine.localize_text(
            "Hello, world!", {"source_locale": "en", "target_locale": "es"}
        )

        assert isinstance(result, str)
        assert len(result) > 0
        assert result != "Hello, world!"  # Should be translated

    def test_localize_object_real_api(self):
        """Test object localization against real API"""
        test_object = {
            "greeting": "Hello",
            "farewell": "Goodbye",
            "question": "How are you?",
        }

        result = self.engine.localize_object(
            test_object, {"source_locale": "en", "target_locale": "fr"}
        )

        assert isinstance(result, dict)
        assert len(result) == 3
        assert "greeting" in result
        assert "farewell" in result
        assert "question" in result

        # Values should be translated
        assert result["greeting"] != "Hello"
        assert result["farewell"] != "Goodbye"
        assert result["question"] != "How are you?"

    def test_batch_localize_text_real_api(self):
        """Test batch text localization against real API"""
        result = self.engine.batch_localize_text(
            "Welcome to our application",
            {"source_locale": "en", "target_locales": ["es", "fr", "de"], "fast": True},
        )

        assert isinstance(result, list)
        assert len(result) == 3

        # Each result should be a non-empty string
        for translation in result:
            assert isinstance(translation, str)
            assert len(translation) > 0
            assert translation != "Welcome to our application"

    def test_localize_chat_real_api(self):
        """Test chat localization against real API"""
        chat = [
            {"name": "Alice", "text": "Hello everyone!"},
            {"name": "Bob", "text": "How are you doing?"},
            {"name": "Charlie", "text": "I'm doing great, thanks!"},
        ]

        result = self.engine.localize_chat(
            chat, {"source_locale": "en", "target_locale": "es"}
        )

        assert isinstance(result, list)
        assert len(result) == 3

        # Check structure is preserved
        for i, message in enumerate(result):
            assert isinstance(message, dict)
            assert "name" in message
            assert "text" in message
            assert message["name"] == chat[i]["name"]  # Names should be preserved
            assert message["text"] != chat[i]["text"]  # Text should be translated

    def test_recognize_locale_real_api(self):
        """Test locale recognition against real API"""
        test_cases = [
            ("Hello, how are you?", "en"),
            ("Hola, ¿cómo estás?", "es"),
            ("Bonjour, comment allez-vous?", "fr"),
            ("Guten Tag, wie geht es Ihnen?", "de"),
        ]

        for text, expected_locale in test_cases:
            result = self.engine.recognize_locale(text)
            assert isinstance(result, str)
            assert len(result) > 0
            # Note: We don't assert exact match as recognition might vary
            # but we expect a reasonable locale code

    def test_whoami_real_api(self):
        """Test whoami against real API"""
        result = self.engine.whoami()

        if result:  # If authenticated
            assert isinstance(result, dict)
            assert "email" in result
            assert "id" in result
            assert isinstance(result["email"], str)
            assert isinstance(result["id"], str)
            assert "@" in result["email"]  # Basic email validation
        else:
            # If not authenticated, should return None
            assert result is None

    def test_progress_callback(self):
        """Test progress callback functionality"""
        progress_values = []

        def progress_callback(progress, source_chunk, processed_chunk):
            progress_values.append(progress)
            assert isinstance(progress, int)
            assert 0 <= progress <= 100
            assert isinstance(source_chunk, dict)
            assert isinstance(processed_chunk, dict)

        # Create a larger object to ensure chunking and progress callbacks
        large_object = {f"key_{i}": f"This is test text number {i}" for i in range(50)}

        self.engine.localize_object(
            large_object,
            {"source_locale": "en", "target_locale": "es"},
            progress_callback=progress_callback,
        )

        assert len(progress_values) > 0
        assert max(progress_values) == 100  # Should reach 100% completion

    def test_error_handling_invalid_locale(self):
        """Test error handling with invalid locale"""
        with pytest.raises(Exception):  # Could be ValueError or RuntimeError
            self.engine.localize_text(
                "Hello world",
                {"source_locale": "invalid_locale", "target_locale": "es"},
            )

    def test_error_handling_empty_text(self):
        """Test error handling with empty text"""
        with pytest.raises(ValueError):
            self.engine.recognize_locale("")

    def test_fast_mode(self):
        """Test fast mode functionality"""
        text = "This is a test for fast mode translation"

        # Test with fast mode enabled
        result_fast = self.engine.localize_text(
            text, {"source_locale": "en", "target_locale": "es", "fast": True}
        )

        # Test with fast mode disabled
        result_normal = self.engine.localize_text(
            text, {"source_locale": "en", "target_locale": "es", "fast": False}
        )

        # Both should return valid translations
        assert isinstance(result_fast, str)
        assert isinstance(result_normal, str)
        assert len(result_fast) > 0
        assert len(result_normal) > 0
        assert result_fast != text
        assert result_normal != text


class TestMockedIntegration:
    """Integration tests with mocked responses for CI/CD"""

    def setup_method(self):
        """Set up test fixtures"""
        self.engine = LingoDotDevEngine(
            {"api_key": "test_api_key", "api_url": "https://api.test.com"}
        )

    @patch("lingodotdev.engine.requests.Session.post")
    def test_large_payload_chunking(self, mock_post):
        """Test that large payloads are properly chunked"""
        # Mock API response
        mock_response = mock_post.return_value
        mock_response.ok = True
        mock_response.json.return_value = {"data": {"key": "value"}}

        # Create a large payload that will be chunked
        large_payload = {f"key_{i}": f"value_{i}" for i in range(100)}

        self.engine.localize_object(
            large_payload, {"source_locale": "en", "target_locale": "es"}
        )

        # Should have been called multiple times due to chunking
        assert mock_post.call_count > 1

    @patch("lingodotdev.engine.requests.Session.post")
    def test_reference_parameter(self, mock_post):
        """Test that reference parameter is properly handled"""
        mock_response = mock_post.return_value
        mock_response.ok = True
        mock_response.json.return_value = {"data": {"key": "value"}}

        reference = {
            "es": {"key": "valor de referencia"},
            "fr": {"key": "valeur de référence"},
        }

        self.engine.localize_object(
            {"key": "value"},
            {"source_locale": "en", "target_locale": "es", "reference": reference},
        )

        # Check that reference was included in the request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        assert "reference" in request_data
        assert request_data["reference"] == reference

    @patch("lingodotdev.engine.requests.Session.post")
    def test_workflow_id_consistency(self, mock_post):
        """Test that workflow ID is consistent across chunks"""
        mock_response = mock_post.return_value
        mock_response.ok = True
        mock_response.json.return_value = {"data": {"key": "value"}}

        # Create a payload that will be chunked
        large_payload = {f"key_{i}": f"value_{i}" for i in range(50)}

        self.engine.localize_object(
            large_payload, {"source_locale": "en", "target_locale": "es"}
        )

        # Extract workflow IDs from all calls
        workflow_ids = []
        for call in mock_post.call_args_list:
            request_data = call[1]["json"]
            workflow_id = request_data["params"]["workflowId"]
            workflow_ids.append(workflow_id)

        # All workflow IDs should be the same
        assert len(set(workflow_ids)) == 1
        assert len(workflow_ids[0]) > 0  # Should be a non-empty string
