"""Public entry point for the Lingo.dev Python SDK.

The package exposes LingoDotDevEngine, the asynchronous client used to access
the Lingo.dev localization API. Refer to the engine module for detailed usage
guidance.

  async with LingoDotDevEngine({"api_key": "..."}) as engine:
      result = await engine.localize_text("Hello", {"target_locale": "es"})
"""

__version__ = "1.3.0"

from .engine import LingoDotDevEngine

__all__ = ["LingoDotDevEngine"]
