"""
LingoDotDevEngine implementation for Python SDK
"""
# mypy: disable-error-code=unreachable

from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urljoin

import requests
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
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {self.config.api_key}",
            }
        )

    def _localize_raw(
        self,
        payload: Dict[str, Any],
        params: LocalizationParams,
        progress_callback: Optional[
            Callable[[int, Dict[str, str], Dict[str, str]], None]
        ] = None,
    ) -> Dict[str, str]:
        """
        Localize content using the Lingo.dev API

        Args:
            payload: The content to be localized
            params: Localization parameters
            progress_callback: Optional callback function to report progress (0-100)

        Returns:
            Localized content
        """
        chunked_payload = self._extract_payload_chunks(payload)
        processed_payload_chunks = []

        workflow_id = generate()

        for i, chunk in enumerate(chunked_payload):
            percentage_completed = round(((i + 1) / len(chunked_payload)) * 100)

            processed_payload_chunk = self._localize_chunk(
                params.source_locale,
                params.target_locale,
                {"data": chunk, "reference": params.reference},
                workflow_id,
                params.fast or False,
            )

            if progress_callback:
                progress_callback(percentage_completed, chunk, processed_payload_chunk)

            processed_payload_chunks.append(processed_payload_chunk)

        result = {}
        for chunk in processed_payload_chunks:
            result.update(chunk)

        return result

    def _localize_chunk(
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
        url = urljoin(self.config.api_url, "/i18n")

        request_data = {
            "params": {"workflowId": workflow_id, "fast": fast},
            "locale": {"source": source_locale, "target": target_locale},
            "data": payload["data"],
        }

        if payload.get("reference"):
            request_data["reference"] = payload["reference"]

        try:
            response = self.session.post(url, json=request_data)

            if not response.ok:
                if 500 <= response.status_code < 600:
                    raise RuntimeError(
                        f"Server error ({response.status_code}): {response.reason}. "
                        f"{response.text}. This may be due to temporary service issues."
                    )
                elif response.status_code == 400:
                    raise ValueError(f"Invalid request: {response.reason}")
                else:
                    raise RuntimeError(response.text)

            json_response = response.json()

            # Handle streaming errors
            if not json_response.get("data") and json_response.get("error"):
                raise RuntimeError(json_response["error"])

            return json_response.get("data") or {}

        except requests.RequestException as e:
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

    def localize_object(
        self,
        obj: Dict[str, Any],
        params: Dict[str, Any],
        progress_callback: Optional[
            Callable[[int, Dict[str, str], Dict[str, str]], None]
        ] = None,
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

        Returns:
            A new object with the same structure but localized string values
        """
        localization_params = LocalizationParams(**params)
        return self._localize_raw(obj, localization_params, progress_callback)

    def localize_text(
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

        response = self._localize_raw(
            {"text": text}, localization_params, wrapped_progress_callback
        )

        return response.get("text", "")

    def batch_localize_text(self, text: str, params: Dict[str, Any]) -> List[str]:
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

        responses = []
        for target_locale in target_locales:
            response = self.localize_text(
                text,
                {
                    "source_locale": source_locale,
                    "target_locale": target_locale,
                    "fast": fast,
                },
            )
            responses.append(response)

        return responses

    def localize_chat(
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

        localized = self._localize_raw(
            {"chat": chat}, localization_params, wrapped_progress_callback
        )

        # The API returns the localized chat in the same structure
        chat_result = localized.get("chat")
        if chat_result and isinstance(chat_result, list):
            return chat_result

        return []

    def recognize_locale(self, text: str) -> str:
        """
        Detect the language of a given text

        Args:
            text: The text to analyze

        Returns:
            A locale code (e.g., 'en', 'es', 'fr')
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")

        url = urljoin(self.config.api_url, "/recognize")

        try:
            response = self.session.post(url, json={"text": text})

            if not response.ok:
                if 500 <= response.status_code < 600:
                    raise RuntimeError(
                        f"Server error ({response.status_code}): {response.reason}. "
                        "This may be due to temporary service issues."
                    )
                raise RuntimeError(f"Error recognizing locale: {response.reason}")

            json_response = response.json()
            return json_response.get("locale") or ""

        except requests.RequestException as e:
            raise RuntimeError(f"Request failed: {str(e)}")

    def whoami(self) -> Optional[Dict[str, str]]:
        """
        Get information about the current API key

        Returns:
            Dictionary with 'email' and 'id' keys, or None if not authenticated
        """
        url = urljoin(self.config.api_url, "/whoami")

        try:
            response = self.session.post(url)

            if response.ok:
                payload = response.json()
                if payload.get("email"):
                    return {"email": payload["email"], "id": payload["id"]}

            if 500 <= response.status_code < 600:
                raise RuntimeError(
                    f"Server error ({response.status_code}): {response.reason}. "
                    "This may be due to temporary service issues."
                )

            return None

        except requests.RequestException as e:
            # Return None for network errors, but re-raise server errors
            if "Server error" in str(e):
                raise
            return None
