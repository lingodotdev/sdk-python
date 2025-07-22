"""
LingoDotDevEngine implementation for Python SDK - Async version with httpx
"""

# mypy: disable-error-code=unreachable

import asyncio
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from nanoid import generate
from pydantic import BaseModel, Field, field_validator


class EngineConfig(BaseModel):
    """Configuration for the LingoDotDevEngine"""

    api_key: str
    api_url: str = "https://engine.lingo.dev"
    batch_size: int = Field(default=25, ge=1, le=250)
    ideal_batch_item_size: int = Field(default=250, ge=1, le=2500)

    @field_validator("api_url")
    @classmethod
    def validate_api_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("API URL must be a valid HTTP/HTTPS URL")
        return v


class LocalizationParams(BaseModel):
    """Parameters for localization requests"""

    source_locale: Optional[str] = None
    target_locale: str
    fast: Optional[bool] = None
    reference: Optional[Dict[str, Dict[str, Any]]] = None


class LingoDotDevEngine:
    """
    LingoDotDevEngine class for interacting with the LingoDotDev API
    A powerful localization engine that supports various content types including
    plain text, objects, chat sequences, and HTML documents.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Create a new LingoDotDevEngine instance

        Args:
            config: Configuration options for the Engine
        """
        self.config = EngineConfig(**config)
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _ensure_client(self):
        """Ensure the httpx client is initialized"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Authorization": f"Bearer {self.config.api_key}",
                },
                timeout=30.0,
            )

    async def close(self):
        """Close the httpx client"""
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
        """
        Localize content using the Lingo.dev API

        Args:
            payload: The content to be localized
            params: Localization parameters
            progress_callback: Optional callback function to report progress (0-100)
            concurrent: Whether to process chunks concurrently (faster but no progress tracking)

        Returns:
            Localized content
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
        """
        Localize a single chunk of content

        Args:
            source_locale: Source locale
            target_locale: Target locale
            payload: Payload containing the chunk to be localized
            workflow_id: Workflow ID for tracking
            fast: Whether to use fast mode

        Returns:
            Localized chunk
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
        """
        Extract payload chunks based on the ideal chunk size

        Args:
            payload: The payload to be chunked

        Returns:
            An array of payload chunks
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
        """
        Count words in a record or array

        Args:
            payload: The payload to count words in

        Returns:
            The total number of words
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
        """
        Localize a typical Python dictionary

        Args:
            obj: The object to be localized (strings will be extracted and translated)
            params: Localization parameters:
                - source_locale: The source language code (e.g., 'en')
                - target_locale: The target language code (e.g., 'es')
                - fast: Optional boolean to enable fast mode
            progress_callback: Optional callback function to report progress (0-100)
            concurrent: Whether to process chunks concurrently (faster but no progress tracking)

        Returns:
            A new object with the same structure but localized string values
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
        """
        Localize a single text string

        Args:
            text: The text string to be localized
            params: Localization parameters:
                - source_locale: The source language code (e.g., 'en')
                - target_locale: The target language code (e.g., 'es')
                - fast: Optional boolean to enable fast mode
            progress_callback: Optional callback function to report progress (0-100)

        Returns:
            The localized text string
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
        """
        Localize a text string to multiple target locales

        Args:
            text: The text string to be localized
            params: Localization parameters:
                - source_locale: The source language code (e.g., 'en')
                - target_locales: A list of target language codes (e.g., ['es', 'fr'])
                - fast: Optional boolean to enable fast mode

        Returns:
            A list of localized text strings
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
        """
        Localize a chat sequence while preserving speaker names

        Args:
            chat: Array of chat messages, each with 'name' and 'text' properties
            params: Localization parameters:
                - source_locale: The source language code (e.g., 'en')
                - target_locale: The target language code (e.g., 'es')
                - fast: Optional boolean to enable fast mode
            progress_callback: Optional callback function to report progress (0-100)

        Returns:
            Array of localized chat messages with preserved structure
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
        """
        Detect the language of a given text

        Args:
            text: The text to analyze

        Returns:
            A locale code (e.g., 'en', 'es', 'fr')
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
        """
        Get information about the current API key

        Returns:
            Dictionary with 'email' and 'id' keys, or None if not authenticated
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
        """
        Localize multiple objects concurrently

        Args:
            objects: List of objects to localize
            params: Localization parameters

        Returns:
            List of localized objects
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
        """
        Quick one-off translation without manual context management.
        Automatically handles the async context manager.

        Args:
            content: Text string or dict to translate
            api_key: Your Lingo.dev API key
            target_locale: Target language code (e.g., 'es', 'fr')
            source_locale: Source language code (optional, auto-detected if None)
            api_url: API endpoint URL
            fast: Enable fast mode for quicker translations

        Returns:
            Translated content (same type as input)

        Example:
            # Translate text
            result = await LingoDotDevEngine.quick_translate(
                "Hello world",
                "your-api-key",
                "es"
            )

            # Translate object
            result = await LingoDotDevEngine.quick_translate(
                {"greeting": "Hello", "farewell": "Goodbye"},
                "your-api-key",
                "es"
            )
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
        """
        Quick batch translation to multiple target locales.
        Automatically handles the async context manager.

        Args:
            content: Text string or dict to translate
            api_key: Your Lingo.dev API key
            target_locales: List of target language codes (e.g., ['es', 'fr', 'de'])
            source_locale: Source language code (optional, auto-detected if None)
            api_url: API endpoint URL
            fast: Enable fast mode for quicker translations

        Returns:
            List of translated content (one for each target locale)

        Example:
            results = await LingoDotDevEngine.quick_batch_translate(
                "Hello world",
                "your-api-key",
                ["es", "fr", "de"]
            )
            # Results: ["Hola mundo", "Bonjour le monde", "Hallo Welt"]
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
