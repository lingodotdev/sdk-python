import pytest
import json
from unittest.mock import Mock, patch, PropertyMock
from lingodotdev import LingoDotDevEngine

@pytest.mark.asyncio
async def test_malformed_unicode_handling():
    """Test that malformed unicode responses are handled gracefully"""
    config = {"api_key": "test_key", "api_url": "https://api.test.com"}
    
    # Invalid utf-8 sequence (0xFF)
    invalid_bytes = b"\xff\xfe\xfd" 

    # Re-writing the test to target a successful status code (e.g. 200) but invalid body
    # This triggers _safe_parse_json which is where the fix was applied
    with patch("lingodotdev.engine.httpx.AsyncClient.post") as mock_post:
        mock_response = Mock()
        mock_response.is_success = True 
        mock_response.status_code = 200
        # json() raises UnicodeDecodeError
        mock_response.json.side_effect = UnicodeDecodeError("utf-8", invalid_bytes, 0, 1, "invalid start byte")
        # text property also raises UnicodeDecodeError
        type(mock_response).text = PropertyMock(side_effect=UnicodeDecodeError("utf-8", invalid_bytes, 0, 1, "invalid start byte"))
        # content property returns the bytes
        mock_response.content = invalid_bytes
        
        mock_post.return_value = mock_response

        async with LingoDotDevEngine(config) as engine:
            try:
                await engine.localize_text("hello", {"target_locale": "es"})
                pytest.fail("RuntimeError was not raised")
            except RuntimeError as exc:
                print(f"Caught expected RuntimeError: {exc}")
                error_msg = str(exc)
                assert "Failed to parse API response as JSON" in error_msg
                assert "Response:" in error_msg
            except Exception as e:
                pytest.fail(f"Caught unexpected exception: {type(e).__name__}: {e}")
