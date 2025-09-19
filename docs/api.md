# Table of Contents

* [lingodotdev.engine](#lingodotdev.engine)
  * [EngineConfig](#lingodotdev.engine.EngineConfig)
    * [validate\_api\_url](#lingodotdev.engine.EngineConfig.validate_api_url)
  * [LocalizationParams](#lingodotdev.engine.LocalizationParams)
    * [validate\_locale](#lingodotdev.engine.LocalizationParams.validate_locale)
  * [LingoDotDevEngine](#lingodotdev.engine.LingoDotDevEngine)
    * [\_\_init\_\_](#lingodotdev.engine.LingoDotDevEngine.__init__)
    * [\_\_aenter\_\_](#lingodotdev.engine.LingoDotDevEngine.__aenter__)
    * [\_\_aexit\_\_](#lingodotdev.engine.LingoDotDevEngine.__aexit__)
    * [close](#lingodotdev.engine.LingoDotDevEngine.close)
    * [localize\_object](#lingodotdev.engine.LingoDotDevEngine.localize_object)
    * [localize\_text](#lingodotdev.engine.LingoDotDevEngine.localize_text)
    * [batch\_localize\_text](#lingodotdev.engine.LingoDotDevEngine.batch_localize_text)
    * [localize\_chat](#lingodotdev.engine.LingoDotDevEngine.localize_chat)
    * [recognize\_locale](#lingodotdev.engine.LingoDotDevEngine.recognize_locale)
    * [whoami](#lingodotdev.engine.LingoDotDevEngine.whoami)
    * [batch\_localize\_objects](#lingodotdev.engine.LingoDotDevEngine.batch_localize_objects)
    * [quick\_translate](#lingodotdev.engine.LingoDotDevEngine.quick_translate)
    * [quick\_batch\_translate](#lingodotdev.engine.LingoDotDevEngine.quick_batch_translate)

<a id="lingodotdev.engine"></a>

# lingodotdev.engine

Async client implementation for the Lingo.dev localization service.

This module provides LingoDotDevEngine and supporting data models for
configuration and localization parameter validation.

  config = {"api_key": "your-api-key"}
  async with LingoDotDevEngine(config) as engine:
      result = await engine.localize_text("Hello", {"target_locale": "es"})

<a id="lingodotdev.engine.EngineConfig"></a>

## EngineConfig Objects

```python
class EngineConfig(BaseModel)
```

Runtime configuration for LingoDotDevEngine.

Stores and validates configuration parameters required to interact with the
Lingo.dev API.

**Attributes**:

- `api_key` - Secret token used to authenticate with the Lingo.dev API.
- `api_url` - Base endpoint for the localization engine. Defaults to
  'https://engine.lingo.dev'.
- `batch_size` - Maximum number of top-level entries to send in a single
  localization request (between 1 and 250 inclusive).
- `ideal_batch_item_size` - Target word count per request before payloads are
  split into multiple batches (between 1 and 2500 inclusive).

<a id="lingodotdev.engine.EngineConfig.validate_api_url"></a>

### validate\_api\_url

```python
@validator("api_url")
@classmethod
def validate_api_url(cls, v: str) -> str
```

Validates that the API URL is a valid HTTP/HTTPS URL.

**Arguments**:

- `v` - The URL string to validate.
  

**Returns**:

  The validated URL string.
  

**Raises**:

- `ValueError` - If the URL doesn't start with http:// or https://.

<a id="lingodotdev.engine.LocalizationParams"></a>

## LocalizationParams Objects

```python
class LocalizationParams(BaseModel)
```

Request parameters for localization operations.

These values are serialized directly into API requests after validation.

**Attributes**:

- `source_locale` - Optional BCP 47 language code representing the source
  language. When omitted, the API attempts automatic detection.
- `target_locale` - Required BCP 47 language code for the desired
  translation target.
- `fast` - Optional flag that enables the service's low-latency translation
  mode at the cost of some quality safeguards.
- `reference` - Optional nested mapping of existing translations that
  provides additional context to the engine.

<a id="lingodotdev.engine.LocalizationParams.validate_locale"></a>

### validate\_locale

```python
@validator("source_locale", "target_locale")
@classmethod
def validate_locale(cls, v: Optional[str]) -> Optional[str]
```

Validates that locale codes conform to BCP 47 standards.

**Arguments**:

- `v` - The locale string to validate, or None.
  

**Returns**:

  The validated locale string or None.
  

**Raises**:

- `ValueError` - If the locale is not a valid BCP 47 language tag.

<a id="lingodotdev.engine.LingoDotDevEngine"></a>

## LingoDotDevEngine Objects

```python
class LingoDotDevEngine()
```

Asynchronous client for the Lingo.dev localization API.

The engine manages an httpx.AsyncClient, handles chunking and batching of
content, and exposes helper coroutines for translating strings, structured
objects, and chat transcripts.

All localization methods are async and must be awaited.

<a id="lingodotdev.engine.LingoDotDevEngine.__init__"></a>

### \_\_init\_\_

```python
def __init__(config: Dict[str, Any])
```

Instantiates the engine with configuration data.

**Arguments**:

- `config` - Mapping of values understood by `EngineConfig`. At minimum
  an `api_key` entry must be supplied.
  

**Raises**:

- `ValueError` - If the supplied configuration fails validation.

<a id="lingodotdev.engine.LingoDotDevEngine.__aenter__"></a>

### \_\_aenter\_\_

```python
async def __aenter__()
```

Opens the HTTP session when entering an async context.

**Returns**:

- ``LingoDotDevEngine`` - The active engine instance.

<a id="lingodotdev.engine.LingoDotDevEngine.__aexit__"></a>

### \_\_aexit\_\_

```python
async def __aexit__(exc_type, exc_val, exc_tb)
```

Releases resources acquired during the async context.

<a id="lingodotdev.engine.LingoDotDevEngine.close"></a>

### close

```python
async def close()
```

Closes the HTTP client if it has been created.

<a id="lingodotdev.engine.LingoDotDevEngine.localize_object"></a>

### localize\_object

```python
async def localize_object(obj: Dict[str, Any],
                          params: Dict[str, Any],
                          progress_callback: Optional[
                              Callable[[int, Dict[str, str], Dict[str, str]],
                                       None]] = None,
                          concurrent: bool = False) -> Dict[str, Any]
```

Localizes every string value contained in a mapping.

**Arguments**:

- `obj` - Mapping whose string leaves should be translated.
- `params` - Dictionary of options accepted by `LocalizationParams`.
- `progress_callback` - Optional callable invoked with progress updates
  (0-100) alongside the source and localized chunks. Do not set
  `concurrent` when providing this callback because progress
  updates are unavailable in concurrent mode.
- `concurrent` - When `True` the payload chunks are processed
  concurrently and no progress updates are emitted.
  

**Returns**:

  A dictionary mirroring `obj` with localized string values.
  

**Raises**:

- `RuntimeError` - If the API responds with an error.
- `ValueError` - If the API rejects the request.
  

**Examples**:

    ```python
    async with LingoDotDevEngine({"api_key": "token"}) as engine:
        localized = await engine.localize_object(
            {"title": "Hello"},
            {"target_locale": "es"},
            concurrent=True,
        )
        # localized -> {"title": "Hola"}  (example output)

    async with LingoDotDevEngine({"api_key": "token"}) as engine:
        def on_progress(percent, *_):
            print(f"Progress: {percent}%")

        localized = await engine.localize_object(
            {"welcome": "Hello", "farewell": "Goodbye"},
            {"source_locale": "en", "target_locale": "fr"},
            progress_callback=on_progress,
        )
        # localized -> {"welcome": "Bonjour", "farewell": "Au revoir"}  (example output)
    ```

<a id="lingodotdev.engine.LingoDotDevEngine.localize_text"></a>

### localize\_text

```python
async def localize_text(
        text: str,
        params: Dict[str, Any],
        progress_callback: Optional[Callable[[int], None]] = None) -> str
```

Localizes a single text string.

**Arguments**:

- `text` - The text to translate.
- `params` - Dictionary of options accepted by `LocalizationParams`.
- `progress_callback` - Optional callable receiving the percentage
  complete (0-100).
  

**Returns**:

  The localized text string.
  

**Raises**:

- `RuntimeError` - If the API responds with an error.
- `ValueError` - If the API rejects the request.
  

**Examples**:

    ```python
    async with LingoDotDevEngine({"api_key": "token"}) as engine:
        greeting = await engine.localize_text(
            "Hello", {"target_locale": "de"}
        )
        # greeting -> "Hallo"  (example output)

    progress_updates = []

    async with LingoDotDevEngine({"api_key": "token"}) as engine:
        farewell = await engine.localize_text(
            "Goodbye",
            {"source_locale": "en", "target_locale": "it"},
            progress_callback=progress_updates.append,
        )
        # farewell -> "Arrivederci"  (example output)
    ```

<a id="lingodotdev.engine.LingoDotDevEngine.batch_localize_text"></a>

### batch\_localize\_text

```python
async def batch_localize_text(text: str, params: Dict[str, Any]) -> List[str]
```

Localizes a single text string into multiple target locales.

**Arguments**:

- `text` - The text string to translate.
- `params` - Dictionary of options accepted by `LocalizationParams` plus
  a `target_locales` list.
  

**Returns**:

  Localized strings ordered to match `target_locales`.
  

**Raises**:

- `ValueError` - If `target_locales` is missing or the API rejects a
  request.
- `RuntimeError` - If the API responds with an error.
  

**Examples**:

    ```python
    async with LingoDotDevEngine({"api_key": "token"}) as engine:
        variants = await engine.batch_localize_text(
            "Welcome",
            {"target_locales": ["es", "fr"]},
        )
        # variants -> ["Bienvenido", "Bienvenue"]  (example output)

    async with LingoDotDevEngine({"api_key": "token"}) as engine:
        variants = await engine.batch_localize_text(
            "Checkout",
            {
                "source_locale": "en",
                "target_locales": ["pt-BR", "it"],
                "fast": True,
            },
        )
        # variants -> ["Finalizar compra", "Pagamento"]  (example output)
    ```

<a id="lingodotdev.engine.LingoDotDevEngine.localize_chat"></a>

### localize\_chat

```python
async def localize_chat(
    chat: List[Dict[str, str]],
    params: Dict[str, Any],
    progress_callback: Optional[Callable[[int], None]] = None
) -> List[Dict[str, str]]
```

Localizes a chat transcript while preserving speaker metadata.

**Arguments**:

- `chat` - Sequence of chat messages. Each item must include `name` and
  `text` keys.
- `params` - Dictionary of options accepted by `LocalizationParams`.
- `progress_callback` - Optional callable receiving percentage updates
  (0-100) while the transcript is localized.
  

**Returns**:

  Localized chat messages in the same order as `chat`. If the API
  omits chat data an empty list is returned.
  

**Raises**:

- `ValueError` - If any message in `chat` omits the required keys.
- `RuntimeError` - If the API responds with an error.
  

**Examples**:

    ```python
    chat = [
        {"name": "Alice", "text": "Hello"},
        {"name": "Bob", "text": "Goodbye"},
    ]

    async with LingoDotDevEngine({"api_key": "token"}) as engine:
        translated = await engine.localize_chat(
            chat,
            {"target_locale": "es"},
        )
        # translated -> [{"name": "Alice", "text": "Hola"}, ...]  (example output)

    updates = []

    async with LingoDotDevEngine({"api_key": "token"}) as engine:
        translated = await engine.localize_chat(
            chat,
            {"source_locale": "en", "target_locale": "de"},
            progress_callback=updates.append,
        )
        # translated -> [{"name": "Alice", "text": "Hallo"}, ...]  (example output)
    ```

<a id="lingodotdev.engine.LingoDotDevEngine.recognize_locale"></a>

### recognize\_locale

```python
async def recognize_locale(text: str) -> str
```

Detects the language of the supplied text.

**Arguments**:

- `text` - Non-empty string to analyse.
  

**Returns**:

  Locale code reported by the API (for example `"en"`) or an
  empty string when the service cannot determine a locale.
  

**Raises**:

- `ValueError` - If `text` is empty or only whitespace.
- `RuntimeError` - If the request fails or the API reports an error.

<a id="lingodotdev.engine.LingoDotDevEngine.whoami"></a>

### whoami

```python
async def whoami() -> Optional[Dict[str, str]]
```

Retrieves account metadata associated with the current API key.

**Returns**:

  Dictionary containing `email` and `id` keys when available, or
  `None` if the key is unauthenticated or a recoverable network error
  occurs.
  

**Raises**:

- `RuntimeError` - If the service reports a server-side error.

<a id="lingodotdev.engine.LingoDotDevEngine.batch_localize_objects"></a>

### batch\_localize\_objects

```python
async def batch_localize_objects(
        objects: List[Dict[str, Any]],
        params: Dict[str, Any]) -> List[Dict[str, Any]]
```

Localizes multiple mapping objects concurrently.

**Arguments**:

- `objects` - List of objects whose string values should be translated.
- `params` - Dictionary of options accepted by `LocalizationParams`,
  shared across all objects.
  

**Returns**:

  Localized objects preserving the order of `objects`.
  

**Raises**:

- `RuntimeError` - If the API responds with an error.
- `ValueError` - If the API rejects a request.

<a id="lingodotdev.engine.LingoDotDevEngine.quick_translate"></a>

### quick\_translate

```python
@classmethod
async def quick_translate(cls,
                          content: Any,
                          api_key: str,
                          target_locale: str,
                          source_locale: Optional[str] = None,
                          api_url: str = "https://engine.lingo.dev",
                          fast: bool = True) -> Any
```

Translates content without managing an engine instance manually.

The helper opens a `LingoDotDevEngine` using the supplied configuration,
performs the translation, and automatically closes the underlying HTTP
client.

**Arguments**:

- `content` - Text string or mapping to translate. The returned value
  matches the type of `content`.
- `api_key` - Lingo.dev API key to authenticate the request.
- `target_locale` - Target language code for the translation.
- `source_locale` - Optional source language code. When omitted the API
  may attempt to detect it.
- `api_url` - Lingo.dev engine base URL. Defaults to
  `"https://engine.lingo.dev"`.
- `fast` - Whether to enable the service's fast translation mode.
  

**Returns**:

  Translated content with the same type as `content`.
  

**Raises**:

- `ValueError` - If `content` is not a string or dictionary, or if the
  service rejects the request.
- `RuntimeError` - If the API indicates a failure or the request cannot
  be completed.
  

**Examples**:

    ```python
    greeting = await LingoDotDevEngine.quick_translate(
        "Hello world",
        api_key="api-key",
        target_locale="es",
    )
    # greeting -> "Hola mundo"  (example output)

    landing_page = await LingoDotDevEngine.quick_translate(
        {"headline": "Hello", "cta": "Buy now"},
        api_key="api-key",
        target_locale="de",
        source_locale="en",
        fast=False,
    )
    # landing_page -> {"headline": "Hallo", "cta": "Jetzt kaufen"}  (example output)
    ```

<a id="lingodotdev.engine.LingoDotDevEngine.quick_batch_translate"></a>

### quick\_batch\_translate

```python
@classmethod
async def quick_batch_translate(cls,
                                content: Any,
                                api_key: str,
                                target_locales: List[str],
                                source_locale: Optional[str] = None,
                                api_url: str = "https://engine.lingo.dev",
                                fast: bool = True) -> List[Any]
```

Translates content into multiple locales without manual setup.

**Arguments**:

- `content` - Text string or mapping to translate for each locale.
- `api_key` - Lingo.dev API key to authenticate requests.
- `target_locales` - List of locale codes. Results maintain this order.
- `source_locale` - Optional source language code. When omitted the API
  may attempt to detect it.
- `api_url` - Lingo.dev engine base URL. Defaults to
  `"https://engine.lingo.dev"`.
- `fast` - Whether to enable the service's fast translation mode.
  

**Returns**:

  Translated content, one entry per `target_locales` item.
  

**Raises**:

- `ValueError` - If `content` is not a string or dictionary, or if a
  request is rejected by the API.
- `RuntimeError` - If the API indicates a failure or the request cannot
  be completed.
  

**Examples**:

    ```python
    variants = await LingoDotDevEngine.quick_batch_translate(
        "Hello world",
        api_key="api-key",
        target_locales=["es", "fr"],
    )
    # variants -> ["Hola mundo", "Bonjour le monde"]  (example output)

    localized_objects = await LingoDotDevEngine.quick_batch_translate(
        {"success": "Saved", "error": "Failed"},
        api_key="api-key",
        target_locales=["pt-BR", "it"],
        source_locale="en",
        fast=False,
    )
    # localized_objects -> [
    #     {"success": "Salvo", "error": "Falhou"},
    #     {"success": "Salvato", "error": "Non riuscito"},
    # ]  (example output)
    ```

