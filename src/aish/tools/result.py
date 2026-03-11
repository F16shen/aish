from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolResult:
    ok: bool
    output: str = ""
    code: Optional[int] = None
    meta: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)

    def render_for_llm(self) -> str:
        return self.output
