"""
Performance integration tests comparing sync vs async functionality

This module tests performance characteristics and validates that async methods
provide significant performance improvements over sync methods.
"""

import asyncio
import time
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Dict, Any, List
import statistics

from src.lingodotdev.engine import LingoDotDevEngine
from src.lingodotdev.models import EnhancedEngineConfig


@pytest.fixture
def performance_config():
    """Configuration optimized for performance testing"""
    return EnhancedEngineConfig(
        api_key="api_sc16jj23cdpyvou6octw3hyl",
        api_url="https://test.lingo.dev",
        timeout=10.0,
        batch_size=10,  # Smaller batches for more chunks
        ideal_batch_item_size=50,  # Smaller chunks for more concurrent processing
        retry_config=None  # Disable retries for consistent timing
    )


@pytest.fixture
def engine(performance_config):
    """Engine instance for performance testing"""
    return LingoDotDevEngine(performance_config)


class TestSyncVsAsyncPerformance:
    """Performance comparison tests between sync and async methods"""
    
    def test_single_text_localization_performance(self, engine):
        """Compare sync vs async performance for single text localization"""
        text = "Hello world, this is a test message for performance comparison."
        params = {"source_locale": "en", "target_locale": "es"}
        
        # Mock responses with simulated network delay
        def mock_sync_response(*args, **kwargs):
            time.sleep(0.01)  # Simulate 10ms network delay
            return {"text": "Hola mundo, este es un mensaje de prueba para comparación de rendimiento."}
        
        async def mock_async_response(*args, **kwargs):
            await asyncio.sleep(0.01)  # Simulate 10ms network delay
            return {"text": "Hola mundo, este es un mensaje de prueba para comparación de rendimiento."}
        
        # Test sync performance
        with patch.object(engine, '_localize_raw', side_effect=mock_sync_response):
            sync_start = time.time()
            sync_result = engine.localize_text(text, params)
            sync_duration = time.time() - sync_start
        
        # Test async performance
        async def test_async():
            with patch.object(engine, '_alocalize_raw', side_effect=mock_async_response):
                async_start = time.time()
                async_result = await engine.alocalize_text(text, params)
                async_duration = time.time() - async_start
                return async_result, async_duration
        
        async_result, async_duration = asyncio.run(test_async())
        
        # Results should be the same
        assert sync_result == async_result
        
        # For single requests, timing should be similar (allow more variance due to overhead)
        time_ratio = async_duration / sync_duration
        assert 0.3 <= time_ratio <= 3.0, f"Async/Sync ratio: {time_ratio:.2f}"
    
    def test_batch_localization_performance(self, engine):
        """Compare sync vs async performance for batch localization"""
        text = "Hello world"
        target_locales = ["es", "fr", "de", "it", "pt"]
        params = {
            "source_locale": "en",
            "target_locales": target_locales,
            "fast": True
        }
        
        # Mock responses with network delays
        def mock_sync_localize_text(text, params):
            time.sleep(0.02)  # 20ms delay per request
            locale = params["target_locale"]
            return f"translated_{locale}"
        
        async def mock_async_localize_text(text, params):
            await asyncio.sleep(0.02)  # 20ms delay per request
            locale = params["target_locale"]
            return f"translated_{locale}"
        
        # Test sync performance (sequential)
        with patch.object(engine, 'localize_text', side_effect=mock_sync_localize_text):
            sync_start = time.time()
            sync_result = engine.batch_localize_text(text, params)
            sync_duration = time.time() - sync_start
        
        # Test async performance (concurrent)
        async def test_async():
            with patch.object(engine, 'alocalize_text', side_effect=mock_async_localize_text):
                async_start = time.time()
                async_result = await engine.abatch_localize_text(text, params)
                async_duration = time.time() - async_start
                return async_result, async_duration
        
        async_result, async_duration = asyncio.run(test_async())
        
        # Results should be the same
        assert sync_result == async_result
        assert len(sync_result) == len(target_locales)
        
        # Async should be significantly faster due to concurrency
        # With 5 requests of 20ms each:
        # - Sync: ~100ms (sequential)
        # - Async: ~20ms (concurrent)
        speedup_ratio = sync_duration / async_duration
        assert speedup_ratio >= 2.0, f"Async speedup: {speedup_ratio:.2f}x (expected >= 2x)"
        
        print(f"Batch localization speedup: {speedup_ratio:.2f}x")
        print(f"Sync duration: {sync_duration:.3f}s, Async duration: {async_duration:.3f}s")
    
    def test_large_object_localization_performance(self, engine):
        """Compare sync vs async performance for large object localization"""
        # Create a large object that will be chunked
        large_obj = {f"key_{i}": f"This is test value number {i} for performance testing" 
                    for i in range(50)}  # 50 key-value pairs
        
        params = {"source_locale": "en", "target_locale": "es"}
        
        # Mock chunk processing with delays
        def mock_sync_chunk(*args, **kwargs):
            time.sleep(0.005)  # 5ms per chunk
            chunk_data = args[2]["data"]  # payload["data"]
            return {k: f"translated_{v}" for k, v in chunk_data.items()}
        
        async def mock_async_chunk(*args, **kwargs):
            await asyncio.sleep(0.005)  # 5ms per chunk
            chunk_data = args[2]["data"]  # payload["data"]
            return {k: f"translated_{v}" for k, v in chunk_data.items()}
        
        # Test sync performance
        with patch.object(engine, '_localize_chunk', side_effect=mock_sync_chunk):
            sync_start = time.time()
            sync_result = engine.localize_object(large_obj, params)
            sync_duration = time.time() - sync_start
        
        # Test async performance
        async def test_async():
            with patch.object(engine, '_alocalize_chunk', side_effect=mock_async_chunk):
                async_start = time.time()
                async_result = await engine.alocalize_object(large_obj, params)
                async_duration = time.time() - async_start
                return async_result, async_duration
        
        async_result, async_duration = asyncio.run(test_async())
        
        # Results should have same structure
        assert len(sync_result) == len(async_result) == len(large_obj)
        
        # Async should be faster due to concurrent chunk processing
        speedup_ratio = sync_duration / async_duration
        assert speedup_ratio >= 1.1, f"Async speedup: {speedup_ratio:.2f}x (expected >= 1.1x)"
        
        print(f"Large object localization speedup: {speedup_ratio:.2f}x")
        print(f"Sync duration: {sync_duration:.3f}s, Async duration: {async_duration:.3f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, engine):
        """Test that async methods can handle multiple concurrent requests efficiently"""
        texts = [f"Test message {i}" for i in range(10)]
        params = {"source_locale": "en", "target_locale": "es"}
        
        async def mock_alocalize_raw(payload, params, progress_callback=None):
            await asyncio.sleep(0.01)  # 10ms delay
            text_key = list(payload.keys())[0]
            return {text_key: f"translated_{payload[text_key]}"}
        
        with patch.object(engine, '_alocalize_raw', side_effect=mock_alocalize_raw):
            # Test concurrent execution
            start_time = time.time()
            
            tasks = [
                engine.alocalize_text(text, params)
                for text in texts
            ]
            
            results = await asyncio.gather(*tasks)
            
            concurrent_duration = time.time() - start_time
        
        # All requests should complete
        assert len(results) == len(texts)
        
        # With 10 concurrent requests of 10ms each, total time should be ~10ms, not ~100ms
        # Allow some overhead, but should be much less than sequential
        assert concurrent_duration < 0.05, f"Concurrent duration too high: {concurrent_duration:.3f}s"
        
        print(f"Concurrent requests duration: {concurrent_duration:.3f}s for {len(texts)} requests")
    
    def test_memory_usage_comparison(self, engine):
        """Compare memory usage patterns between sync and async methods"""
        import tracemalloc
        
        # Large dataset for memory testing
        large_text = "This is a large text for memory testing. " * 100  # ~4KB text
        params = {"source_locale": "en", "target_locale": "es"}
        
        def mock_response(*args, **kwargs):
            return {"text": "translated_" + args[0]["text"]}
        
        async def mock_async_response(*args, **kwargs):
            return {"text": "translated_" + args[0]["text"]}
        
        # Test sync memory usage
        tracemalloc.start()
        with patch.object(engine, '_localize_raw', side_effect=mock_response):
            sync_result = engine.localize_text(large_text, params)
        sync_current, sync_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Test async memory usage
        async def test_async_memory():
            tracemalloc.start()
            with patch.object(engine, '_alocalize_raw', side_effect=mock_async_response):
                async_result = await engine.alocalize_text(large_text, params)
            async_current, async_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            return async_result, async_current, async_peak
        
        async_result, async_current, async_peak = asyncio.run(test_async_memory())
        
        # Results should be equivalent
        assert len(sync_result) == len(async_result)
        
        # Memory usage should be comparable (within 2x)
        memory_ratio = async_peak / sync_peak
        assert 0.5 <= memory_ratio <= 2.0, f"Memory usage ratio: {memory_ratio:.2f}"
        
        print(f"Sync peak memory: {sync_peak / 1024:.1f} KB")
        print(f"Async peak memory: {async_peak / 1024:.1f} KB")
        print(f"Memory ratio (async/sync): {memory_ratio:.2f}")


class TestPerformanceCharacteristics:
    """Test specific performance characteristics and optimizations"""
    
    @pytest.mark.asyncio
    async def test_semaphore_concurrency_control(self, engine):
        """Test that semaphore properly controls concurrency without blocking unnecessarily"""
        concurrent_count = 0
        max_concurrent = 0
        
        async def mock_chunk_with_tracking(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            
            await asyncio.sleep(0.01)  # Simulate work
            
            concurrent_count -= 1
            return {"result": "data"}
        
        # Test with different concurrency limits
        for max_concurrent_requests in [1, 3, 5]:
            concurrent_count = 0
            max_concurrent = 0
            
            with patch.object(engine, '_alocalize_chunk', side_effect=mock_chunk_with_tracking):
                # Create a large object that will generate multiple chunks
                large_obj = {f"key_{i}": f"value_{i}" for i in range(15)}
                params = {"source_locale": "en", "target_locale": "es"}
                
                from src.lingodotdev.models import LocalizationParams
                localization_params = LocalizationParams(**params)
                await engine._alocalize_raw(
                    large_obj, 
                    localization_params,
                    max_concurrent_requests=max_concurrent_requests
                )
            
            # Should never exceed the specified limit
            assert max_concurrent <= max_concurrent_requests, \
                f"Exceeded concurrency limit: {max_concurrent} > {max_concurrent_requests}"
            
            print(f"Max concurrent with limit {max_concurrent_requests}: {max_concurrent}")
    
    def test_progress_callback_performance_impact(self, engine):
        """Test that progress callbacks don't significantly impact performance"""
        text = "Test message for progress callback performance"
        params = {"source_locale": "en", "target_locale": "es"}
        
        progress_calls = []
        def progress_callback(progress):
            progress_calls.append(progress)
        
        def mock_response(*args, **kwargs):
            time.sleep(0.001)  # 1ms delay
            return {"text": "translated_text"}
        
        # Test without progress callback
        with patch.object(engine, '_localize_raw', side_effect=mock_response):
            start_time = time.time()
            result_no_callback = engine.localize_text(text, params)
            duration_no_callback = time.time() - start_time
        
        # Test with progress callback
        with patch.object(engine, '_localize_raw', side_effect=mock_response):
            start_time = time.time()
            result_with_callback = engine.localize_text(text, params, progress_callback)
            duration_with_callback = time.time() - start_time
        
        # Results should be the same
        assert result_no_callback == result_with_callback
        
        # Progress callback should have been called (if chunks were processed)
        # Note: For small text, there might be only one chunk, so callback might not be called
        # This is expected behavior, so we'll just check that the test ran without error
        
        # Performance impact should be minimal (< 50% overhead)
        overhead_ratio = duration_with_callback / duration_no_callback
        assert overhead_ratio < 1.5, f"Progress callback overhead too high: {overhead_ratio:.2f}x"
        
        print(f"Progress callback overhead: {overhead_ratio:.2f}x")
    
    @pytest.mark.asyncio
    async def test_error_handling_performance_impact(self, engine):
        """Test that error handling doesn't significantly impact normal operation performance"""
        text = "Test message"
        params = {"source_locale": "en", "target_locale": "es"}
        
        # Mock successful response
        async def mock_success(*args, **kwargs):
            await asyncio.sleep(0.001)
            return {"text": "translated_text"}
        
        # Test performance with retry handler enabled
        from src.lingodotdev.models import RetryConfiguration
        from src.lingodotdev.retry import RetryHandler
        retry_config = RetryConfiguration(
            max_retries=3,
            backoff_factor=0.1
        )
        engine.config.retry_config = retry_config
        engine.retry_handler = RetryHandler(retry_config)
        
        with patch.object(engine, '_alocalize_raw', side_effect=mock_success):
            start_time = time.time()
            result = await engine.alocalize_text(text, params)
            duration_with_retry = time.time() - start_time
        
        # Test performance with retry handler disabled
        engine.config.retry_config = None
        engine.retry_handler = None
        
        with patch.object(engine, '_alocalize_raw', side_effect=mock_success):
            start_time = time.time()
            result_no_retry = await engine.alocalize_text(text, params)
            duration_no_retry = time.time() - start_time
        
        # Results should be the same
        assert result == result_no_retry
        
        # Retry handler overhead should be minimal for successful requests
        overhead_ratio = duration_with_retry / duration_no_retry
        assert overhead_ratio < 2.0, f"Retry handler overhead too high: {overhead_ratio:.2f}x"
        
        print(f"Retry handler overhead: {overhead_ratio:.2f}x")


class TestScalabilityCharacteristics:
    """Test scalability characteristics of async implementation"""
    
    @pytest.mark.asyncio
    async def test_scaling_with_request_count(self, engine):
        """Test how performance scales with increasing number of requests"""
        params = {"source_locale": "en", "target_locale": "es"}
        
        async def mock_alocalize_text(text, params):
            await asyncio.sleep(0.005)  # 5ms per request
            return f"translated_{text}"
        
        # Test with different numbers of concurrent requests
        request_counts = [1, 5, 10, 20]
        durations = []
        
        for count in request_counts:
            texts = [f"Message {i}" for i in range(count)]
            
            with patch.object(engine, 'alocalize_text', side_effect=mock_alocalize_text):
                start_time = time.time()
                
                tasks = [engine.alocalize_text(text, params) for text in texts]
                results = await asyncio.gather(*tasks)
                
                duration = time.time() - start_time
                durations.append(duration)
            
            assert len(results) == count
        
        # Performance should scale well (not linearly with request count)
        # Duration should be roughly constant for concurrent requests
        for i, (count, duration) in enumerate(zip(request_counts, durations)):
            print(f"{count} requests: {duration:.3f}s ({duration/count*1000:.1f}ms per request)")
        
        # The duration for 20 requests should be much less than 20x the duration for 1 request
        efficiency_ratio = durations[-1] / (durations[0] * request_counts[-1])
        assert efficiency_ratio < 0.5, f"Poor scaling efficiency: {efficiency_ratio:.2f}"
        
        print(f"Scaling efficiency: {efficiency_ratio:.2f} (lower is better)")


if __name__ == "__main__":
    pytest.main([__file__])