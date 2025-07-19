"""
Tests for async core processing methods

This module tests the async core processing functionality including
_alocalize_chunk, _alocalize_raw, concurrent processing, and semaphore control.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.lingodotdev.engine import LingoDotDevEngine
from src.lingodotdev.models import EnhancedEngineConfig, LocalizationParams
from src.lingodotdev.exceptions import LingoDevAPIError


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


@pytest.fixture
def localization_params():
    """Basic localization parameters"""
    return LocalizationParams(
        source_locale="en",
        target_locale="es",
        fast=False
    )


class TestAsyncCoreProcessingMethods:
    """Test cases for async core processing methods"""
    
    @pytest.mark.asyncio
    async def test_alocalize_chunk_success(self, engine, localization_params):
        """Test successful async chunk localization"""
        # Mock the async client
        mock_async_client = AsyncMock()
        mock_response = {"data": {"hello": "hola", "world": "mundo"}}
        mock_async_client.post.return_value = mock_response
        
        with patch.object(engine, '_get_async_client', return_value=mock_async_client):
            payload = {"data": {"hello": "world"}}
            result = await engine._alocalize_chunk(
                "en", "es", payload, "test-workflow", False
            )
            
            assert result == {"hello": "hola", "world": "mundo"}
            
            # Verify the API call was made correctly
            mock_async_client.post.assert_called_once_with(
                "/i18n",
                {
                    "params": {"workflowId": "test-workflow", "fast": False},
                    "locale": {"source": "en", "target": "es"},
                    "data": {"hello": "world"},
                }
            )
    
    @pytest.mark.asyncio
    async def test_alocalize_chunk_with_reference(self, engine):
        """Test async chunk localization with reference data"""
        mock_async_client = AsyncMock()
        mock_response = {"data": {"test": "prueba"}}
        mock_async_client.post.return_value = mock_response
        
        with patch.object(engine, '_get_async_client', return_value=mock_async_client):
            payload = {
                "data": {"test": "data"},
                "reference": {"context": {"key": "value"}}
            }
            
            result = await engine._alocalize_chunk(
                "en", "es", payload, "test-workflow", True
            )
            
            assert result == {"test": "prueba"}
            
            # Verify reference was included in the request
            call_args = mock_async_client.post.call_args[0][1]
            assert "reference" in call_args
            assert call_args["reference"] == {"context": {"key": "value"}}
    
    @pytest.mark.asyncio
    async def test_alocalize_chunk_streaming_error(self, engine):
        """Test handling of streaming errors in async chunk localization"""
        mock_async_client = AsyncMock()
        mock_response = {"error": "Streaming failed", "data": None}
        mock_async_client.post.return_value = mock_response
        
        with patch.object(engine, '_get_async_client', return_value=mock_async_client):
            payload = {"data": {"test": "data"}}
            
            with pytest.raises(LingoDevAPIError) as exc_info:
                await engine._alocalize_chunk(
                    "en", "es", payload, "test-workflow", False
                )
            
            error = exc_info.value
            assert "API streaming error" in str(error)
            assert "Streaming failed" in str(error)
    
    @pytest.mark.asyncio
    async def test_alocalize_raw_single_chunk(self, engine, localization_params):
        """Test async raw localization with single chunk"""
        # Mock the chunk processing
        with patch.object(engine, '_extract_payload_chunks') as mock_extract:
            with patch.object(engine, '_alocalize_chunk') as mock_alocalize_chunk:
                mock_extract.return_value = [{"key1": "value1", "key2": "value2"}]
                mock_alocalize_chunk.return_value = {"key1": "valor1", "key2": "valor2"}
                
                payload = {"key1": "value1", "key2": "value2"}
                result = await engine._alocalize_raw(payload, localization_params)
                
                assert result == {"key1": "valor1", "key2": "valor2"}
                
                # Verify chunk processing was called correctly
                mock_alocalize_chunk.assert_called_once()
                args = mock_alocalize_chunk.call_args[0]
                assert args[0] == "en"  # source_locale
                assert args[1] == "es"  # target_locale
                assert args[3] != ""    # workflow_id should be generated
                assert args[4] is False # fast mode
    
    @pytest.mark.asyncio
    async def test_alocalize_raw_multiple_chunks_concurrent(self, engine, localization_params):
        """Test async raw localization with multiple chunks processed concurrently"""
        # Mock the chunk processing
        with patch.object(engine, '_extract_payload_chunks') as mock_extract:
            with patch.object(engine, '_alocalize_chunk') as mock_alocalize_chunk:
                # Simulate 3 chunks
                mock_extract.return_value = [
                    {"chunk1": "data1"},
                    {"chunk2": "data2"}, 
                    {"chunk3": "data3"}
                ]
                
                # Mock responses for each chunk
                async def mock_chunk_response(*args, **kwargs):
                    chunk_data = args[2]["data"]  # payload["data"]
                    if "chunk1" in chunk_data:
                        return {"chunk1": "datos1"}
                    elif "chunk2" in chunk_data:
                        return {"chunk2": "datos2"}
                    else:
                        return {"chunk3": "datos3"}
                
                mock_alocalize_chunk.side_effect = mock_chunk_response
                
                payload = {"chunk1": "data1", "chunk2": "data2", "chunk3": "data3"}
                result = await engine._alocalize_raw(payload, localization_params)
                
                # All chunks should be combined
                expected = {"chunk1": "datos1", "chunk2": "datos2", "chunk3": "datos3"}
                assert result == expected
                
                # Verify all chunks were processed
                assert mock_alocalize_chunk.call_count == 3
    
    @pytest.mark.asyncio
    async def test_alocalize_raw_with_progress_callback(self, engine, localization_params):
        """Test async raw localization with progress callback"""
        progress_calls = []
        
        def progress_callback(progress, source_chunk, processed_chunk):
            progress_calls.append({
                "progress": progress,
                "source_chunk": source_chunk,
                "processed_chunk": processed_chunk
            })
        
        with patch.object(engine, '_extract_payload_chunks') as mock_extract:
            with patch.object(engine, '_alocalize_chunk') as mock_alocalize_chunk:
                mock_extract.return_value = [
                    {"chunk1": "data1"},
                    {"chunk2": "data2"}
                ]
                
                async def mock_chunk_response(*args, **kwargs):
                    chunk_data = args[2]["data"]
                    if "chunk1" in chunk_data:
                        return {"chunk1": "datos1"}
                    else:
                        return {"chunk2": "datos2"}
                
                mock_alocalize_chunk.side_effect = mock_chunk_response
                
                payload = {"chunk1": "data1", "chunk2": "data2"}
                await engine._alocalize_raw(
                    payload, 
                    localization_params, 
                    progress_callback=progress_callback
                )
                
                # Progress callback should have been called for each chunk
                assert len(progress_calls) == 2
                
                # Check progress values (should be 50% and 100%)
                progress_values = [call["progress"] for call in progress_calls]
                assert 50 in progress_values
                assert 100 in progress_values
    
    @pytest.mark.asyncio
    async def test_alocalize_raw_semaphore_control(self, engine, localization_params):
        """Test that semaphore properly controls concurrent requests"""
        # Track concurrent executions
        concurrent_count = 0
        max_concurrent = 0
        
        async def mock_chunk_with_delay(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            concurrent_count -= 1
            return {"result": "data"}
        
        with patch.object(engine, '_extract_payload_chunks') as mock_extract:
            with patch.object(engine, '_alocalize_chunk') as mock_alocalize_chunk:
                # Create many chunks to test concurrency control
                mock_extract.return_value = [{"chunk" + str(i): "data"} for i in range(10)]
                mock_alocalize_chunk.side_effect = mock_chunk_with_delay
                
                payload = {f"chunk{i}": "data" for i in range(10)}
                
                # Test with max_concurrent_requests=3
                await engine._alocalize_raw(
                    payload, 
                    localization_params,
                    max_concurrent_requests=3
                )
                
                # Should never exceed the semaphore limit
                assert max_concurrent <= 3
                assert mock_alocalize_chunk.call_count == 10
    
    @pytest.mark.asyncio
    async def test_alocalize_raw_maintains_chunk_order(self, engine, localization_params):
        """Test that results maintain original chunk order despite concurrent processing"""
        with patch.object(engine, '_extract_payload_chunks') as mock_extract:
            with patch.object(engine, '_alocalize_chunk') as mock_alocalize_chunk:
                # Create chunks that will be processed in different orders
                mock_extract.return_value = [
                    {"chunk1": "data1"},
                    {"chunk2": "data2"},
                    {"chunk3": "data3"},
                    {"chunk4": "data4"}
                ]
                
                # Mock responses with different delays to simulate out-of-order completion
                async def mock_chunk_response(*args, **kwargs):
                    chunk_data = args[2]["data"]
                    if "chunk1" in chunk_data:
                        await asyncio.sleep(0.03)  # Longest delay
                        return {"chunk1": "result1"}
                    elif "chunk2" in chunk_data:
                        await asyncio.sleep(0.01)  # Short delay
                        return {"chunk2": "result2"}
                    elif "chunk3" in chunk_data:
                        await asyncio.sleep(0.02)  # Medium delay
                        return {"chunk3": "result3"}
                    else:
                        # No delay - should complete first
                        return {"chunk4": "result4"}
                
                mock_alocalize_chunk.side_effect = mock_chunk_response
                
                payload = {"chunk1": "data1", "chunk2": "data2", "chunk3": "data3", "chunk4": "data4"}
                result = await engine._alocalize_raw(payload, localization_params)
                
                # Results should be combined in the correct order
                expected = {"chunk1": "result1", "chunk2": "result2", "chunk3": "result3", "chunk4": "result4"}
                assert result == expected
    
    @pytest.mark.asyncio
    async def test_alocalize_raw_error_propagation(self, engine, localization_params):
        """Test that errors in chunk processing are properly propagated"""
        with patch.object(engine, '_extract_payload_chunks') as mock_extract:
            with patch.object(engine, '_alocalize_chunk') as mock_alocalize_chunk:
                mock_extract.return_value = [{"chunk1": "data1"}]
                
                # Mock an error in chunk processing
                mock_alocalize_chunk.side_effect = LingoDevAPIError(
                    "Test API error", 500, "Server error"
                )
                
                payload = {"chunk1": "data1"}
                
                with pytest.raises(LingoDevAPIError) as exc_info:
                    await engine._alocalize_raw(payload, localization_params)
                
                error = exc_info.value
                assert "Test API error" in str(error)
                assert error.status_code == 500


class TestAsyncCoreIntegration:
    """Integration tests for async core methods"""
    
    @pytest.mark.asyncio
    async def test_async_client_lifecycle_management(self, engine):
        """Test that async client is properly managed during operations"""
        # Initially no async client
        assert engine._async_client is None
        
        # Mock the async client creation
        mock_async_client = AsyncMock()
        mock_async_client.is_closed = False
        mock_response = {"data": {"test": "result"}}
        mock_async_client.post.return_value = mock_response
        
        with patch('src.lingodotdev.engine.AsyncHTTPClient') as mock_client_class:
            mock_client_class.return_value = mock_async_client
            
            # First call should create the client
            result = await engine._alocalize_chunk(
                "en", "es", {"data": {"test": "data"}}, "workflow", False
            )
            
            assert result == {"test": "result"}
            assert engine._async_client is not None
            
            # Second call should reuse the same client
            await engine._alocalize_chunk(
                "en", "fr", {"data": {"test": "data"}}, "workflow", False
            )
            
            # Client should only be created once
            mock_client_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_client_recreation_after_close(self, engine):
        """Test that async client is recreated if it was closed"""
        mock_async_client = AsyncMock()
        mock_async_client.is_closed = True  # Simulate closed client
        mock_response = {"data": {"test": "result"}}
        mock_async_client.post.return_value = mock_response
        
        # Set a closed client
        engine._async_client = mock_async_client
        
        with patch('src.lingodotdev.engine.AsyncHTTPClient') as mock_client_class:
            new_mock_client = AsyncMock()
            new_mock_client.is_closed = False
            new_mock_client.post.return_value = mock_response
            mock_client_class.return_value = new_mock_client
            
            # Should create a new client since the old one is closed
            result = await engine._alocalize_chunk(
                "en", "es", {"data": {"test": "data"}}, "workflow", False
            )
            
            assert result == {"test": "result"}
            mock_client_class.assert_called_once()
            assert engine._async_client is new_mock_client


if __name__ == "__main__":
    pytest.main([__file__])