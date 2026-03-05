"""Security utilities for AI Shell.

Important: avoid heavy imports at package import time.

This package is imported by system services like the privileged sandbox daemon.
Some interactive-shell dependencies (e.g. ``rich``) are only required by the
interactive UI and should not break sandboxd startup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .security_manager import SecurityDecision, SimpleSecurityManager
    from .security_policy import RiskLevel, SecurityPolicy


__all__ = [
    "RiskLevel",
    "SecurityPolicy",
    "load_policy",
    "SimpleSecurityManager",
    "SecurityDecision",
]


def __getattr__(name: str) -> Any:
    if name in {"RiskLevel", "SecurityPolicy", "load_policy"}:
        from . import security_policy

        return getattr(security_policy, name)

    if name in {"SimpleSecurityManager", "SecurityDecision"}:
        from . import security_manager

        return getattr(security_manager, name)

    raise AttributeError(name)
