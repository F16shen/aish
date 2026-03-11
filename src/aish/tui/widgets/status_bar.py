"""Status bar widget for TUI."""

from typing import TYPE_CHECKING

from rich.console import RenderableType
from rich.text import Text

from aish.tui.types import StatusInfo

if TYPE_CHECKING:
    from aish.config import TUISettings


class StatusBar:
    """Status bar widget displaying model, mode, time, and processing state."""

    def __init__(self, settings: "TUISettings"):
        """Initialize status bar.

        Args:
            settings: TUI settings
        """
        self.settings = settings
        self.theme = settings.theme

    def render(self, status: StatusInfo, hint: str = "") -> RenderableType:
        """Render the status bar.

        Args:
            status: Current status information
            hint: Optional hint message to display in status bar (right side)

        Returns:
            Renderable content
        """
        parts = []

        # Model
        if status.model:
            model_display = status.model
            # Shorten model name if too long
            if len(model_display) > 20:
                model_display = model_display[:17] + "..."
            parts.append(("model", f"[Model: {model_display}]"))

        # Mode (PTY/AI) - unified gray style
        parts.append(("mode", f"[Mode: {status.mode}]", "dim"))

        # Processing indicator - unified gray style
        if status.is_processing:
            parts.append(("processing", "[Processing...]", "dim"))

        # Current working directory
        if status.cwd and self.settings.show_cwd:
            cwd_display = status.cwd
            # Shorten path if too long
            if len(cwd_display) > 30:
                cwd_display = "..." + cwd_display[-27:]
            parts.append(("cwd", f"[{cwd_display}]", "dim"))

        # Hint (right side) - shows tips like "Use ';' to ask AI"
        if hint:
            parts.append(("hint", f"  [{hint}]", "dim"))

        # Build text
        text = Text()
        for i, part in enumerate(parts):
            if i > 0:
                text.append(" ")
            if len(part) == 3:
                key, content, style = part
                text.append(content, style=style)
            else:
                key, content = part
                text.append(content)

        # Apply theme styling
        if self.theme == "dark":
            bg_style = "on #1e1e1e"
        else:
            bg_style = "on #f0f0f0"

        text.stylize(bg_style)

        return text
