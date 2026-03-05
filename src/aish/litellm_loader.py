"""Shared LiteLLM loading helpers.

Centralizes lazy import, quiet flags, and optional background preload so
different modules don't duplicate import/cache logic.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

_SENTINEL = object()
_cached_litellm: object = _SENTINEL
_preload_thread: Optional[threading.Thread] = None


def _configure_litellm(litellm: object) -> None:
    """Best-effort reduce LiteLLM log/debug noise."""
    litellm_logger = logging.getLogger("litellm")
    if litellm_logger.level < logging.WARNING:
        litellm_logger.setLevel(logging.WARNING)

    for attr in ("suppress_debug_info", "disable_debug_info"):
        if hasattr(litellm, attr):
            try:
                setattr(litellm, attr, True)
            except Exception:
                pass

    if hasattr(litellm, "set_verbose"):
        try:
            setattr(litellm, "set_verbose", False)
        except Exception:
            pass


def load_litellm() -> object | None:
    """Import LiteLLM once and return cached module (or None if unavailable)."""
    global _cached_litellm

    if _cached_litellm is not _SENTINEL:
        return _cached_litellm

    t = _preload_thread
    if t is not None and t.is_alive() and t is not threading.current_thread():
        t.join()
        if _cached_litellm is not _SENTINEL:
            return _cached_litellm

    try:
        import litellm
    except ImportError:
        _cached_litellm = None
        return None

    _configure_litellm(litellm)
    _cached_litellm = litellm
    return litellm


def preload_litellm() -> None:
    """Start daemon preload thread once; no-op if already loaded/preloading."""
    global _preload_thread

    if _preload_thread is not None:
        return
    if _cached_litellm is not _SENTINEL:
        return
    _preload_thread = threading.Thread(target=load_litellm, daemon=True)
    _preload_thread.start()
