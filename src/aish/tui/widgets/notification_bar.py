"""Notification bar widget for TUI."""

import time
from typing import TYPE_CHECKING

from rich.console import RenderableType
from rich.text import Text

from aish.tui.types import Notification

if TYPE_CHECKING:
    from aish.config import TUISettings


class NotificationBar:
    """Notification bar widget displaying info, warning, and error messages."""

    def __init__(self, settings: "TUISettings"):
        """Initialize notification bar.

        Args:
            settings: TUI settings
        """
        self.settings = settings
        self.theme = settings.theme

        # Style mappings for notification levels
        self._style_map = {
            "info": ("ℹ️", "cyan"),
            "warning": ("⚠️", "yellow"),
            "error": ("❌", "bold red"),
        }

    def render(self, notifications: list[Notification]) -> RenderableType:
        """Render the notification bar.

        Args:
            notifications: List of active notifications

        Returns:
            Renderable content
        """
        if not notifications:
            # Empty notification bar
            return Text("", style="dim")

        # Show the most recent notification
        latest = notifications[-1]
        icon, style = self._style_map.get(latest.level, ("•", ""))

        # Calculate remaining time
        elapsed = time.time() - latest.timestamp
        remaining = max(0, latest.timeout - elapsed)

        text = Text()
        text.append(f"{icon} ")
        text.append(latest.message, style=style)

        # Show remaining time for auto-dismiss
        if remaining > 0:
            text.append(f" ({remaining:.0f}s)", style="dim")

        return text

    def render_all(self, notifications: list[Notification]) -> RenderableType:
        """Render all notifications (for notification history).

        Args:
            notifications: List of all notifications

        Returns:
            Renderable content
        """
        if not notifications:
            return Text("(No notifications)", style="dim")

        text = Text()
        for i, notif in enumerate(notifications):
            if i > 0:
                text.append("\n")

            icon, style = self._style_map.get(notif.level, ("•", ""))
            text.append(f"{icon} ")
            text.append(notif.message, style=style)

        return text
