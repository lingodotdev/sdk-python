"""
Backward compatibility validation tests

This module ensures that all enhancements maintain full backward compatibility
with existing code and that no breaking changes have been introduced.
"""

import inspect
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List, Optional, Callable

from src.lingodotdev import LingoDotDevEngine
from src.lingodotdev.engine import LingoDotDevEngine as DirectEngine


class TestBackwardCompatibilityAPI:
    """Test that all existing API methods remain unchanged"""
    
    def test_engine_initialization_backward_compatibility(self):
        """Test that engine can still be initialized with old-style dict config"""
        # Old-style configuration (should still work)
        old_config = {
            "api_key": "api_sc16jj23cdpyvou6octw3hyl",
            "api_url": "https://api.test.com",
            "batch_size": 50,
            "ideal_batch_item_size": 500
        }
        
        # Should work without any issues
        engine = LingoDotDevEngine(old_config)
        
        assert engine.config.api_key == "api_sc16jj23cdpyvou6octw3hyl"
        assert engine.config.api_url == "https://api.test.com"
        assert engine.config.batch_size == 50
        assert engine.config.ideal_batch_item_size == 500
        
        # Should have default values for new fields
        assert engine.config.timeout == 30.0  # Default
        assert engine.config.retry_config is not None  # Default retry config
    
    def test_method_signatures_unchanged(self):
        """Test that all existing method signatures remain exactly the same"""
        engine = LingoDotDevEngine({"api_key": "api_sc16jj23cdpyvou6octw3hyl"})
        
        # Test localize_text signature
        localize_text_sig = inspect.signature(engine.localize_text)
        expected_params = ['text', 'params', 'progress_callback']
        actual_params = list(localize_text_sig.parameters.keys())
        # Remove 'self' parameter if present
        if actual_params and actual_params[0] == 'self':
            actual_params = actual_params[1:]
        assert actual_params == expected_params, f"Expected {expected_params}, got {actual_params}"
        
        # Test localize_object signature
        localize_object_sig = inspect.signature(engine.localize_object)
        expected_params = ['obj', 'params', 'progress_callback']
        actual_params = list(localize_object_sig.parameters.keys())
        if actual_params and actual_params[0] == 'self':
            actual_params = actual_params[1:]
        assert actual_params == expected_params
        
        # Test batch_localize_text signature
        batch_localize_sig = inspect.signature(engine.batch_localize_text)
        expected_params = ['text', 'params']
        actual_params = list(batch_localize_sig.parameters.keys())
        if actual_params and actual_params[0] == 'self':
            actual_params = actual_params[1:]
        assert actual_params == expected_params
        
        # Test localize_chat signature
        localize_chat_sig = inspect.signature(engine.localize_chat)
        expected_params = ['chat', 'params', 'progress_callback']
        actual_params = list(localize_chat_sig.parameters.keys())
        if actual_params and actual_params[0] == 'self':
            actual_params = actual_params[1:]
        assert actual_params == expected_params
        
        # Test recognize_locale signature
        recognize_locale_sig = inspect.signature(engine.recognize_locale)
        expected_params = ['text']
        actual_params = list(recognize_locale_sig.parameters.keys())
        if actual_params and actual_params[0] == 'self':
            actual_params = actual_params[1:]
        assert actual_params == expected_params
        
        # Test whoami signature
        whoami_sig = inspect.signature(engine.whoami)
        expected_params = []
        actual_params = list(whoami_sig.parameters.keys())
        if actual_params and actual_params[0] == 'self':
            actual_params = actual_params[1:]
        assert actual_params == expected_params
    
    def test_import_compatibility(self):
        """Test that all existing imports still work"""
        # Test main engine import
        from src.lingodotdev import LingoDotDevEngine
        assert LingoDotDevEngine is not None
        
        # Test direct engine import
        from src.lingodotdev.engine import LingoDotDevEngine as DirectEngine
        assert DirectEngine is not None
        
        # Should be the same class
        assert LingoDotDevEngine is DirectEngine
        
        # Test that we can still create instances
        config = {"api_key": "api_sc16jj23cdpyvou6octw3hyl"}
        engine1 = LingoDotDevEngine(config)
        engine2 = DirectEngine(config)
        
        assert type(engine1) == type(engine2)
    
    def test_parameter_format_compatibility(self):
        """Test that old parameter formats still work"""
        engine = LingoDotDevEngine({"api_key": "api_sc16jj23cdpyvou6octw3hyl"})
        
        # Mock the internal methods to avoid actual API calls
        with patch.object(engine, '_localize_raw') as mock_localize:
            mock_localize.return_value = {"text": "hola mundo"}
            
            # Old-style parameters (plain dict) should still work
            old_params = {
                "source_locale": "en",
                "target_locale": "es",
                "fast": True
            }
            
            result = engine.localize_text("hello world", old_params)
            assert result == "hola mundo"
            
            # Verify the call was made
            mock_localize.assert_called_once()
            
            # Check that LocalizationParams was created correctly
            call_args = mock_localize.call_args[0]
            localization_params = call_args[1]  # Second argument
            assert localization_params.source_locale == "en"
            assert localization_params.target_locale == "es"
            assert localization_params.fast is True
    
    def test_return_value_compatibility(self):
        """Test that return values maintain the same format"""
        engine = LingoDotDevEngine({"api_key": "api_sc16jj23cdpyvou6octw3hyl"})
        
        # Test localize_text return type
        with patch.object(engine, '_localize_raw') as mock_localize:
            mock_localize.return_value = {"text": "hola"}
            result = engine.localize_text("hello", {"target_locale": "es"})
            assert isinstance(result, str)
            assert result == "hola"
        
        # Test localize_object return type
        with patch.object(engine, '_localize_raw') as mock_localize:
            mock_localize.return_value = {"key": "valor"}
            result = engine.localize_object({"key": "value"}, {"target_locale": "es"})
            assert isinstance(result, dict)
            assert result == {"key": "valor"}
        
        # Test batch_localize_text return type
        with patch.object(engine, 'localize_text') as mock_localize:
            mock_localize.side_effect = ["hola", "bonjour"]
            result = engine.batch_localize_text("hello", {
                "target_locales": ["es", "fr"]
            })
            assert isinstance(result, list)
            assert result == ["hola", "bonjour"]
        
        # Test localize_chat return type
        with patch.object(engine, '_localize_raw') as mock_localize:
            mock_localize.return_value = {
                "chat": [{"name": "Alice", "text": "Hola"}]
            }
            result = engine.localize_chat(
                [{"name": "Alice", "text": "Hello"}], 
                {"target_locale": "es"}
            )
            assert isinstance(result, list)
            assert result == [{"name": "Alice", "text": "Hola"}]
        
        # Test recognize_locale return type
        with patch.object(engine, 'session') as mock_session:
            mock_response = MagicMock()
            mock_response.ok = True
            mock_response.json.return_value = {"locale": "en"}
            mock_session.post.return_value = mock_response
            
            result = engine.recognize_locale("Hello world")
            assert isinstance(result, str)
            assert result == "en"
        
        # Test whoami return type
        with patch.object(engine, 'session') as mock_session:
            mock_response = MagicMock()
            mock_response.ok = True
            mock_response.json.return_value = {"email": "test@example.com", "id": "123"}
            mock_session.post.return_value = mock_response
            
            result = engine.whoami()
            assert isinstance(result, dict) or result is None
            assert result == {"email": "test@example.com", "id": "123"}


class TestExistingCodeCompatibility:
    """Test that existing code patterns still work"""
    
    def test_simple_usage_pattern(self):
        """Test the most common usage pattern still works"""
        # This is how most users would use the SDK
        config = {
            "api_key": "api_sc16jj23cdpyvou6octw3hyl"
        }
        
        engine = LingoDotDevEngine(config)
        
        with patch.object(engine, '_localize_raw') as mock_localize:
            mock_localize.return_value = {"text": "Hola mundo"}
            
            # Simple text localization
            result = engine.localize_text(
                "Hello world",
                {"target_locale": "es"}
            )
            
            assert result == "Hola mundo"
    
    def test_complex_usage_pattern(self):
        """Test more complex usage patterns still work"""
        config = {
            "api_key": "api_sc16jj23cdpyvou6octw3hyl",
            "api_url": "https://custom.api.com",
            "batch_size": 100
        }
        
        engine = LingoDotDevEngine(config)
        
        # Test object localization with progress callback
        progress_calls = []
        def progress_callback(progress, source_chunk, processed_chunk):
            progress_calls.append(progress)
        
        with patch.object(engine, '_localize_raw') as mock_localize:
            mock_localize.return_value = {
                "title": "Título",
                "description": "Descripción"
            }
            
            obj = {
                "title": "Title",
                "description": "Description"
            }
            
            result = engine.localize_object(
                obj,
                {
                    "source_locale": "en",
                    "target_locale": "es",
                    "fast": True
                },
                progress_callback
            )
            
            assert result == {"title": "Título", "description": "Descripción"}
    
    def test_batch_processing_pattern(self):
        """Test batch processing patterns still work"""
        engine = LingoDotDevEngine({"api_key": "api_sc16jj23cdpyvou6octw3hyl"})
        
        with patch.object(engine, 'localize_text') as mock_localize:
            mock_localize.side_effect = ["Hola", "Bonjour", "Hallo"]
            
            # Batch localization to multiple languages
            result = engine.batch_localize_text(
                "Hello",
                {
                    "source_locale": "en",
                    "target_locales": ["es", "fr", "de"],
                    "fast": True
                }
            )
            
            assert result == ["Hola", "Bonjour", "Hallo"]
            assert mock_localize.call_count == 3
    
    def test_chat_localization_pattern(self):
        """Test chat localization patterns still work"""
        engine = LingoDotDevEngine({"api_key": "api_sc16jj23cdpyvou6octw3hyl"})
        
        chat = [
            {"name": "Alice", "text": "Hello"},
            {"name": "Bob", "text": "How are you?"}
        ]
        
        with patch.object(engine, '_localize_raw') as mock_localize:
            mock_localize.return_value = {
                "chat": [
                    {"name": "Alice", "text": "Hola"},
                    {"name": "Bob", "text": "¿Cómo estás?"}
                ]
            }
            
            result = engine.localize_chat(
                chat,
                {"target_locale": "es"}
            )
            
            expected = [
                {"name": "Alice", "text": "Hola"},
                {"name": "Bob", "text": "¿Cómo estás?"}
            ]
            assert result == expected
    
    def test_error_handling_compatibility(self):
        """Test that error handling behavior remains the same"""
        engine = LingoDotDevEngine({"api_key": "api_sc16jj23cdpyvou6octw3hyl"})
        
        # Test ValueError for missing target_locales
        with pytest.raises(ValueError) as exc_info:
            engine.batch_localize_text("Hello", {"source_locale": "en"})
        assert "target_locales is required" in str(exc_info.value)
        
        # Test ValueError for invalid chat format
        with pytest.raises(ValueError) as exc_info:
            engine.localize_chat(
                [{"name": "Alice"}],  # Missing 'text'
                {"target_locale": "es"}
            )
        assert "Each chat message must have 'name' and 'text' properties" in str(exc_info.value)
        
        # Test ValueError for empty text in recognize_locale
        with pytest.raises(ValueError) as exc_info:
            engine.recognize_locale("")
        assert "Text cannot be empty" in str(exc_info.value)


class TestConfigurationCompatibility:
    """Test that all configuration options remain backward compatible"""
    
    def test_minimal_configuration(self):
        """Test that minimal configuration still works"""
        # Just API key (most minimal config)
        config = {"api_key": "api_sc16jj23cdpyvou6octw3hyl"}
        engine = LingoDotDevEngine(config)
        
        # Should use default values
        assert engine.config.api_url == "https://engine.lingo.dev"
        assert engine.config.batch_size == 25
        assert engine.config.ideal_batch_item_size == 250
        assert engine.config.timeout == 30.0
    
    def test_full_old_configuration(self):
        """Test that full old-style configuration works"""
        config = {
            "api_key": "api_sc16jj23cdpyvou6octw3hyl",
            "api_url": "https://custom.api.com",
            "batch_size": 50,
            "ideal_batch_item_size": 500
        }
        
        engine = LingoDotDevEngine(config)
        
        assert engine.config.api_key == "api_sc16jj23cdpyvou6octw3hyl"
        assert engine.config.api_url == "https://custom.api.com"
        assert engine.config.batch_size == 50
        assert engine.config.ideal_batch_item_size == 500
        assert engine.config.timeout == 30.0  # Default for new field
    
    def test_mixed_configuration(self):
        """Test mixing old and new configuration options"""
        config = {
            "api_key": "api_sc16jj23cdpyvou6octw3hyl",
            "api_url": "https://custom.api.com",
            "batch_size": 50,
            "timeout": 60.0,  # New field
            "retry_config": {  # New field
                "max_retries": 5,
                "backoff_factor": 1.0
            }
        }
        
        engine = LingoDotDevEngine(config)
        
        # Old fields should work
        assert engine.config.api_key == "api_sc16jj23cdpyvou6octw3hyl"
        assert engine.config.api_url == "https://custom.api.com"
        assert engine.config.batch_size == 50
        
        # New fields should work
        assert engine.config.timeout == 60.0
        assert engine.config.retry_config.max_retries == 5
        assert engine.config.retry_config.backoff_factor == 1.0
    
    def test_configuration_validation_backward_compatibility(self):
        """Test that configuration validation doesn't break existing valid configs"""
        # These should all work (they would have worked before)
        valid_configs = [
            {"api_key": "api_sc16jj23cdpyvou6octw3hyl"},
            {"api_key": "api_sc16jj23cdpyvou6octw3hyl", "api_url": "https://api.test.com"},
            {"api_key": "api_sc16jj23cdpyvou6octw3hyl", "batch_size": 10},
            {"api_key": "api_sc16jj23cdpyvou6octw3hyl", "ideal_batch_item_size": 100},
        ]
        
        for config in valid_configs:
            engine = LingoDotDevEngine(config)
            assert engine.config.api_key == "api_sc16jj23cdpyvou6octw3hyl"


class TestProgressCallbackCompatibility:
    """Test that progress callback behavior remains the same"""
    
    def test_simple_progress_callback(self):
        """Test simple progress callback (for text localization)"""
        engine = LingoDotDevEngine({"api_key": "api_sc16jj23cdpyvou6octw3hyl"})
        
        progress_calls = []
        def progress_callback(progress):
            progress_calls.append(progress)
        
        with patch.object(engine, '_localize_raw') as mock_localize:
            mock_localize.return_value = {"text": "hola"}
            
            result = engine.localize_text(
                "hello",
                {"target_locale": "es"},
                progress_callback
            )
            
            assert result == "hola"
            # Progress callback should have been wrapped and passed through
            mock_localize.assert_called_once()
    
    def test_detailed_progress_callback(self):
        """Test detailed progress callback (for object localization)"""
        engine = LingoDotDevEngine({"api_key": "api_sc16jj23cdpyvou6octw3hyl"})
        
        progress_calls = []
        def progress_callback(progress, source_chunk, processed_chunk):
            progress_calls.append({
                "progress": progress,
                "source_chunk": source_chunk,
                "processed_chunk": processed_chunk
            })
        
        with patch.object(engine, '_localize_raw') as mock_localize:
            mock_localize.return_value = {"key": "valor"}
            
            result = engine.localize_object(
                {"key": "value"},
                {"target_locale": "es"},
                progress_callback
            )
            
            assert result == {"key": "valor"}
            # Progress callback should have been passed through directly
            mock_localize.assert_called_once()


class TestExistingTestCompatibility:
    """Run existing test patterns to ensure they still work"""
    
    def test_existing_test_pattern_1(self):
        """Test a typical existing test pattern"""
        # This simulates how existing tests might look
        config = {"api_key": "api_sc16jj23cdpyvou6octw3hyl"}
        engine = LingoDotDevEngine(config)
        
        # Mock the session to simulate API response
        with patch.object(engine, 'session') as mock_session:
            mock_response = MagicMock()
            mock_response.ok = True
            mock_response.json.return_value = {"locale": "es"}
            mock_session.post.return_value = mock_response
            
            result = engine.recognize_locale("Hola mundo")
            assert result == "es"
            
            # Verify the API call was made correctly
            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            assert "/recognize" in call_args[0][0]  # URL contains /recognize
            assert call_args[1]["json"]["text"] == "Hola mundo"
    
    def test_existing_test_pattern_2(self):
        """Test another typical existing test pattern"""
        config = {
            "api_key": "api_sc16jj23cdpyvou6octw3hyl",
            "api_url": "https://test.api.com"
        }
        engine = LingoDotDevEngine(config)
        
        # Test with mocked _localize_raw (common pattern)
        with patch.object(engine, '_localize_raw') as mock_localize:
            mock_localize.return_value = {"greeting": "Hola", "farewell": "Adiós"}
            
            obj = {"greeting": "Hello", "farewell": "Goodbye"}
            result = engine.localize_object(obj, {
                "source_locale": "en",
                "target_locale": "es"
            })
            
            assert result == {"greeting": "Hola", "farewell": "Adiós"}
            
            # Verify the call
            mock_localize.assert_called_once()
            args = mock_localize.call_args[0]
            assert args[0] == obj  # First arg should be the object
            assert args[1].target_locale == "es"  # Second arg should be LocalizationParams
    
    def test_existing_error_test_pattern(self):
        """Test existing error handling test patterns"""
        config = {"api_key": "api_sc16jj23cdpyvou6octw3hyl"}
        engine = LingoDotDevEngine(config)
        
        # Test that existing error conditions still raise the same errors
        with pytest.raises(ValueError):
            engine.batch_localize_text("Hello", {})  # Missing target_locales
        
        with pytest.raises(ValueError):
            engine.recognize_locale("")  # Empty text
        
        with pytest.raises(ValueError):
            engine.localize_chat([{"name": "Alice"}], {"target_locale": "es"})  # Invalid chat


if __name__ == "__main__":
    pytest.main([__file__])