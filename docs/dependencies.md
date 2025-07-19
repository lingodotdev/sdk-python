# Dependencies and Requirements

## Overview

This document outlines the dependencies and requirements for the enhanced Lingo.dev Python SDK, including async support, improved error handling, and retry capabilities.

## Python Version Compatibility

The SDK requires Python 3.8 or higher. We recommend using the latest stable Python version for optimal performance and security.

## Core Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `requests` | >=2.25.0 | HTTP client for synchronous API calls |
| `pydantic` | >=2.0.0 | Data validation and settings management |
| `nanoid` | >=2.0.0 | Generation of unique workflow IDs |
| `typing-extensions` | >=4.0.0 | Enhanced typing support for backward compatibility |
| `aiohttp` | >=3.8.0 | Async HTTP client for asynchronous API calls |

## Installation Options

### Basic Installation

```bash
pip install lingodotdev
```

This installs all core dependencies including async support.

### With Optional Dependencies

#### Async Support
```bash
pip install lingodotdev[async]
```

Note: Async dependencies are already included in the core installation, but this option is available for explicit async-only installations.

#### Development Dependencies
```bash
pip install lingodotdev[dev]
```

This includes all development tools:
- Testing frameworks (pytest, pytest-asyncio, pytest-cov)
- Code formatting (black)
- Linting (flake8)
- Type checking (mypy)
- Type stubs (types-requests, types-aiohttp)
- Release management (python-semantic-release)

#### Testing Only
```bash
pip install lingodotdev[test]
```

This includes only testing dependencies without development tools.

#### All Dependencies
```bash
pip install lingodotdev[dev,async,test]
```

## Dependency Changes from Previous Versions

### New Dependencies

1. **aiohttp (>=3.8.0)**
   - Added for async/await functionality
   - Provides efficient asynchronous HTTP requests
   - Required for all async methods (`alocalize_text`, `alocalize_object`, etc.)

2. **pydantic (>=2.0.0)**
   - Added for enhanced data validation and configuration management
   - Provides runtime type checking and validation
   - Used for `EnhancedEngineConfig`, `LocalizationParams`, and `RetryConfiguration`

3. **typing-extensions (>=4.0.0)**
   - Added for enhanced typing support across Python versions
   - Provides `TypedDict`, `Protocol`, and other advanced typing features
   - Ensures compatibility with older Python versions

### Updated Dependencies

- **requests**: Maintained minimum version of 2.25.0 for stability
- **nanoid**: Maintained minimum version of 2.0.0 for workflow ID generation

## Development Dependencies

### Testing
- **pytest (>=7.0.0)**: Main testing framework
- **pytest-asyncio (>=0.21.0)**: Async testing support
- **pytest-cov (>=4.0.0)**: Test coverage reporting

### Code Quality
- **black (>=23.0.0)**: Code formatting
- **flake8 (>=6.0.0)**: Code linting
- **mypy (>=1.0.0)**: Static type checking

### Type Stubs
- **types-requests (>=2.25.0)**: Type stubs for requests library
- **types-aiohttp (>=3.8.0)**: Type stubs for aiohttp library

### Release Management
- **python-semantic-release (>=8.0.0)**: Automated versioning and releases

## Configuration Files

### MyPy Configuration
The project includes a `mypy.ini` file with strict type checking configuration:
- Strict mode enabled
- Comprehensive warning settings
- Module-specific overrides for external dependencies

### Requirements Files
- `requirements.txt`: Core dependencies
- `requirements-dev.txt`: Development dependencies
- `requirements-async.txt`: Async-specific dependencies (currently same as core)

## Compatibility Notes

### Python 3.8+
- All features are fully supported
- Native typing support where available
- Optimal performance and compatibility

### Async Support
- Requires Python 3.8+ for full async/await support
- aiohttp provides the async HTTP client functionality
- Concurrent processing capabilities with asyncio

### Type Safety
- Enhanced type checking with mypy
- Runtime validation with pydantic
- Comprehensive type annotations throughout the codebase

## Installation Troubleshooting

### Common Issues

1. **Python Version**: Ensure you're using Python 3.8 or higher
2. **Virtual Environment**: Recommended to use a virtual environment
3. **Dependency Conflicts**: Use `pip install --upgrade` to resolve version conflicts

### Verification

After installation, verify the setup:

```python
import lingodotdev
print(lingodotdev.__version__)

# Test async support
import asyncio
from lingodotdev import LingoDotDevEngine

async def test_async():
    engine = LingoDotDevEngine({"api_key": "your_key"})
    # Async methods are available
    assert hasattr(engine, 'alocalize_text')
    print("Async support verified!")

# Run if in an async context
# asyncio.run(test_async())
```

## Future Dependencies

The SDK is designed to be extensible. Future versions may include:
- Additional HTTP client options
- Enhanced monitoring and metrics libraries
- Performance optimization libraries
- Additional type checking tools

All new dependencies will be added as optional dependencies to maintain backward compatibility.