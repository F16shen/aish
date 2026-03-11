"""Content area widget for TUI."""

from typing import TYPE_CHECKING, Optional

from rich.console import RenderableType
from rich.text import Text

from aish.tui.types import ContentLine, ContentLineType

if TYPE_CHECKING:
    from aish.config import TUISettings


class ContentArea:
    """Scrollable content area displaying command output and AI responses."""

    def __init__(self, settings: "TUISettings"):
        """Initialize content area.

        Args:
            settings: TUI settings
        """
        self.settings = settings
        self.theme = settings.theme

        # Style mappings for different content types
        self._style_map = {
            ContentLineType.INPUT: "bold cyan",
            ContentLineType.OUTPUT: "",
            ContentLineType.ERROR: "bold red",
            ContentLineType.AI_RESPONSE: "green",
            ContentLineType.SYSTEM: "dim yellow",
            ContentLineType.COMMAND: "bold yellow",
        }

        # Prefix mappings for different content types
        self._prefix_map = {
            ContentLineType.INPUT: "$ ",
            ContentLineType.OUTPUT: "",
            ContentLineType.ERROR: "❌ ",
            ContentLineType.AI_RESPONSE: "🤖 ",
            ContentLineType.SYSTEM: "ℹ️ ",
            ContentLineType.COMMAND: "▶ ",
        }

    def render(
        self,
        lines: list[ContentLine],
        scroll_offset: int = 0,
        max_height: Optional[int] = None,
    ) -> RenderableType:
        """Render the content area.

        Args:
            lines: List of content lines
            scroll_offset: Scroll offset from bottom (0 = show latest)
            max_height: Maximum height in lines (None = auto)

        Returns:
            Renderable content
        """
        if not lines:
            return Text("(No content yet)", style="dim")

        # Calculate visible range
        if max_height is None:
            # Show all lines (will be constrained by layout)
            visible_lines = lines
        else:
            # Calculate visible range based on scroll offset
            total_lines = len(lines)
            end_idx = total_lines - scroll_offset
            start_idx = max(0, end_idx - max_height)
            visible_lines = lines[start_idx:end_idx]

        # Build text content
        text = Text()

        for i, line in enumerate(visible_lines):
            if i > 0:
                text.append("\n")

            # Add prefix
            prefix = self._prefix_map.get(line.line_type, "")
            style = self._style_map.get(line.line_type, "")

            text.append(prefix)
            text.append(line.text, style=style)

        return text

    def get_line_style(self, line_type: ContentLineType) -> str:
        """Get the style for a content line type.

        Args:
            line_type: Type of content line

        Returns:
            Rich style string
        """
        return self._style_map.get(line_type, "")

    def get_line_prefix(self, line_type: ContentLineType) -> str:
        """Get the prefix for a content line type.

        Args:
            line_type: Type of content line

        Returns:
            Prefix string
        """
        return self._prefix_map.get(line_type, "")
