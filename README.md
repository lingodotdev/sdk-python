# Lingo.dev Python SDK

A powerful async-first localization engine that supports various content types including plain text, objects, chat sequences, and HTML documents.

## ✨ Key Features

- 🚀 **Async-first design** for high-performance concurrent translations
- 🔀 **Concurrent processing** for dramatically faster bulk translations
- 🎯 **Multiple content types**: text, objects, chat messages, and more
- 🌐 **Auto-detection** of source languages
- 🔧 **Flexible configuration** with progress callbacks
- 📦 **Context manager** support for proper resource management

## 🚀 Performance Benefits

The async implementation provides significant performance improvements:
- **Concurrent chunk processing** for large payloads
- **Batch operations** for multiple translations
- **Parallel API requests** instead of sequential ones
- **Better resource management** with httpx

## 📦 Installation

```bash
pip install lingodotdev
```

## 🎯 Quick Start

### Simple Translation

```python
import asyncio
from lingodotdev import LingoDotDevEngine

async def main():
    # Quick one-off translation (handles context management automatically)
    result = await LingoDotDevEngine.quick_translate(
        "Hello, world!",
        api_key="your-api-key",
        engine_id="your-engine-id",
        target_locale="es"
    )
    print(result)  # "¡Hola, mundo!"

asyncio.run(main())
```

### Context Manager (Recommended for Multiple Operations)

```python
import asyncio
from lingodotdev import LingoDotDevEngine

async def main():
    config = {
        "api_key": "your-api-key",
        "engine_id": "your-engine-id",  # Optional
    }

    async with LingoDotDevEngine(config) as engine:
        # Translate text
        text_result = await engine.localize_text(
            "Hello, world!",
            {"target_locale": "es"}
        )
        
        # Translate object with concurrent processing
        obj_result = await engine.localize_object(
            {
                "greeting": "Hello",
                "farewell": "Goodbye",
                "question": "How are you?"
            },
            {"target_locale": "es"},
            concurrent=True  # Process chunks concurrently for speed
        )

asyncio.run(main())
```

## 🔥 Advanced Usage

### Batch Processing (Multiple Target Languages)

```python
async def batch_example():
    # Translate to multiple languages at once
    results = await LingoDotDevEngine.quick_batch_translate(
        "Welcome to our application",
        api_key="your-api-key",
        engine_id="your-engine-id",
        target_locales=["es", "fr", "de", "it"]
    )
    # Results: ["Bienvenido...", "Bienvenue...", "Willkommen...", "Benvenuto..."]
```

### Large Object Processing with Progress

```python
async def progress_example():
    def progress_callback(progress, source_chunk, processed_chunk):
        print(f"Progress: {progress}% - Processed {len(processed_chunk)} items")

    large_content = {f"item_{i}": f"Content {i}" for i in range(1000)}
    
    async with LingoDotDevEngine({"api_key": "your-api-key", "engine_id": "your-engine-id"}) as engine:
        result = await engine.localize_object(
            large_content,
            {"target_locale": "es"},
            progress_callback=progress_callback,
            concurrent=True  # Much faster for large objects
        )
```

### Chat Translation

```python
async def chat_example():
    chat_messages = [
        {"name": "Alice", "text": "Hello everyone!"},
        {"name": "Bob", "text": "How is everyone doing?"},
        {"name": "Charlie", "text": "Great to see you all!"}
    ]
    
    async with LingoDotDevEngine({"api_key": "your-api-key", "engine_id": "your-engine-id"}) as engine:
        translated_chat = await engine.localize_chat(
            chat_messages,
            {"source_locale": "en", "target_locale": "es"}
        )
        # Names preserved, text translated
```

### Multiple Objects Concurrently

```python
async def concurrent_objects_example():
    objects = [
        {"title": "Welcome", "description": "Please sign in"},
        {"error": "Invalid input", "help": "Check your email"},
        {"success": "Account created", "next": "Continue to dashboard"}
    ]
    
    async with LingoDotDevEngine({"api_key": "your-api-key", "engine_id": "your-engine-id"}) as engine:
        results = await engine.batch_localize_objects(
            objects,
            {"target_locale": "fr"}
        )
        # All objects translated concurrently
```

### Language Detection

```python
async def detection_example():
    async with LingoDotDevEngine({"api_key": "your-api-key", "engine_id": "your-engine-id"}) as engine:
        detected = await engine.recognize_locale("Bonjour le monde")
        print(detected)  # "fr"
```

## ⚙️ Configuration Options

```python
config = {
    "api_key": "your-api-key",              # Required: Your API key
    "engine_id": "your-engine-id",          # Optional: Your engine ID
    "api_url": "https://api.lingo.dev",     # Optional: API endpoint
    "batch_size": 25,                       # Optional: Items per batch (1-250)
    "ideal_batch_item_size": 250            # Optional: Target words per batch (1-2500)
}
```

## 🎛️ Method Parameters

### Translation Parameters
- **source_locale**: Source language code (auto-detected if None)
- **target_locale**: Target language code (required)
- **reference**: Reference translations for context
- **concurrent**: Process chunks concurrently (faster, but no progress callbacks)

### Performance Options
- **concurrent=True**: Enables parallel processing of chunks
- **progress_callback**: Function to track progress (disabled with concurrent=True)

## 🔧 Error Handling

```python
async def error_handling_example():
    try:
        async with LingoDotDevEngine({"api_key": "invalid-key", "engine_id": "your-engine-id"}) as engine:
            result = await engine.localize_text("Hello", {"target_locale": "es"})
    except ValueError as e:
        print(f"Invalid request: {e}")
    except RuntimeError as e:
        print(f"API error: {e}")
```

## 🚀 Performance Tips

1. **Use `concurrent=True`** for large objects or multiple chunks
2. **Use `batch_localize_objects()`** for multiple objects
3. **Use context managers** for multiple operations
4. **Use `quick_translate()`** for one-off translations
5. **Adjust `batch_size`** based on your content structure

## 🤝 Migration from Sync Version

The async version is a drop-in replacement with these changes:
- Add `async`/`await` to all method calls
- Use `async with` for context managers
- All methods now return awaitable coroutines

## 📚 API Reference

### Core Methods
- `localize_text(text, params)` - Translate text strings
- `localize_object(obj, params)` - Translate dictionary objects
- `localize_chat(chat, params)` - Translate chat messages
- `batch_localize_text(text, params)` - Translate to multiple languages
- `batch_localize_objects(objects, params)` - Translate multiple objects
- `recognize_locale(text)` - Detect language
- `whoami()` - Get API account info

### Convenience Methods
- `quick_translate(content, api_key, target_locale, ...)` - One-off translation
- `quick_batch_translate(content, api_key, target_locales, ...)` - Batch translation

## 📄 License

Apache-2.0 License

## 🤖 Support

- 📚 [Documentation](https://lingo.dev/docs)
- 🐛 [Issues](https://github.com/lingodotdev/sdk-python/issues)
- 💬 [Community](https://discord.gg/rJ8zGYJQj5)
