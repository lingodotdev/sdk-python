"""
Integration tests for the LingoDotDevEngine
These tests can be run against a real API endpoint if provided
"""

import os
import pytest
from unittest.mock import patch, Mock

from lingodotdev import LingoDotDevEngine


# Skip integration tests if no API key is provided
pytestmark = pytest.mark.skipif(
    not os.getenv("LINGODOTDEV_API_KEY"),
    reason="Integration tests require LINGODOTDEV_API_KEY environment variable",
)


@pytest.mark.asyncio
class TestRealAPIIntegration:
    """Integration tests against the real API"""

    def setup_method(self):
        """Set up test fixtures"""
        api_key = os.getenv("LINGODOTDEV_API_KEY")
        if not api_key:
            pytest.skip("No API key provided")

        self.engine = LingoDotDevEngine(
            {
                "api_key": api_key,
                "api_url": os.getenv("LINGO_DEV_API_URL", "https://engine.lingo.dev"),
            }
        )

    async def test_localize_text_real_api(self):
        """Test text localization against real API"""
        async with self.engine:
            result = await self.engine.localize_text(
                "Hello, world!", {"source_locale": "en", "target_locale": "es"}
            )

            assert isinstance(result, str)
            assert len(result) > 0
            assert result != "Hello, world!"  # Should be translated

    async def test_localize_object_real_api(self):
        """Test object localization against real API"""
        test_object = {
            "greeting": "Hello",
            "farewell": "Goodbye",
            "question": "How are you?",
        }

        async with self.engine:
            result = await self.engine.localize_object(
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

    async def test_batch_localize_text_real_api(self):
        """Test batch text localization against real API"""
        async with self.engine:
            result = await self.engine.batch_localize_text(
                "Welcome to our application",
                {
                    "source_locale": "en",
                    "target_locales": ["es", "fr", "de"],
                    "fast": True,
                },
            )

            assert isinstance(result, list)
            assert len(result) == 3

            # Each result should be a non-empty string
            for translation in result:
                assert isinstance(translation, str)
                assert len(translation) > 0
                assert translation != "Welcome to our application"

    async def test_localize_chat_real_api(self):
        """Test chat localization against real API"""
        chat = [
            {"name": "Alice", "text": "Hello everyone!"},
            {"name": "Bob", "text": "How are you doing?"},
            {"name": "Charlie", "text": "I'm doing great, thanks!"},
        ]

        async with self.engine:
            result = await self.engine.localize_chat(
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

    async def test_recognize_locale_real_api(self):
        """Test locale recognition against real API"""
        test_cases = [
            ("Hello, how are you?", "en"),
            ("Hola, ¿cómo estás?", "es"),
            ("Bonjour, comment allez-vous?", "fr"),
            ("Guten Tag, wie geht es Ihnen?", "de"),
        ]

        async with self.engine:
            for text, expected_locale in test_cases:
                result = await self.engine.recognize_locale(text)
                assert isinstance(result, str)
                assert len(result) > 0
                # Note: We don't assert exact match as recognition might vary
                # but we expect a reasonable locale code

    async def test_whoami_real_api(self):
        """Test whoami against real API"""
        async with self.engine:
            result = await self.engine.whoami()

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

    async def test_progress_callback(self):
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

        async with self.engine:
            await self.engine.localize_object(
                large_object,
                {"source_locale": "en", "target_locale": "es"},
                progress_callback=progress_callback,
            )

            assert len(progress_values) > 0
            assert max(progress_values) == 100  # Should reach 100% completion

    async def test_error_handling_invalid_locale(self):
        """Test error handling with invalid locale"""
        async with self.engine:
            with pytest.raises(Exception):  # Could be ValueError or RuntimeError
                await self.engine.localize_text(
                    "Hello world",
                    {"source_locale": "invalid_locale", "target_locale": "es"},
                )

    async def test_error_handling_empty_text(self):
        """Test error handling with empty text"""
        async with self.engine:
            with pytest.raises(ValueError):
                await self.engine.recognize_locale("")

    async def test_fast_mode(self):
        """Test fast mode functionality"""
        text = "This is a test for fast mode translation"

        async with self.engine:
            # Test with fast mode enabled
            result_fast = await self.engine.localize_text(
                text, {"source_locale": "en", "target_locale": "es", "fast": True}
            )

            # Test with fast mode disabled
            result_normal = await self.engine.localize_text(
                text, {"source_locale": "en", "target_locale": "es", "fast": False}
            )

            # Both should return valid translations
            assert isinstance(result_fast, str)
            assert isinstance(result_normal, str)
            assert len(result_fast) > 0
            assert len(result_normal) > 0
            assert result_fast != text
            assert result_normal != text

    async def test_concurrent_processing_performance(self):
        """Test concurrent processing performance improvement"""
        import time

        large_object = {
            f"key_{i}": f"Test content number {i} for performance testing"
            for i in range(10)
        }

        async with self.engine:
            # Test sequential processing
            start_time = time.time()
            await self.engine.localize_object(
                large_object,
                {"source_locale": "en", "target_locale": "es"},
                concurrent=False,
            )
            sequential_time = time.time() - start_time

            # Test concurrent processing
            start_time = time.time()
            await self.engine.localize_object(
                large_object,
                {"source_locale": "en", "target_locale": "es"},
                concurrent=True,
            )
            concurrent_time = time.time() - start_time

            # Concurrent processing should be faster (or at least not significantly slower)
            assert concurrent_time <= sequential_time * 1.5  # Allow 50% margin

    async def test_batch_localize_objects(self):
        """Test batch object localization"""
        objects = [
            {"greeting": "Hello", "question": "How are you?"},
            {"farewell": "Goodbye", "thanks": "Thank you"},
            {"welcome": "Welcome", "help": "Can I help you?"},
        ]

        async with self.engine:
            results = await self.engine.batch_localize_objects(
                objects, {"source_locale": "en", "target_locale": "es"}
            )

            assert len(results) == 3
            for i, result in enumerate(results):
                assert isinstance(result, dict)
                # Check that structure is preserved but content is translated
                for key in objects[i].keys():
                    assert key in result
                    assert result[key] != objects[i][key]  # Should be translated


@pytest.mark.asyncio
class TestMockedIntegration:
    """Integration tests with mocked responses for CI/CD"""

    def setup_method(self):
        """Set up test fixtures"""
        self.engine = LingoDotDevEngine(
            {"api_key": "test_api_key", "api_url": "https://api.test.com"}
        )

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_large_payload_chunking(self, mock_post):
        """Test that large payloads are properly chunked"""
        # Mock API response
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {"data": {"key": "value"}}
        mock_post.return_value = mock_response

        # Create a large payload that will be chunked
        large_payload = {f"key_{i}": f"value_{i}" for i in range(100)}

        await self.engine.localize_object(
            large_payload, {"source_locale": "en", "target_locale": "es"}
        )

        # Should have been called multiple times due to chunking
        assert mock_post.call_count > 1

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_reference_parameter(self, mock_post):
        """Test that reference parameter is properly handled"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {"data": {"key": "value"}}
        mock_post.return_value = mock_response

        reference = {
            "es": {"key": "valor de referencia"},
            "fr": {"key": "valeur de référence"},
        }

        await self.engine.localize_object(
            {"key": "value"},
            {"source_locale": "en", "target_locale": "es", "reference": reference},
        )

        # Check that reference was included in the request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        assert "reference" in request_data
        assert request_data["reference"] == reference

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_workflow_id_consistency(self, mock_post):
        """Test that workflow ID is consistent across chunks"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {"data": {"key": "value"}}
        mock_post.return_value = mock_response

        # Create a payload that will be chunked
        large_payload = {f"key_{i}": f"value_{i}" for i in range(50)}

        await self.engine.localize_object(
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

    @patch("lingodotdev.engine.httpx.AsyncClient.post")
    async def test_concurrent_chunk_processing(self, mock_post):
        """Test concurrent chunk processing"""
        import asyncio

        # Mock API response with delay to test concurrency
        async def mock_response_with_delay(*args, **kwargs):
            await asyncio.sleep(0.1)  # Small delay
            mock_resp = type("MockResponse", (), {})()
            mock_resp.is_success = True
            mock_resp.json = lambda: {"data": {"key": "value"}}
            return mock_resp

        mock_post.side_effect = mock_response_with_delay

        # Create a payload that will be chunked
        large_payload = {f"key_{i}": f"value_{i}" for i in range(10)}

        # Test concurrent processing
        start_time = asyncio.get_event_loop().time()
        await self.engine.localize_object(
            large_payload,
            {"source_locale": "en", "target_locale": "es"},
            concurrent=True,
        )
        concurrent_time = asyncio.get_event_loop().time() - start_time

        # With concurrent processing, total time should be less than
        # (number of chunks * delay) since requests run in parallel
        # Allow some margin for test execution overhead
        assert concurrent_time < (mock_post.call_count * 0.1) + 0.05
        assert mock_post.call_count > 0  # Should have been called
