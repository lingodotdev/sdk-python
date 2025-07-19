# Migration Guide: Adopting Async Methods

## Overview

This guide helps you migrate from synchronous to asynchronous methods in the Lingo.dev Python SDK to take advantage of improved performance and concurrent processing capabilities.

## Why Migrate to Async?

### Performance Benefits
- **Concurrent Processing**: Handle multiple localization requests simultaneously
- **Better Resource Utilization**: Non-blocking I/O operations
- **Improved Throughput**: Significant performance gains for batch operations
- **Scalability**: Better handling of high-volume localization tasks

### When to Use Async
- Processing large volumes of content
- Batch localization to multiple languages
- Real-time applications requiring low latency
- Applications already using async/await patterns

## Migration Strategies

### 1. Gradual Migration (Recommended)

Start by migrating specific parts of your application while keeping existing synchronous code intact.

#### Before (Synchronous)
```python
from lingodotdev import LingoDotDevEngine

def localize_content():
    engine = LingoDotDevEngine({'api_key': 'your-api-key'})
    
    # Synchronous processing
    result1 = engine.localize_text("Hello", {'target_locale': 'es'})
    result2 = engine.localize_text("World", {'target_locale': 'es'})
    
    return [result1, result2]
```

#### After (Asynchronous)
```python
import asyncio
from lingodotdev import LingoDotDevEngine

async def localize_content():
    engine = LingoDotDevEngine({'api_key': 'your-api-key'})
    
    # Asynchronous concurrent processing
    tasks = [
        engine.alocalize_text("Hello", {'target_locale': 'es'}),
        engine.alocalize_text("World", {'target_locale': 'es'})
    ]
    
    results = await asyncio.gather(*tasks)
    await engine.close_async_client()
    
    return results
```

### 2. Mixed Approach

You can use both synchronous and asynchronous methods in the same application:

```python
import asyncio
from lingodotdev import LingoDotDevEngine

class LocalizationService:
    def __init__(self, api_key):
        self.engine = LingoDotDevEngine({'api_key': api_key})
    
    # Synchronous method for simple cases
    def localize_simple(self, text, target_locale):
        return self.engine.localize_text(text, {'target_locale': target_locale})
    
    # Asynchronous method for batch processing
    async def localize_batch(self, texts, target_locales):
        tasks = []
        for text in texts:
            for locale in target_locales:
                task = self.engine.alocalize_text(text, {'target_locale': locale})
                tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        await self.engine.close_async_client()
        
        return results
```

## Method Migration Map

### Text Localization
```python
# Synchronous
result = engine.localize_text(text, params, progress_callback)

# Asynchronous
result = await engine.alocalize_text(text, params, progress_callback)
```

### Object Localization
```python
# Synchronous
result = engine.localize_object(obj, params, progress_callback)

# Asynchronous
result = await engine.alocalize_object(obj, params, progress_callback)
```

### Batch Localization
```python
# Synchronous
results = engine.batch_localize_text(text, params)

# Asynchronous (with concurrent processing)
results = await engine.abatch_localize_text(text, params)
```

### Chat Localization
```python
# Synchronous
result = engine.localize_chat(chat, params, progress_callback)

# Asynchronous
result = await engine.alocalize_chat(chat, params, progress_callback)
```

### Locale Recognition
```python
# Synchronous
locale = engine.recognize_locale(text)

# Asynchronous
locale = await engine.arecognize_locale(text)
```

### User Information
```python
# Synchronous
user_info = engine.whoami()

# Asynchronous
user_info = await engine.awhoami()
```

## Common Migration Patterns

### 1. Batch Processing Migration

#### Before: Sequential Processing
```python
def process_multiple_texts(texts, target_locales):
    engine = LingoDotDevEngine({'api_key': 'your-api-key'})
    results = []
    
    for text in texts:
        for locale in target_locales:
            result = engine.localize_text(text, {'target_locale': locale})
            results.append(result)
    
    return results
```

#### After: Concurrent Processing
```python
async def process_multiple_texts(texts, target_locales):
    engine = LingoDotDevEngine({'api_key': 'your-api-key'})
    
    # Create all tasks upfront
    tasks = []
    for text in texts:
        task = engine.abatch_localize_text(text, {
            'source_locale': 'en',
            'target_locales': target_locales
        })
        tasks.append(task)
    
    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks)
    await engine.close_async_client()
    
    return results
```

### 2. Web Framework Integration

#### Flask with Async Support
```python
from flask import Flask
import asyncio
from lingodotdev import LingoDotDevEngine

app = Flask(__name__)

@app.route('/localize')
def localize_endpoint():
    # Run async function in sync context
    return asyncio.run(async_localize())

async def async_localize():
    engine = LingoDotDevEngine({'api_key': 'your-api-key'})
    result = await engine.alocalize_text("Hello", {'target_locale': 'es'})
    await engine.close_async_client()
    return result
```

#### FastAPI (Native Async)
```python
from fastapi import FastAPI
from lingodotdev import LingoDotDevEngine

app = FastAPI()
engine = LingoDotDevEngine({'api_key': 'your-api-key'})

@app.post("/localize")
async def localize_endpoint(text: str, target_locale: str):
    result = await engine.alocalize_text(text, {'target_locale': target_locale})
    return {"result": result}

@app.on_event("shutdown")
async def shutdown_event():
    await engine.close_async_client()
```

### 3. Class-Based Migration

#### Before: Synchronous Class
```python
class ContentLocalizer:
    def __init__(self, api_key):
        self.engine = LingoDotDevEngine({'api_key': api_key})
    
    def localize_content(self, content):
        results = {}
        for key, text in content.items():
            results[key] = self.engine.localize_text(text, {'target_locale': 'es'})
        return results
```

#### After: Asynchronous Class
```python
class ContentLocalizer:
    def __init__(self, api_key):
        self.engine = LingoDotDevEngine({'api_key': api_key})
    
    async def localize_content(self, content):
        tasks = []
        keys = []
        
        for key, text in content.items():
            task = self.engine.alocalize_text(text, {'target_locale': 'es'})
            tasks.append(task)
            keys.append(key)
        
        results = await asyncio.gather(*tasks)
        return dict(zip(keys, results))
    
    async def close(self):
        await self.engine.close_async_client()
```

## Best Practices

### 1. Resource Management
Always close the async client when done:

```python
async def main():
    engine = LingoDotDevEngine({'api_key': 'your-api-key'})
    
    try:
        # Your async operations
        result = await engine.alocalize_text("Hello", {'target_locale': 'es'})
    finally:
        # Always clean up
        await engine.close_async_client()
```

### 2. Error Handling
Use the same error handling patterns with async methods:

```python
from lingodotdev.exceptions import LingoDevError

async def safe_localize(text, target_locale):
    engine = LingoDotDevEngine({'api_key': 'your-api-key'})
    
    try:
        result = await engine.alocalize_text(text, {'target_locale': target_locale})
        return result
    except LingoDevError as e:
        print(f"Localization failed: {e}")
        return None
    finally:
        await engine.close_async_client()
```

### 3. Concurrency Control
Limit concurrent requests to avoid overwhelming the API:

```python
import asyncio

async def controlled_batch_processing(texts, target_locale, max_concurrent=5):
    engine = LingoDotDevEngine({'api_key': 'your-api-key'})
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_text(text):
        async with semaphore:
            return await engine.alocalize_text(text, {'target_locale': target_locale})
    
    tasks = [process_text(text) for text in texts]
    results = await asyncio.gather(*tasks)
    await engine.close_async_client()
    
    return results
```

### 4. Progress Tracking with Async
Progress callbacks work the same way with async methods:

```python
async def track_progress():
    engine = LingoDotDevEngine({'api_key': 'your-api-key'})
    
    def progress_callback(progress):
        print(f"Progress: {progress}%")
    
    result = await engine.alocalize_text(
        "Long text to localize",
        {'target_locale': 'es'},
        progress_callback=progress_callback
    )
    
    await engine.close_async_client()
    return result
```

## Performance Considerations

### Measuring Performance Improvements
```python
import time
import asyncio
from lingodotdev import LingoDotDevEngine

async def compare_performance():
    engine = LingoDotDevEngine({'api_key': 'your-api-key'})
    texts = ["Hello", "World", "How are you?", "Welcome", "Goodbye"]
    
    # Synchronous timing
    start_time = time.time()
    sync_results = []
    for text in texts:
        result = engine.localize_text(text, {'target_locale': 'es'})
        sync_results.append(result)
    sync_time = time.time() - start_time
    
    # Asynchronous timing
    start_time = time.time()
    tasks = [engine.alocalize_text(text, {'target_locale': 'es'}) for text in texts]
    async_results = await asyncio.gather(*tasks)
    async_time = time.time() - start_time
    
    await engine.close_async_client()
    
    print(f"Synchronous time: {sync_time:.2f}s")
    print(f"Asynchronous time: {async_time:.2f}s")
    print(f"Performance improvement: {sync_time/async_time:.2f}x")
```

## Troubleshooting

### Common Issues

1. **Forgetting to await**: Always use `await` with async methods
2. **Not closing async client**: Always call `close_async_client()`
3. **Mixing sync and async incorrectly**: Use `asyncio.run()` to bridge sync/async
4. **Event loop issues**: Be careful with nested event loops

### Migration Checklist

- [ ] Identify methods to migrate to async
- [ ] Add `async`/`await` keywords
- [ ] Replace sync methods with async counterparts
- [ ] Add proper error handling
- [ ] Implement resource cleanup (`close_async_client()`)
- [ ] Test performance improvements
- [ ] Update documentation and examples

## Conclusion

Migrating to async methods can provide significant performance improvements, especially for batch processing and high-volume applications. Start with a gradual migration approach, test thoroughly, and always ensure proper resource cleanup.

The async methods maintain the same API surface as their synchronous counterparts, making migration straightforward while providing substantial performance benefits."