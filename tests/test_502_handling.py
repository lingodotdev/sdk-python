import pytest
import json
from unittest.mock import Mock, patch
from lingodotdev import LingoDotDevEngine


@pytest.mark.asyncio
async def test_502_html_handling():
    """Test that 502 errors with HTML bodies are sanitized"""
    config = {"api_key": "test_key", "api_url": "https://api.test.com"}

    html_body = "<html><body>" + ("<h1>502 Bad Gateway</h1>" * 50) + "</body></html>"
    assert len(html_body) > 200  # Ensure it triggers truncation

    with patch("lingodotdev.engine.httpx.AsyncClient.post") as mock_post:
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 502
        mock_response.reason_phrase = "Bad Gateway"
        mock_response.text = html_body
        mock_response.json.side_effect = ValueError(
            "Not JSON"
        )  # simulating non-JSON response
        mock_post.return_value = mock_response

        async with LingoDotDevEngine(config) as engine:
            with pytest.raises(RuntimeError) as exc_info:
                await engine.localize_text("hello", {"target_locale": "es"})

        error_msg = str(exc_info.value)

        # Assertions
        assert "Server error (502): Bad Gateway." in error_msg
        assert "This may be due to temporary service issues." in error_msg
        assert "Response:" not in error_msg
        assert "<html>" not in error_msg
        assert "<body>" not in error_msg


@pytest.mark.asyncio
async def test_500_json_handling():
    """Test that 500 errors with JSON bodies are preserved"""
    config = {"api_key": "test_key", "api_url": "https://api.test.com"}
    error_json = {"error": "Specific internal error message"}

    with patch("lingodotdev.engine.httpx.AsyncClient.post") as mock_post:
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"
        mock_response.text = json.dumps(error_json)  # Needed for response_preview
        mock_response.json.return_value = error_json
        mock_post.return_value = mock_response

        async with LingoDotDevEngine(config) as engine:
            with pytest.raises(RuntimeError) as exc_info:
                await engine.localize_text("hello", {"target_locale": "es"})

        error_msg = str(exc_info.value)

        # Assertions
        assert "Server error (500): Internal Server Error." in error_msg
        assert "Specific internal error message" in error_msg
