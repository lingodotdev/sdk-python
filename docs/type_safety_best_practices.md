# Type Safety Best Practices

## Overview

The enhanced Lingo.dev Python SDK provides comprehensive type safety through static type hints, runtime validation with Pydantic, and mypy compatibility. This guide covers best practices for leveraging these type safety features.

## Type Safety Features

### 1. Static Type Hints
All methods include comprehensive type annotations:

```python
from typing import Dict, List, Optional, Any
from lingodotdev import LingoDotDevEngine

# Type hints are included for all parameters and return values
def localize_content(
    engine: LingoDotDevEngine,
    text: str,
    target_locale: str
) -> str:
    result: str = engine.localize_text(
        text,
        {'target_locale': target_locale}
    )
    return result
```

### 2. Runtime Validation with Pydantic
Configuration and parameters are validated at runtime:

```python
from lingodotdev import LingoDotDevEngine
from lingodotdev.models import EnhancedEngineConfig, RetryConfiguration

# Type-safe configuration
config = EnhancedEngineConfig(
    api_key="your-api-key",
    timeout=30.0,  # Must be a float
    batch_size=25,  # Must be an integer
    retry_config=RetryConfiguration(
        max_retries=3,
        backoff_factor=2.0
    )
)

engine = LingoDotDevEngine(config)
```

### 3. MyPy Compatibility
The SDK is fully compatible with mypy for static type checking:

```bash
# Run mypy on your code
mypy your_application.py
```

## Best Practices

### 1. Use Type Annotations

#### ✅ Good: Explicit Type Annotations
```python
from typing import Dict, List, Optional
from lingodotdev import LingoDotDevEngine

def batch_localize(
    engine: LingoDotDevEngine,
    texts: List[str],
    target_locales: List[str]
) -> List[List[str]]:
    results: List[List[str]] = []
    
    for text in texts:
        batch_result: List[str] = engine.batch_localize_text(
            text,
            {
                'source_locale': 'en',
                'target_locales': target_locales
            }
        )
        results.append(batch_result)
    
    return results
```

#### ❌ Avoid: Missing Type Annotations
```python
def batch_localize(engine, texts, target_locales):  # No type hints
    results = []  # Type unclear
    # ... rest of implementation
    return results
```

### 2. Use TypedDict for Parameters

#### ✅ Good: TypedDict for Structured Parameters
```python
from typing_extensions import TypedDict
from lingodotdev import LingoDotDevEngine

class LocalizationParams(TypedDict):
    source_locale: str
    target_locale: str
    fast: bool

def localize_with_params(
    engine: LingoDotDevEngine,
    text: str,
    params: LocalizationParams
) -> str:
    return engine.localize_text(text, params)

# Usage
params: LocalizationParams = {
    'source_locale': 'en',
    'target_locale': 'es',
    'fast': True
}
```

#### ❌ Avoid: Untyped Dictionaries
```python
def localize_with_params(engine, text, params):  # params type unclear
    return engine.localize_text(text, params)

# Usage - no type safety
params = {'source_locale': 'en', 'target_locale': 'es'}  # Could have typos
```

### 3. Use Pydantic Models for Configuration

#### ✅ Good: Pydantic Models
```python
from lingodotdev.models import EnhancedEngineConfig, RetryConfiguration

# Type-safe configuration with validation
retry_config = RetryConfiguration(
    max_retries=5,
    backoff_factor=1.5,
    jitter=True,
    max_delay=60.0
)

config = EnhancedEngineConfig(
    api_key="your-api-key",
    api_url="https://engine.lingo.dev",
    timeout=45.0,
    retry_config=retry_config
)

# Validation happens automatically
engine = LingoDotDevEngine(config)
```

#### ❌ Avoid: Plain Dictionaries for Complex Configuration
```python
# No validation, prone to errors
config = {
    'api_key': 'your-api-key',
    'timeout': '45',  # Wrong type (string instead of float)
    'retry_config': {
        'max_retries': -1,  # Invalid value
        'backoff_factor': 'invalid'  # Wrong type
    }
}
```

### 4. Handle Optional Values Properly

#### ✅ Good: Explicit Optional Handling
```python
from typing import Optional
from lingodotdev import LingoDotDevEngine

def safe_whoami(engine: LingoDotDevEngine) -> Optional[str]:
    user_info: Optional[Dict[str, str]] = engine.whoami()
    
    if user_info is not None:
        return user_info.get('email')
    return None

# Usage with type checking
email: Optional[str] = safe_whoami(engine)
if email is not None:
    print(f"Logged in as: {email}")
```

#### ❌ Avoid: Ignoring Optional Types
```python
def unsafe_whoami(engine):
    user_info = engine.whoami()  # Could be None
    return user_info['email']  # Could raise KeyError if None
```

### 5. Use Generic Types for Collections

#### ✅ Good: Specific Generic Types
```python
from typing import List, Dict, Any
from lingodotdev import LingoDotDevEngine

def localize_object_list(
    engine: LingoDotDevEngine,
    objects: List[Dict[str, Any]],
    target_locale: str
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    
    for obj in objects:
        localized: Dict[str, Any] = engine.localize_object(
            obj,
            {'target_locale': target_locale}
        )
        results.append(localized)
    
    return results
```

#### ❌ Avoid: Untyped Collections
```python
def localize_object_list(engine, objects, target_locale):  # No type info
    results = []  # Could contain anything
    for obj in objects:  # obj type unknown
        results.append(engine.localize_object(obj, {'target_locale': target_locale}))
    return results
```

### 6. Use Protocol for Callback Types

#### ✅ Good: Protocol for Callbacks
```python
from typing import Protocol
from lingodotdev import LingoDotDevEngine

class ProgressCallback(Protocol):
    def __call__(self, progress: int) -> None: ...

class DetailedProgressCallback(Protocol):
    def __call__(
        self, 
        progress: int, 
        source_chunk: Dict[str, str], 
        processed_chunk: Dict[str, str]
    ) -> None: ...

def localize_with_progress(
    engine: LingoDotDevEngine,
    text: str,
    target_locale: str,
    callback: ProgressCallback
) -> str:
    return engine.localize_text(
        text,
        {'target_locale': target_locale},
        progress_callback=callback
    )
```

### 7. Async Type Safety

#### ✅ Good: Proper Async Type Annotations
```python
import asyncio
from typing import List, Awaitable
from lingodotdev import LingoDotDevEngine

async def async_batch_localize(
    engine: LingoDotDevEngine,
    texts: List[str],
    target_locale: str
) -> List[str]:
    tasks: List[Awaitable[str]] = [
        engine.alocalize_text(text, {'target_locale': target_locale})
        for text in texts
    ]
    
    results: List[str] = await asyncio.gather(*tasks)
    await engine.close_async_client()
    
    return results
```

## MyPy Configuration

### Recommended mypy.ini Settings
```ini
[mypy]
python_version = 3.8
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true
show_error_codes = true

# External dependencies
[mypy-requests.*]
ignore_missing_imports = true

[mypy-aiohttp.*]
ignore_missing_imports = true

[mypy-nanoid.*]
ignore_missing_imports = true
```

### Running MyPy
```bash
# Check specific file
mypy your_application.py

# Check entire project
mypy src/

# Generate HTML report
mypy --html-report mypy-report src/
```

## Common Type Safety Patterns

### 1. Factory Functions with Type Safety
```python
from typing import Union, overload
from lingodotdev import LingoDotDevEngine
from lingodotdev.models import EnhancedEngineConfig

@overload
def create_engine(config: Dict[str, Any]) -> LingoDotDevEngine: ...

@overload
def create_engine(config: EnhancedEngineConfig) -> LingoDotDevEngine: ...

def create_engine(
    config: Union[Dict[str, Any], EnhancedEngineConfig]
) -> LingoDotDevEngine:
    return LingoDotDevEngine(config)
```

### 2. Context Managers with Type Safety
```python
from typing import AsyncContextManager
from contextlib import asynccontextmanager
from lingodotdev import LingoDotDevEngine

@asynccontextmanager
async def localization_engine(api_key: str) -> AsyncContextManager[LingoDotDevEngine]:
    engine = LingoDotDevEngine({'api_key': api_key})
    try:
        yield engine
    finally:
        await engine.close_async_client()

# Usage
async def main() -> None:
    async with localization_engine('your-api-key') as engine:
        result: str = await engine.alocalize_text(
            "Hello", 
            {'target_locale': 'es'}
        )
        print(result)
```

### 3. Error Handling with Type Safety
```python
from typing import Union, Result  # Python 3.12+
from lingodotdev import LingoDotDevEngine
from lingodotdev.exceptions import LingoDevError

def safe_localize(
    engine: LingoDotDevEngine,
    text: str,
    target_locale: str
) -> Union[str, LingoDevError]:
    try:
        result: str = engine.localize_text(
            text,
            {'target_locale': target_locale}
        )
        return result
    except LingoDevError as e:
        return e
```

## IDE Integration

### VS Code Settings
```json
{
    "python.linting.mypyEnabled": true,
    "python.linting.enabled": true,
    "python.analysis.typeCheckingMode": "strict",
    "python.analysis.autoImportCompletions": true
}
```

### PyCharm Settings
- Enable "Type Checker" inspection
- Set "Python Type Checker" to "mypy"
- Enable "Missing type hinting" inspections

## Testing Type Safety

### Unit Tests with Type Assertions
```python
import pytest
from typing import TYPE_CHECKING
from lingodotdev import LingoDotDevEngine

if TYPE_CHECKING:
    # Type checking only imports
    from typing import Any

def test_type_safety() -> None:
    engine: LingoDotDevEngine = LingoDotDevEngine({'api_key': 'test'})
    
    # Test with proper types
    result: str = engine.localize_text("Hello", {'target_locale': 'es'})
    assert isinstance(result, str)
    
    # Test configuration validation
    with pytest.raises(ValueError):
        LingoDotDevEngine({'api_key': 123})  # Wrong type
```

### Property-Based Testing
```python
from hypothesis import given, strategies as st
from lingodotdev import LingoDotDevEngine

@given(
    text=st.text(min_size=1, max_size=100),
    target_locale=st.sampled_from(['es', 'fr', 'de', 'it'])
)
def test_localize_text_types(text: str, target_locale: str) -> None:
    engine = LingoDotDevEngine({'api_key': 'test'})
    
    # Mock the actual API call for testing
    with patch.object(engine, '_localize_raw') as mock:
        mock.return_value = {'text': 'mocked_result'}
        
        result: str = engine.localize_text(text, {'target_locale': target_locale})
        assert isinstance(result, str)
```

## Troubleshooting Type Issues

### Common MyPy Errors and Solutions

1. **"Argument has incompatible type"**
   ```python
   # Error: Argument 1 to "localize_text" has incompatible type "int"; expected "str"
   engine.localize_text(123, {'target_locale': 'es'})  # Wrong!
   
   # Fix: Use correct type
   engine.localize_text("123", {'target_locale': 'es'})  # Correct
   ```

2. **"Missing return statement"**
   ```python
   def get_locale(text: str) -> str:  # Promises to return str
       if text:
           return engine.recognize_locale(text)
       # Missing return for else case!
   
   # Fix: Handle all cases
   def get_locale(text: str) -> str:
       if text:
           return engine.recognize_locale(text)
       return "unknown"  # Default return
   ```

3. **"Incompatible default for argument"**
   ```python
   def localize(text: str, params: Dict[str, str] = {}) -> str:  # Mutable default!
   
   # Fix: Use None as default
   def localize(text: str, params: Optional[Dict[str, str]] = None) -> str:
       if params is None:
           params = {}
   ```

## Conclusion

Type safety in the Lingo.dev SDK provides:
- **Early Error Detection**: Catch issues at development time
- **Better IDE Support**: Enhanced autocomplete and refactoring
- **Self-Documenting Code**: Types serve as documentation
- **Reduced Runtime Errors**: Fewer production issues
- **Improved Maintainability**: Easier to understand and modify code

By following these best practices, you can leverage the full power of Python's type system while using the Lingo.dev SDK effectively and safely."