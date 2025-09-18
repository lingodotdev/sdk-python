"""
Public entry point for the Lingo.dev Python SDK.

The package exposes :class:`~lingodotdev.engine.LingoDotDevEngine`, the
asynchronous client used to access the Lingo.dev localization API. Refer to the
engine module for detailed usage guidance.
"""

__version__ = "1.3.0"

from .engine import LingoDotDevEngine

__all__ = ["LingoDotDevEngine"]
