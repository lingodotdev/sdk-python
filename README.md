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
- 🚀 **Batch Processing**: Efficient handling of large content with automatic chunking
- 🔄 **Progress Tracking**: Optional progress callbacks for long-running operations
- 🎯 **Language Detection**: Automatic language recognition
- 📊 **Fast Mode**: Optional fast processing for larger batches
- 🛡️ **Type Safety**: Full type hints and Pydantic validation
- 🧪 **Well Tested**: Comprehensive test suite with high coverage
- 🔧 **Easy Configuration**: Simple setup with minimal configuration required

## Installation

```bash
pip install lingodotdev
```

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

## Error Handling

The SDK raises the following exceptions:

- `ValueError`: For invalid input parameters
- `RuntimeError`: For API errors and network issues
- `pydantic.ValidationError`: For configuration validation errors

**Example:**
```python
try:
    result = engine.localize_text(
        "Hello world",
        {'target_locale': 'es'}  # Missing source_locale
    )
except ValueError as e:
    print(f"Invalid parameters: {e}")
except RuntimeError as e:
    print(f"API error: {e}")
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
- 📖 Documentation: [https://lingo.dev/docs](https://lingo.dev/docs)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes.

---

> 💬 **[Join our Discord community](https://lingo.dev/go/discord)** for support, discussions, and updates!