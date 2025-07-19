"""
Tests for async public API methods

This module tests the async public API methods including alocalize_text,
alocalize_object, abatch_localize_text, alocalize_chat, arecognize_locale, and awhoami.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from src.lingodotdev.engine import LingoDotDevEngine
from src.lingodotdev.models import EnhancedEngineConfig
from src.lingodotdev.exceptions import LingoDevError, LingoDevAPIError


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
def engine(basic_config):
    """Engine instance for testing"""
    return LingoDotDevEngine(basic_config)


class TestAsyncPublicAPIMethods:
    """Test cases for async public API methods"""
    
    @pytest.mark.asyncio
    async def test_alocalize_text_success(self, engine):
        """Test successful async text localization"""
        with patch.object(engine, '_alocalize_raw') as mock_alocalize_raw:
            mock_alocalize_raw.return_value = {"text": "hola mundo"}
            
            result = await engine.alocalize_text(
                "hello world",
                {"source_locale": "en", "target_locale": "es"}
            )
            
            assert result == "hola mundo"
            
            # Verify the call was made correctly
            mock_alocalize_raw.assert_called_once()
            args = mock_alocalize_raw.call_args[0]
            assert args[0] == {"text": "hello world"}  # payload
            assert args[1].source_locale == "en"       # params
            assert args[1].target_locale == "es"
    
    @pytest.mark.asyncio
    async def test_alocalize_text_with_progress_callback(self, engine):
        """Test async text localization with progress callback"""
        progress_calls = []
        
        def progress_callback(progress):
            progress_calls.append(progress)
        
        with patch.object(engine, '_alocalize_raw') as mock_alocalize_raw:
            mock_alocalize_raw.return_value = {"text": "hola"}
            
            result = await engine.alocalize_text(
                "hello",
                {"source_locale": "en", "target_locale": "es"},
                progress_callback=progress_callback
            )
            
            assert result == "hola"
            
            # Verify progress callback wrapper was passed
            mock_alocalize_raw.assert_called_once()
            args = mock_alocalize_raw.call_args[0]
            assert len(args) == 3  # payload, params, progress_callback
            assert callable(args[2])  # progress callback wrapper
    
    @pytest.mark.asyncio
    async def test_alocalize_object_success(self, engine):
        """Test successful async object localization"""
        with patch.object(engine, '_alocalize_raw') as mock_alocalize_raw:
            mock_alocalize_raw.return_value = {
                "greeting": "hola",
                "farewell": "adiós"
            }
            
            obj = {"greeting": "hello", "farewell": "goodbye"}
            result = await engine.alocalize_object(
                obj,
                {"source_locale": "en", "target_locale": "es"}
            )
            
            assert result == {"greeting": "hola", "farewell": "adiós"}
            
            # Verify the call was made correctly
            mock_alocalize_raw.assert_called_once()
            args = mock_alocalize_raw.call_args[0]
            assert args[0] == obj  # payload
            assert args[1].source_locale == "en"
            assert args[1].target_locale == "es"
    
    @pytest.mark.asyncio
    async def test_alocalize_object_with_progress_callback(self, engine):
        """Test async object localization with progress callback"""
        progress_calls = []
        
        def progress_callback(progress, source_chunk, processed_chunk):
            progress_calls.append({
                "progress": progress,
                "source_chunk": source_chunk,
                "processed_chunk": processed_chunk
            })
        
        with patch.object(engine, '_alocalize_raw') as mock_alocalize_raw:
            mock_alocalize_raw.return_value = {"key": "valor"}
            
            obj = {"key": "value"}
            result = await engine.alocalize_object(
                obj,
                {"source_locale": "en", "target_locale": "es"},
                progress_callback=progress_callback
            )
            
            assert result == {"key": "valor"}
            
            # Verify progress callback was passed through
            mock_alocalize_raw.assert_called_once()
            args = mock_alocalize_raw.call_args[0]
            assert len(args) == 3
            assert args[2] is progress_callback  # Direct callback, not wrapped
    
    @pytest.mark.asyncio
    async def test_abatch_localize_text_success(self, engine):
        """Test successful async batch text localization"""
        # Mock individual alocalize_text calls
        with patch.object(engine, 'alocalize_text') as mock_alocalize_text:
            # Return different translations for different locales
            async def mock_localize_side_effect(text, params):
                if params["target_locale"] == "es":
                    return "hola"
                elif params["target_locale"] == "fr":
                    return "bonjour"
                else:
                    return "hello"
            
            mock_alocalize_text.side_effect = mock_localize_side_effect
            
            result = await engine.abatch_localize_text(
                "hello",
                {
                    "source_locale": "en",
                    "target_locales": ["es", "fr"],
                    "fast": True
                }
            )
            
            assert result == ["hola", "bonjour"]
            
            # Verify both calls were made concurrently
            assert mock_alocalize_text.call_count == 2
            
            # Check the calls were made with correct parameters
            calls = mock_alocalize_text.call_args_list
            assert calls[0][0][0] == "hello"  # text
            assert calls[0][0][1]["target_locale"] == "es"
            assert calls[0][0][1]["fast"] is True
            
            assert calls[1][0][0] == "hello"  # text
            assert calls[1][0][1]["target_locale"] == "fr"
            assert calls[1][0][1]["fast"] is True
    
    @pytest.mark.asyncio
    async def test_abatch_localize_text_missing_target_locales(self, engine):
        """Test async batch localization with missing target_locales"""
        with pytest.raises(ValueError) as exc_info:
            await engine.abatch_localize_text(
                "hello",
                {"source_locale": "en"}  # Missing target_locales
            )
        
        assert "target_locales is required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_abatch_localize_text_concurrent_processing(self, engine):
        """Test that batch localization processes locales concurrently"""
        call_order = []
        
        async def mock_localize_with_delay(text, params):
            locale = params["target_locale"]
            call_order.append(f"start_{locale}")
            
            # Different delays to test concurrency
            if locale == "es":
                await asyncio.sleep(0.02)
            elif locale == "fr":
                await asyncio.sleep(0.01)
            else:
                await asyncio.sleep(0.03)
            
            call_order.append(f"end_{locale}")
            return f"translated_{locale}"
        
        with patch.object(engine, 'alocalize_text') as mock_alocalize_text:
            mock_alocalize_text.side_effect = mock_localize_with_delay
            
            result = await engine.abatch_localize_text(
                "hello",
                {
                    "source_locale": "en",
                    "target_locales": ["es", "fr", "de"]
                }
            )
            
            assert result == ["translated_es", "translated_fr", "translated_de"]
            
            # All should start before any finish (concurrent execution)
            start_calls = [call for call in call_order if call.startswith("start_")]
            end_calls = [call for call in call_order if call.startswith("end_")]
            
            # All starts should come before all ends if truly concurrent
            assert len(start_calls) == 3
            assert len(end_calls) == 3
    
    @pytest.mark.asyncio
    async def test_alocalize_chat_success(self, engine):
        """Test successful async chat localization"""
        chat = [
            {"name": "Alice", "text": "Hello"},
            {"name": "Bob", "text": "How are you?"}
        ]
        
        with patch.object(engine, '_alocalize_raw') as mock_alocalize_raw:
            mock_alocalize_raw.return_value = {
                "chat": [
                    {"name": "Alice", "text": "Hola"},
                    {"name": "Bob", "text": "¿Cómo estás?"}
                ]
            }
            
            result = await engine.alocalize_chat(
                chat,
                {"source_locale": "en", "target_locale": "es"}
            )
            
            expected = [
                {"name": "Alice", "text": "Hola"},
                {"name": "Bob", "text": "¿Cómo estás?"}
            ]
            assert result == expected
            
            # Verify the call was made correctly
            mock_alocalize_raw.assert_called_once()
            args = mock_alocalize_raw.call_args[0]
            assert args[0] == {"chat": chat}  # payload
    
    @pytest.mark.asyncio
    async def test_alocalize_chat_invalid_format(self, engine):
        """Test async chat localization with invalid message format"""
        invalid_chat = [
            {"name": "Alice", "text": "Hello"},
            {"name": "Bob"}  # Missing 'text' field
        ]
        
        with pytest.raises(ValueError) as exc_info:
            await engine.alocalize_chat(
                invalid_chat,
                {"source_locale": "en", "target_locale": "es"}
            )
        
        assert "Each chat message must have 'name' and 'text' properties" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_alocalize_chat_with_progress_callback(self, engine):
        """Test async chat localization with progress callback"""
        progress_calls = []
        
        def progress_callback(progress):
            progress_calls.append(progress)
        
        chat = [{"name": "Alice", "text": "Hello"}]
        
        with patch.object(engine, '_alocalize_raw') as mock_alocalize_raw:
            mock_alocalize_raw.return_value = {
                "chat": [{"name": "Alice", "text": "Hola"}]
            }
            
            result = await engine.alocalize_chat(
                chat,
                {"source_locale": "en", "target_locale": "es"},
                progress_callback=progress_callback
            )
            
            assert result == [{"name": "Alice", "text": "Hola"}]
            
            # Verify progress callback wrapper was passed
            mock_alocalize_raw.assert_called_once()
            args = mock_alocalize_raw.call_args[0]
            assert len(args) == 3
            assert callable(args[2])  # progress callback wrapper
    
    @pytest.mark.asyncio
    async def test_arecognize_locale_success(self, engine):
        """Test successful async locale recognition"""
        mock_async_client = AsyncMock()
        mock_response = {"locale": "es"}
        mock_async_client.post.return_value = mock_response
        
        with patch.object(engine, '_get_async_client', return_value=mock_async_client):
            result = await engine.arecognize_locale("Hola mundo")
            
            assert result == "es"
            
            # Verify the API call was made correctly
            mock_async_client.post.assert_called_once_with(
                "/recognize",
                {"text": "Hola mundo"}
            )
    
    @pytest.mark.asyncio
    async def test_arecognize_locale_empty_text(self, engine):
        """Test async locale recognition with empty text"""
        with pytest.raises(ValueError) as exc_info:
            await engine.arecognize_locale("")
        
        assert "Text cannot be empty" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            await engine.arecognize_locale("   ")  # Whitespace only
        
        assert "Text cannot be empty" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_arecognize_locale_no_locale_returned(self, engine):
        """Test async locale recognition when no locale is returned"""
        mock_async_client = AsyncMock()
        mock_response = {}  # No locale field
        mock_async_client.post.return_value = mock_response
        
        with patch.object(engine, '_get_async_client', return_value=mock_async_client):
            result = await engine.arecognize_locale("Some text")
            
            assert result == ""  # Should return empty string
    
    @pytest.mark.asyncio
    async def test_awhoami_success(self, engine):
        """Test successful async whoami"""
        mock_async_client = AsyncMock()
        mock_response = {
            "email": "test@example.com",
            "id": "user123"
        }
        mock_async_client.post.return_value = mock_response
        
        with patch.object(engine, '_get_async_client', return_value=mock_async_client):
            result = await engine.awhoami()
            
            assert result == {
                "email": "test@example.com",
                "id": "user123"
            }
            
            # Verify the API call was made correctly
            mock_async_client.post.assert_called_once_with("/whoami", {})
    
    @pytest.mark.asyncio
    async def test_awhoami_no_email(self, engine):
        """Test async whoami when no email is returned"""
        mock_async_client = AsyncMock()
        mock_response = {}  # No email field
        mock_async_client.post.return_value = mock_response
        
        with patch.object(engine, '_get_async_client', return_value=mock_async_client):
            result = await engine.awhoami()
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_awhoami_error_handling(self, engine):
        """Test async whoami error handling"""
        mock_async_client = AsyncMock()
        mock_async_client.post.side_effect = LingoDevAPIError(
            "API Error", 500, "Server Error"
        )
        
        with patch.object(engine, '_get_async_client', return_value=mock_async_client):
            result = await engine.awhoami()
            
            # Should return None on errors, not raise
            assert result is None


class TestAsyncPublicAPIIntegration:
    """Integration tests for async public API methods"""
    
    @pytest.mark.asyncio
    async def test_async_methods_use_same_client(self, engine):
        """Test that multiple async methods use the same client instance"""
        mock_async_client = AsyncMock()
        mock_async_client.is_closed = False
        mock_async_client.post.return_value = {"locale": "en"}
        
        with patch.object(engine, '_get_async_client', return_value=mock_async_client) as mock_get_client:
            # Make multiple async calls
            await engine.arecognize_locale("Hello")
            await engine.awhoami()
            
            # Client should be retrieved for each call but reused
            assert mock_get_client.call_count == 2
            assert mock_async_client.post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_async_methods_parameter_validation(self, engine):
        """Test parameter validation in async methods"""
        # Test LocalizationParams validation
        with pytest.raises(Exception):  # Should raise validation error
            await engine.alocalize_text(
                "hello",
                {"target_locale": ""}  # Invalid empty locale
            )
        
        # Test chat validation
        with pytest.raises(ValueError):
            await engine.alocalize_chat(
                [{"name": "Alice"}],  # Missing 'text'
                {"target_locale": "es"}
            )
    
    @pytest.mark.asyncio
    async def test_async_methods_concurrent_execution(self, engine):
        """Test that async methods can be executed concurrently"""
        mock_async_client = AsyncMock()
        mock_async_client.is_closed = False
        
        # Different responses for different endpoints
        async def mock_post_side_effect(endpoint, data):
            if endpoint == "/recognize":
                await asyncio.sleep(0.01)  # Simulate network delay
                return {"locale": "en"}
            elif endpoint == "/whoami":
                await asyncio.sleep(0.01)
                return {"email": "test@example.com", "id": "123"}
            else:
                return {}
        
        mock_async_client.post.side_effect = mock_post_side_effect
        
        with patch.object(engine, '_get_async_client', return_value=mock_async_client):
            # Execute multiple async methods concurrently
            tasks = [
                engine.arecognize_locale("Hello world"),
                engine.awhoami(),
                engine.arecognize_locale("Bonjour monde")
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert results[0] == "en"
            assert results[1] == {"email": "test@example.com", "id": "123"}
            assert results[2] == "en"
            
            # All calls should have been made
            assert mock_async_client.post.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__])