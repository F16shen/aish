"""Types for setup wizard flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProviderOption:
    key: str
    label: str
    api_base: Optional[str]
    env_key: Optional[str]
    allow_custom_model: bool = True
    requires_api_base: bool = False


@dataclass
class ConnectivityResult:
    """Layer 1: Model connectivity check result."""

    ok: bool
    error: Optional[str] = None
    timed_out: bool = False
    cancelled: bool = False
    latency_ms: Optional[int] = None


@dataclass
class ToolSupportResult:
    """Layer 2: Tool calling capability check result."""

    supports: Optional[bool]
    error: Optional[str] = None
    timed_out: bool = False
    cancelled: bool = False
