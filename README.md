# Lingo.dev Python SDK

> 💬 **[Join our Discord community](https://lingo.dev/go/discord)** for support, discussions, and updates!

[![PyPI version](https://badge.fury.io/py/lingodotdev.svg)](https://badge.fury.io/py/lingodotdev)
[![Python support](https://img.shields.io/pypi/pyversions/lingodotdev)](https://pypi.org/project/lingodotdev/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Tests](https://github.com/lingodotdev/sdk-python/workflows/Pull%20Request/badge.svg)](https://github.com/lingodotdev/sdk-python/actions)
[![Coverage](https://codecov.io/gh/lingodotdev/sdk-python/branch/main/graph/badge.svg)](https://codecov.io/gh/lingodotdev/sdk-python)

A powerful Python SDK for the Lingo.dev localization platform. This SDK provides easy-to-use methods for localizing various content types including plain text, objects, and chat sequences. 

## Features

- 🌍 **Multiple Content Types**: Localize text, objects, and chat sequences
- ⚡ **Async/Await Support**: High-performance async methods for concurrent processing
- 🚀 **Batch Processing**: Efficient handling of large content with automatic chunking
- 🔄 **Progress Tracking**: Optional progress callbacks for long-running operations
- 🎯 **Language Detection**: Automatic language recognition
- 📊 **Fast Mode**: Optional fast processing for larger batches
- 🔁 **Smart Retry Logic**: Configurable retry with exponential backoff and jitter
- 🛡️ **Enhanced Error Handling**: Detailed error information with intelligent suggestions
- 🔒 **Type Safety**: Full type hints and Pydantic validation
- 🧪 **Well Tested**: Comprehensive test suite with high coverage
- 🔧 **Easy Configuration**: Simple setup with minimal configuration required
- 🔄 **Backward Compatible**: All existing code works without changes

## Installation

### Basic Installation

```bash
pip install lingodotdev
```

### Installation with Optional Dependencies

```bash
# For development (includes testing, linting, type checking)
pip install lingodotdev[dev]

# For testing only
pip install lingodotdev[test]

# Explicit async support (already included in basic installation)
pip install lingodotdev[async]
```

See [Dependencies Documentation](docs/dependencies.md) for detailed information about requirements and optional dependencies.

## Quick Start

```python
from lingodotdev import LingoDotDevEngine

# Initialize the engine
engine = LingoDotDevEngine({
    'api_key': 'your-api-key-here'
})

# Localize a simple text
result = engine.localize_text(
    "Hello, world!",
    {
        'source_locale': 'en',
        'target_locale': 'es'
    }
)
print(result)  # "¡Hola, mundo!"

# Localize an object
data = {
    'greeting': 'Hello',
    'farewell': 'Goodbye',
    'question': 'How are you?'
}

result = engine.localize_object(
    data,
    {
        'source_locale': 'en',
        'target_locale': 'fr'
    }
)
print(result)
# {
#     'greeting': 'Bonjour',
#     'farewell': 'Au revoir',
#     'question': 'Comment allez-vous?'
# }
```

## Async/Await Support

The SDK provides full async/await support for high-performance concurrent processing:

### Basic Async Usage

```python
import asyncio
from lingodotdev import LingoDotDevEngine

async def main():
    # Initialize the engine
    engine = LingoDotDevEngine({
        'api_key': 'your-api-key-here'
    })
    
    # Async text localization
    result = await engine.alocalize_text(
        "Hello, world!",
        {
            'source_locale': 'en',
            'target_locale': 'es'
        }
    )
    print(result)  # "¡Hola, mundo!"
    
    # Don't forget to close the async client
    await engine.close_async_client()

# Run the async function
asyncio.run(main())
```

### Concurrent Processing

```python
import asyncio
from lingodotdev import LingoDotDevEngine

async def concurrent_localization():
    engine = LingoDotDevEngine({
        'api_key': 'your-api-key-here'
    })
    
    # Process multiple texts concurrently
    texts = [
        "Hello, world!",
        "How are you today?",
        "Welcome to our platform!"
    ]
    
    # Create concurrent tasks
    tasks = [
        engine.alocalize_text(text, {
            'source_locale': 'en',
            'target_locale': 'es'
        })
        for text in texts
    ]
    
    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks)
    
    for original, translated in zip(texts, results):
        print(f"{original} -> {translated}")
    
    await engine.close_async_client()

asyncio.run(concurrent_localization())
```

### Async Batch Processing

```python
import asyncio
from lingodotdev import LingoDotDevEngine

async def async_batch_processing():
    engine = LingoDotDevEngine({
        'api_key': 'your-api-key-here'
    })
    
    # Batch localize to multiple languages concurrently
    results = await engine.abatch_localize_text(
        "Welcome to our platform",
        {
            'source_locale': 'en',
            'target_locales': ['es', 'fr', 'de', 'it', 'pt']
        }
    )
    
    languages = ['Spanish', 'French', 'German', 'Italian', 'Portuguese']
    for lang, result in zip(languages, results):
        print(f"{lang}: {result}")
    
    await engine.close_async_client()

asyncio.run(async_batch_processing())
```

## Enhanced Configuration

### Basic Configuration

```python
from lingodotdev import LingoDotDevEngine

# Simple configuration
engine = LingoDotDevEngine({
    'api_key': 'your-api-key-here'
})
```

### Advanced Configuration with Retry Logic

```python
from lingodotdev import LingoDotDevEngine

# Enhanced configuration with retry settings
engine = LingoDotDevEngine({
    'api_key': 'your-api-key-here',
    'api_url': 'https://engine.lingo.dev',  # Custom API URL
    'timeout': 60.0,  # Request timeout in seconds
    'batch_size': 50,  # Items per batch
    'ideal_batch_item_size': 500,  # Target size per batch item
    'retry_config': {
        'max_retries': 3,  # Maximum retry attempts
        'backoff_factor': 2.0,  # Exponential backoff multiplier
        'jitter': True,  # Add random jitter to prevent thundering herd
        'retry_on_status_codes': [500, 502, 503, 504],  # HTTP status codes to retry
        'retry_on_exceptions': ['requests.exceptions.RequestException']
    }
})
```

### Type-Safe Configuration

```python
from lingodotdev import LingoDotDevEngine
from lingodotdev.models import EnhancedEngineConfig, RetryConfiguration

# Using Pydantic models for type safety
retry_config = RetryConfiguration(
    max_retries=5,
    backoff_factor=1.5,
    jitter=True,
    max_delay=60.0
)

config = EnhancedEngineConfig(
    api_key='your-api-key-here',
    timeout=45.0,
    retry_config=retry_config
)

engine = LingoDotDevEngine(config)
```

## API Reference

### LingoDotDevEngine

#### Constructor

```python
engine = LingoDotDevEngine(config)
```

**Parameters:**
- `config` (dict): Configuration dictionary with the following options:
  - `api_key` (str, required): Your Lingo.dev API key

#### Methods

### `localize_text(text, params, progress_callback=None)`

Localize a single text string.

**Parameters:**
- `text` (str): The text to localize
- `params` (dict): Localization parameters
  - `source_locale` (str): Source language code (e.g., 'en')
  - `target_locale` (str): Target language code (e.g., 'es')
- `progress_callback` (callable): Progress callback function

**Returns:** `str` - The localized text

**Example:**
```python
result = engine.localize_text(
    "Welcome to our application",
    {
        'source_locale': 'en',
        'target_locale': 'es'
    }
)
```

### `localize_object(obj, params, progress_callback=None)`

Localize a Python dictionary with string values.

**Parameters:**
- `obj` (dict): The object to localize
- `params` (dict): Localization parameters (same as `localize_text`)
- `progress_callback` (callable): Progress callback function

**Returns:** `dict` - The localized object with the same structure

**Example:**
```python
def progress_callback(progress, source_chunk, processed_chunk):
    print(f"Progress: {progress}%")

result = engine.localize_object(
    {
        'title': 'My App',
        'description': 'A great application',
        'button_text': 'Click me'
    },
    {
        'source_locale': 'en',
        'target_locale': 'de'
    },
    progress_callback=progress_callback
)
```

### `batch_localize_text(text, params)`

Localize a text string to multiple target languages.

**Parameters:**
- `text` (str): The text to localize
- `params` (dict): Batch localization parameters
  - `source_locale` (str): Source language code
  - `target_locales` (list): List of target language codes

**Returns:** `list` - List of localized strings in the same order as target_locales

**Example:**
```python
results = engine.batch_localize_text(
    "Welcome to our platform",
    {
        'source_locale': 'en',
        'target_locales': ['es', 'fr', 'de', 'it']
    }
)
```

### `localize_chat(chat, params, progress_callback=None)`

Localize a chat conversation while preserving speaker names.

**Parameters:**
- `chat` (list): List of chat messages with `name` and `text` keys
- `params` (dict): Localization parameters (same as `localize_text`)
- `progress_callback` (callable, optional): Progress callback function

**Returns:** `list` - Localized chat messages with preserved structure

**Example:**
```python
chat = [
    {'name': 'Alice', 'text': 'Hello everyone!'},
    {'name': 'Bob', 'text': 'How are you doing?'},
    {'name': 'Charlie', 'text': 'Great, thanks for asking!'}
]

result = engine.localize_chat(
    chat,
    {
        'source_locale': 'en',
        'target_locale': 'es'
    }
)
```

### `recognize_locale(text)`

Detect the language of a given text.

**Parameters:**
- `text` (str): The text to analyze

**Returns:** `str` - The detected language code (e.g., 'en', 'es', 'fr')

**Example:**
```python
locale = engine.recognize_locale("Bonjour, comment allez-vous?")
print(locale)  # 'fr'
```

### `whoami()`

Get information about the current API key.

**Returns:** `dict` or `None` - User information with 'email' and 'id' keys, or None if not authenticated

**Example:**
```python
user_info = engine.whoami()
if user_info:
    print(f"Authenticated as: {user_info['email']}")
else:
    print("Not authenticated")
```

## Async API Methods

All synchronous methods have async counterparts with the `a` prefix:

### `alocalize_text(text, params, progress_callback=None)`

Async version of `localize_text` with concurrent processing capabilities.

**Parameters:** Same as `localize_text`
**Returns:** `str` - The localized text

**Example:**
```python
import asyncio

async def main():
    result = await engine.alocalize_text(
        "Welcome to our application",
        {
            'source_locale': 'en',
            'target_locale': 'es'
        }
    )
    print(result)

asyncio.run(main())
```

### `alocalize_object(obj, params, progress_callback=None)`

Async version of `localize_object` with concurrent chunk processing.

**Parameters:** Same as `localize_object`
**Returns:** `dict` - The localized object

### `abatch_localize_text(text, params)`

Async version of `batch_localize_text` with concurrent target language processing.

**Parameters:** Same as `batch_localize_text`
**Returns:** `list` - List of localized strings

**Example:**
```python
async def main():
    results = await engine.abatch_localize_text(
        "Welcome to our platform",
        {
            'source_locale': 'en',
            'target_locales': ['es', 'fr', 'de', 'it']
        }
    )
    print(results)

asyncio.run(main())
```

### `alocalize_chat(chat, params, progress_callback=None)`

Async version of `localize_chat`.

**Parameters:** Same as `localize_chat`
**Returns:** `list` - Localized chat messages

### `arecognize_locale(text)`

Async version of `recognize_locale`.

**Parameters:** Same as `recognize_locale`
**Returns:** `str` - The detected language code

### `awhoami()`

Async version of `whoami`.

**Parameters:** None
**Returns:** `dict` or `None` - User information

### `close_async_client()`

Close the async HTTP client and clean up resources.

**Important:** Always call this method when you're done with async operations to properly clean up resources.

**Example:**
```python
async def main():
    engine = LingoDotDevEngine({'api_key': 'your-key'})
    
    # Perform async operations
    result = await engine.alocalize_text("Hello", {"target_locale": "es"})
    
    # Clean up
    await engine.close_async_client()

asyncio.run(main())
```

## Error Handling

The SDK provides enhanced error handling with detailed error information and intelligent suggestions:

### Exception Hierarchy

- `LingoDevError`: Base exception for all SDK errors
- `LingoDevAPIError`: API-related errors (HTTP 4xx/5xx responses)
- `LingoDevNetworkError`: Network connectivity issues
- `LingoDevRetryExhaustedError`: When retry attempts are exhausted
- `LingoDevValidationError`: Data validation errors
- `LingoDevConfigurationError`: Configuration-related errors
- `LingoDevTimeoutError`: Request timeout errors

### Basic Error Handling

```python
from lingodotdev import LingoDotDevEngine
from lingodotdev.exceptions import LingoDevError, LingoDevAPIError

try:
    engine = LingoDotDevEngine({'api_key': 'your-api-key'})
    result = engine.localize_text("Hello", {'target_locale': 'es'})
except LingoDevAPIError as e:
    print(f"API Error: {e}")
    print(f"Status Code: {e.status_code}")
    print(f"Suggestions: {e.suggestions}")
except LingoDevError as e:
    print(f"SDK Error: {e}")
    print(f"Error Details: {e.details}")
```

### Advanced Error Handling with Retry

```python
from lingodotdev import LingoDotDevEngine
from lingodotdev.exceptions import LingoDevRetryExhaustedError

# Configure retry behavior
engine = LingoDotDevEngine({
    'api_key': 'your-api-key',
    'retry_config': {
        'max_retries': 3,
        'backoff_factor': 2.0,
        'jitter': True
    }
})

try:
    result = engine.localize_text("Hello", {'target_locale': 'es'})
except LingoDevRetryExhaustedError as e:
    print(f"All retry attempts failed: {e}")
    print(f"Total attempts: {e.total_attempts}")
    print(f"Last error: {e.last_error}")
```

### Error Context and Debugging

```python
try:
    result = engine.localize_text("Hello", {'target_locale': 'invalid'})
except LingoDevError as e:
    # All errors include timestamp and context
    print(f"Error occurred at: {e.timestamp}")
    print(f"Error context: {e.details}")
    
    # API errors include request details
    if hasattr(e, 'request_details'):
        print(f"Request details: {e.request_details}")
    
    # Some errors include helpful suggestions
    if hasattr(e, 'suggestions'):
        print(f"Suggestions: {e.suggestions}")
```

## Advanced Usage

### Using Reference Translations

You can provide reference translations to improve consistency:

```python
reference = {
    'es': {
        'greeting': 'Hola',
        'app_name': 'Mi Aplicación'
    },
    'fr': {
        'greeting': 'Bonjour',
        'app_name': 'Mon Application'
    }
}

result = engine.localize_object(
    {
        'greeting': 'Hello',
        'app_name': 'My App',
        'welcome_message': 'Welcome to My App'
    },
    {
        'source_locale': 'en',
        'target_locale': 'es',
        'reference': reference
    }
)
```

### Progress Tracking

For long-running operations, you can track progress:

```python
def progress_callback(progress, source_chunk, processed_chunk):
    print(f"Progress: {progress}%")
    print(f"Processing: {len(source_chunk)} items")
    print(f"Completed: {len(processed_chunk)} items")

# Large dataset that will be processed in chunks
large_data = {f"key_{i}": f"Text content {i}" for i in range(1000)}

result = engine.localize_object(
    large_data,
    {
        'source_locale': 'en',
        'target_locale': 'es'
    },
    progress_callback=progress_callback
)
```


## Development

### Setup

```bash
git clone https://github.com/lingodotdev/sdk-python.git
cd sdk-python
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/lingo_dev_sdk --cov-report=html

# Run only unit tests
pytest tests/test_engine.py

# Run integration tests (requires API key)
export LINGO_DEV_API_KEY=your-api-key
pytest tests/test_integration.py
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy src/lingo_dev_sdk
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Commit your changes using [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: add new feature`
   - `fix: resolve bug`
   - `docs: update documentation`
   - `style: format code`
   - `refactor: refactor code`
   - `test: add tests`
   - `chore: update dependencies`
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Release Process

This project uses automated semantic releases:

- **Pull Requests**: Automatically run tests and build checks
- **Main Branch**: Automatically analyzes commit messages, bumps version, updates changelog, and publishes to PyPI
- **Commit Messages**: Must follow [Conventional Commits](https://www.conventionalcommits.org/) format
  - `feat:` triggers a minor version bump (0.1.0 → 0.2.0)
  - `fix:` triggers a patch version bump (0.1.0 → 0.1.1)
  - `BREAKING CHANGE:` triggers a major version bump (0.1.0 → 1.0.0)

### Development Workflow

1. Create a feature branch
2. Make changes with proper commit messages
3. Open a PR (triggers CI/CD)
4. Merge to main (triggers release if applicable)
5. Automated release to PyPI

## Support

- 📧 Email: [hi@lingo.dev](mailto:hi@lingo.dev)
- 🐛 Issues: [GitHub Issues](https://github.com/lingodotdev/sdk-python/issues)
- 📖 Documentation: [https://lingo.dev/sdk](https://lingo.dev/sdk)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes.

---

> 💬 **[Join our Discord community](https://lingo.dev/go/discord)** for support, discussions, and updates!