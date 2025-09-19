"""
Async client implementation for the Lingo.dev localization service.

This module houses :class:`LingoDotDevEngine` alongside supporting data models
used to validate configuration and localization parameters.
"""

# mypy: disable-error-code=unreachable

import asyncio
import re
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from nanoid import generate
from pydantic import BaseModel, Field, validator

_BCP47_TAG_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")


class EngineConfig(BaseModel):
    """Stores and validates runtime configuration for :class:`LingoDotDevEngine`.

    Attributes:
        api_key: Secret token used to authenticate with the Lingo.dev API.
        api_url: Base endpoint for the localization engine. Defaults to
            ``https://engine.lingo.dev``.
        batch_size: Maximum number of top-level entries to send in a single
            localization request (between 1 and 250 inclusive).
        ideal_batch_item_size: Target word count per request before payloads are
            split into multiple batches (between 1 and 2500 inclusive).
    """

    api_key: str
    api_url: str = "https://engine.lingo.dev"
    batch_size: int = Field(default=25, ge=1, le=250)
    ideal_batch_item_size: int = Field(default=250, ge=1, le=2500)

    @validator("api_url")
    @classmethod
    def validate_api_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("API URL must be a valid HTTP/HTTPS URL")
        return v


class LocalizationParams(BaseModel):
    """Request parameters accepted by localization operations.

    These values are serialized directly into API requests after validation.

    Attributes:
        source_locale: Optional BCP 47 language code representing the source
            language. When omitted the API attempts automatic detection.
        target_locale: Required BCP 47 language code for the desired translation
            target.
        fast: Optional flag that enables the service's low-latency translation
            mode at the cost of some quality safeguards.
        reference: Optional nested mapping of existing translations that
            provides additional context to the engine.
    """

    source_locale: Optional[str] = None
    target_locale: str
    fast: Optional[bool] = None
    reference: Optional[Dict[str, Dict[str, Any]]] = None

    @validator("source_locale", "target_locale")
    @classmethod
    def validate_locale(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not _BCP47_TAG_RE.fullmatch(v):
            raise ValueError(
                "Locale values must be valid BCP 47 language tags (example: 'en', 'en-US')."
            )
        return v


class LingoDotDevEngine:
    """Asynchronous client for the Lingo.dev localization API.

    The engine manages an :class:`httpx.AsyncClient`, handles chunking and
    batching of content, and exposes helper coroutines for translating strings,
    structured objects, and chat transcripts. Instances can be reused or
    managed via an async context manager::

        async with LingoDotDevEngine({"api_key": "..."}) as engine:
            await engine.localize_text("Hello", {"target_locale": "es"})

    All localization methods are ``async`` and must be awaited.
    """

    def __init__(self, config: Dict[str, Any]):
        """Instantiate the engine with configuration data.

        Args:
            config: Mapping of values understood by
                :class:`EngineConfig`. At minimum an ``api_key`` entry must
                be supplied.

        Raises:
            ValueError: If the supplied configuration fails validation.
        """
        self.config = EngineConfig(**config)
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Open the HTTP session when entering an async context.

        Returns:
            LingoDotDevEngine: The active engine instance.
        """
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release resources acquired during the async context."""
        await self.close()

    async def _ensure_client(self):
        """Create an :class:`httpx.AsyncClient` if one is not already available."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Authorization": f"Bearer {self.config.api_key}",
                },
                timeout=60.0,
            )

    async def close(self):
        """Close the HTTP client if it has been created."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _localize_raw(
        self,
        payload: Dict[str, Any],
        params: LocalizationParams,
        progress_callback: Optional[
            Callable[[int, Dict[str, str], Dict[str, str]], None]
        ] = None,
        concurrent: bool = False,
    ) -> Dict[str, str]:
        """Submit a localization request for the provided payload.

        The payload is split into chunks based on the configured limits and the
        resulting pieces are localized sequentially or concurrently. Sequential
        mode enables progress reporting while concurrent mode maximizes
        throughput.

        Args:
            payload: Mapping or structured content to be localized.
            params: Pre-validated localization parameters.
            progress_callback: Optional callable invoked after each chunk is
                localized. Receives the percentage completed, the source chunk,
                and the localized chunk.
            concurrent: When ``True`` and no ``progress_callback`` is supplied,
                chunks are processed concurrently.

        Returns:
            Dictionary containing the merged localized chunks.

        Raises:
            RuntimeError: If the API responds with an error.
            ValueError: If the API rejects the payload.
        """
        await self._ensure_client()
        chunked_payload = self._extract_payload_chunks(payload)
        workflow_id = generate()

        if concurrent and not progress_callback:
            # Process chunks concurrently for better performance
            tasks = []
            for chunk in chunked_payload:
                task = self._localize_chunk(
                    params.source_locale,
                    params.target_locale,
                    {"data": chunk, "reference": params.reference},
                    workflow_id,
                    params.fast or False,
                )
                tasks.append(task)

            processed_payload_chunks = await asyncio.gather(*tasks)
        else:
            # Process chunks sequentially (supports progress tracking)
            processed_payload_chunks = []
            for i, chunk in enumerate(chunked_payload):
                percentage_completed = round(((i + 1) / len(chunked_payload)) * 100)

                processed_payload_chunk = await self._localize_chunk(
                    params.source_locale,
                    params.target_locale,
                    {"data": chunk, "reference": params.reference},
                    workflow_id,
                    params.fast or False,
                )

                if progress_callback:
                    progress_callback(
                        percentage_completed, chunk, processed_payload_chunk
                    )

                processed_payload_chunks.append(processed_payload_chunk)

        result = {}
        for chunk in processed_payload_chunks:
            result.update(chunk)

        return result

    async def _localize_chunk(
        self,
        source_locale: Optional[str],
        target_locale: str,
        payload: Dict[str, Any],
        workflow_id: str,
        fast: bool,
    ) -> Dict[str, str]:
        """Translate a single payload chunk through the ``/i18n`` endpoint.

        Args:
            source_locale: Optional source locale used for the request.
            target_locale: Target locale requested from the API.
            payload: Dictionary containing the chunk under the ``data`` key and
                optional ``reference`` metadata.
            workflow_id: Identifier shared across chunks that belong to the
                same localization workflow.
            fast: Whether to request the service's fast translation mode.

        Returns:
            A dictionary representing the localized chunk returned by the API.

        Raises:
            RuntimeError: If the API responds with an error status or signals a
                streaming error.
            ValueError: If the API reports an invalid request (HTTP 400).
        """
        await self._ensure_client()
        assert self._client is not None  # Type guard for mypy
        url = urljoin(self.config.api_url, "/i18n")

        request_data = {
            "params": {"workflowId": workflow_id, "fast": fast},
            "locale": {"source": source_locale, "target": target_locale},
            "data": payload["data"],
        }

        if payload.get("reference"):
            request_data["reference"] = payload["reference"]

        try:
            response = await self._client.post(url, json=request_data)

            if not response.is_success:
                if 500 <= response.status_code < 600:
                    raise RuntimeError(
                        f"Server error ({response.status_code}): {response.reason_phrase}. "
                        f"{response.text}. This may be due to temporary service issues."
                    )
                elif response.status_code == 400:
                    raise ValueError(
                        f"Invalid request ({response.status_code}): {response.reason_phrase}"
                    )
                else:
                    raise RuntimeError(response.text)

            json_response = response.json()

            # Handle streaming errors
            if not json_response.get("data") and json_response.get("error"):
                raise RuntimeError(json_response["error"])

            return json_response.get("data") or {}

        except httpx.RequestError as e:
            raise RuntimeError(f"Request failed: {str(e)}")

    def _extract_payload_chunks(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split a payload into smaller dictionaries based on configured limits.

        The method iterates through the payload in insertion order, grouping
        keys until the number of words or items would exceed the configured
        thresholds. Each chunk is suitable for sending directly to the API.

        Args:
            payload: Mapping to be divided into localization chunks.

        Returns:
            List of dictionaries representing individual request chunks.
        """
        result = []
        current_chunk = {}
        current_chunk_item_count = 0

        for key, value in payload.items():
            current_chunk[key] = value
            current_chunk_item_count += 1

            current_chunk_size = self._count_words_in_record(current_chunk)

            if (
                current_chunk_size > self.config.ideal_batch_item_size
                or current_chunk_item_count >= self.config.batch_size
                or key == list(payload.keys())[-1]
            ):

                result.append(current_chunk)
                current_chunk = {}
                current_chunk_item_count = 0

        return result

    def _count_words_in_record(self, payload: Any) -> int:
        """Recursively count whitespace-delimited words within a payload.

        Args:
            payload: String, mapping, list, or other primitive values to count.

        Returns:
            Total number of words discovered within string values.
        """
        if isinstance(payload, list):
            return sum(self._count_words_in_record(item) for item in payload)
        elif isinstance(payload, dict):
            return sum(self._count_words_in_record(item) for item in payload.values())
        elif isinstance(payload, str):
            return len([word for word in payload.strip().split() if word])
        else:
            return 0

    async def localize_object(
        self,
        obj: Dict[str, Any],
        params: Dict[str, Any],
        progress_callback: Optional[
            Callable[[int, Dict[str, str], Dict[str, str]], None]
        ] = None,
        concurrent: bool = False,
    ) -> Dict[str, Any]:
        """Localize every string value contained in a mapping.

        Args:
            obj: Mapping whose string leaves should be translated.
            params: Dictionary of options accepted by
                :class:`LocalizationParams`.
            progress_callback: Optional callable invoked with progress updates
                (0-100) alongside the source and localized chunks. If provided,
                leave ``concurrent`` as ``False`` (the default) because progress
                updates are unavailable in concurrent mode.
            concurrent: When ``True`` the payload chunks are processed
                concurrently and no progress updates are emitted.

        Returns:
            A dictionary mirroring ``obj`` with localized string values.

        Raises:
            RuntimeError: If the API responds with an error.
            ValueError: If the API rejects the request.

        Examples:
            .. code-block:: python

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
        """
        localization_params = LocalizationParams(**params)
        return await self._localize_raw(
            obj, localization_params, progress_callback, concurrent
        )

    async def localize_text(
        self,
        text: str,
        params: Dict[str, Any],
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> str:
        """Localize a single text string.

        Args:
            text: The text to translate.
            params: Dictionary of options accepted by
                :class:`LocalizationParams`.
            progress_callback: Optional callable receiving the percentage
                complete (0-100).

        Returns:
            The localized text string.

        Raises:
            RuntimeError: If the API responds with an error.
            ValueError: If the API rejects the request.

        Examples:
            .. code-block:: python

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
        """
        localization_params = LocalizationParams(**params)

        def wrapped_progress_callback(
            progress: int, source_chunk: Dict[str, str], processed_chunk: Dict[str, str]
        ):
            if progress_callback:
                progress_callback(progress)

        response = await self._localize_raw(
            {"text": text}, localization_params, wrapped_progress_callback
        )

        return response.get("text", "")

    async def batch_localize_text(self, text: str, params: Dict[str, Any]) -> List[str]:
        """Localize a single text string into multiple target locales.

        Args:
            text: The text string to translate.
            params: Dictionary of options accepted by
                :class:`LocalizationParams` plus a ``target_locales`` list.

        Returns:
            List of localized strings ordered to match ``target_locales``.

        Raises:
            ValueError: If ``target_locales`` is missing or the API rejects a
                request.
            RuntimeError: If the API responds with an error.

        Examples:
            .. code-block:: python

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
        """
        if "target_locales" not in params:
            raise ValueError("target_locales is required")

        target_locales = params["target_locales"]
        source_locale = params.get("source_locale")
        fast = params.get("fast", False)

        # Create tasks for concurrent execution
        tasks = []
        for target_locale in target_locales:
            task = self.localize_text(
                text,
                {
                    "source_locale": source_locale,
                    "target_locale": target_locale,
                    "fast": fast,
                },
            )
            tasks.append(task)

        # Execute all localization tasks concurrently
        responses = await asyncio.gather(*tasks)
        return responses

    async def localize_chat(
        self,
        chat: List[Dict[str, str]],
        params: Dict[str, Any],
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> List[Dict[str, str]]:
        """Localize a chat transcript while preserving speaker metadata.

        Args:
            chat: Sequence of chat messages. Each item must include ``name`` and
                ``text`` keys.
            params: Dictionary of options accepted by
                :class:`LocalizationParams`.
            progress_callback: Optional callable receiving percentage updates
                (0-100) while the transcript is localized.

        Returns:
            List of localized chat messages in the same order as ``chat``. If
            the API omits chat data an empty list is returned.

        Raises:
            ValueError: If any message in ``chat`` omits the required keys.
            RuntimeError: If the API responds with an error.

        Examples:
            .. code-block:: python

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
        """
        # Validate chat format
        for message in chat:
            if "name" not in message or "text" not in message:
                raise ValueError(
                    "Each chat message must have 'name' and 'text' properties"
                )

        localization_params = LocalizationParams(**params)

        def wrapped_progress_callback(
            progress: int, source_chunk: Dict[str, str], processed_chunk: Dict[str, str]
        ):
            if progress_callback:
                progress_callback(progress)

        localized = await self._localize_raw(
            {"chat": chat}, localization_params, wrapped_progress_callback
        )

        # The API returns the localized chat in the same structure
        chat_result = localized.get("chat")
        if chat_result and isinstance(chat_result, list):
            return chat_result

        return []

    async def recognize_locale(self, text: str) -> str:
        """Detect the language of the supplied text via the ``/recognize`` endpoint.

        Args:
            text: Non-empty string to analyse.

        Returns:
            Locale code reported by the API (for example ``"en"``) or an empty
            string when the service cannot determine a locale.

        Raises:
            ValueError: If ``text`` is empty or only whitespace.
            RuntimeError: If the request fails or the API reports an error.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        await self._ensure_client()
        assert self._client is not None  # Type guard for mypy
        url = urljoin(self.config.api_url, "/recognize")

        try:
            response = await self._client.post(url, json={"text": text})

            if not response.is_success:
                if 500 <= response.status_code < 600:
                    raise RuntimeError(
                        f"Server error ({response.status_code}): {response.reason_phrase}. "
                        "This may be due to temporary service issues."
                    )
                raise RuntimeError(
                    f"Error recognizing locale: {response.reason_phrase}"
                )

            json_response = response.json()
            return json_response.get("locale") or ""

        except httpx.RequestError as e:
            raise RuntimeError(f"Request failed: {str(e)}")

    async def whoami(self) -> Optional[Dict[str, str]]:
        """Retrieve account metadata associated with the current API key.

        Returns:
            Dictionary containing ``email`` and ``id`` keys when available, or
            ``None`` if the key is unauthenticated or a recoverable network
            error occurs.

        Raises:
            RuntimeError: If the service reports a server-side error.
        """
        await self._ensure_client()
        assert self._client is not None  # Type guard for mypy
        url = urljoin(self.config.api_url, "/whoami")

        try:
            response = await self._client.post(url)

            if response.is_success:
                payload = response.json()
                if payload.get("email"):
                    return {"email": payload["email"], "id": payload["id"]}

            if 500 <= response.status_code < 600:
                raise RuntimeError(
                    f"Server error ({response.status_code}): {response.reason_phrase}. "
                    "This may be due to temporary service issues."
                )

            return None

        except httpx.RequestError as e:
            # Return None for network errors, but re-raise server errors
            if "Server error" in str(e):
                raise
            return None

    async def batch_localize_objects(
        self, objects: List[Dict[str, Any]], params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Localize multiple mapping objects concurrently.

        Args:
            objects: List of objects whose string values should be translated.
            params: Dictionary of options accepted by
                :class:`LocalizationParams`, shared across all objects.

        Returns:
            List of localized objects preserving the order of ``objects``.

        Raises:
            RuntimeError: If the API responds with an error.
            ValueError: If the API rejects a request.
        """
        tasks = []
        for obj in objects:
            task = self.localize_object(obj, params, concurrent=True)
            tasks.append(task)

        return await asyncio.gather(*tasks)

    @classmethod
    async def quick_translate(
        cls,
        content: Any,
        api_key: str,
        target_locale: str,
        source_locale: Optional[str] = None,
        api_url: str = "https://engine.lingo.dev",
        fast: bool = True,
    ) -> Any:
        """Translate content without managing an engine instance manually.

        The helper opens an :class:`LingoDotDevEngine` using the supplied
        configuration, performs the translation, and automatically closes the
        underlying HTTP client.

        Args:
            content: Text string or mapping to translate. The returned value
                matches the type of ``content``.
            api_key: Lingo.dev API key to authenticate the request.
            target_locale: Target language code for the translation.
            source_locale: Optional source language code. When omitted the API
                may attempt to detect it.
            api_url: Lingo.dev engine base URL. Defaults to
                ``"https://engine.lingo.dev"``.
            fast: Whether to enable the service's fast translation mode.

        Returns:
            Translated content with the same type as ``content``.

        Raises:
            ValueError: If ``content`` is not a string or dictionary, or if the
                service rejects the request.
            RuntimeError: If the API indicates a failure or the request cannot
                be completed.

        Examples:
            .. code-block:: python

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
        """
        config = {
            "api_key": api_key,
            "api_url": api_url,
        }

        async with cls(config) as engine:
            params = {
                "source_locale": source_locale,
                "target_locale": target_locale,
                "fast": fast,
            }

            if isinstance(content, str):
                return await engine.localize_text(content, params)
            elif isinstance(content, dict):
                return await engine.localize_object(content, params, concurrent=True)
            else:
                raise ValueError("Content must be a string or dictionary")

    @classmethod
    async def quick_batch_translate(
        cls,
        content: Any,
        api_key: str,
        target_locales: List[str],
        source_locale: Optional[str] = None,
        api_url: str = "https://engine.lingo.dev",
        fast: bool = True,
    ) -> List[Any]:
        """Translate content into multiple locales without manual setup.

        Args:
            content: Text string or mapping to translate for each locale.
            api_key: Lingo.dev API key to authenticate requests.
            target_locales: List of locale codes. Results maintain this order.
            source_locale: Optional source language code. When omitted the API
                may attempt to detect it.
            api_url: Lingo.dev engine base URL. Defaults to
                ``"https://engine.lingo.dev"``.
            fast: Whether to enable the service's fast translation mode.

        Returns:
            List of translated content, one entry per ``target_locales`` item.

        Raises:
            ValueError: If ``content`` is not a string or dictionary, or if a
                request is rejected by the API.
            RuntimeError: If the API indicates a failure or the request cannot
                be completed.

        Examples:
            .. code-block:: python

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
        """
        config = {
            "api_key": api_key,
            "api_url": api_url,
        }

        async with cls(config) as engine:
            if isinstance(content, str):
                batch_params = {
                    "source_locale": source_locale,
                    "target_locales": target_locales,
                    "fast": fast,
                }
                return await engine.batch_localize_text(content, batch_params)
            elif isinstance(content, dict):
                # For objects, run concurrent translations to each target locale
                tasks = []
                for target_locale in target_locales:
                    task_params = {
                        "source_locale": source_locale,
                        "target_locale": target_locale,
                        "fast": fast,
                    }
                    task = engine.localize_object(content, task_params, concurrent=True)
                    tasks.append(task)
                return await asyncio.gather(*tasks)
            else:
                raise ValueError("Content must be a string or dictionary")
