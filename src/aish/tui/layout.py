"""Layout utilities for TUI."""

from rich.layout import Layout
from rich.panel import Panel


def create_main_layout(
    status_height: int = 1,
    notification_height: int = 1,
    input_height: int = 1,
) -> Layout:
    """Create the main TUI layout structure.

    Args:
        status_height: Height of status bar in lines
        notification_height: Height of notification bar in lines
        input_height: Height of input bar in lines

    Returns:
        Configured Layout instance
    """
    layout = Layout(name="root")

    layout.split(
        Layout(name="status", size=status_height),
        Layout(name="content", ratio=1),  # Takes remaining space
        Layout(name="input", size=input_height),
        Layout(name="notification", size=notification_height),
    )

    return layout


def make_panel(content, title: str = "", style: str = "") -> Panel:
    """Create a styled panel.

    Args:
        content: Panel content
        title: Optional panel title
        style: Panel border style

    Returns:
        Panel instance
    """
    return Panel(
        content,
        title=title,
        style=style,
        padding=0,
        expand=True,
    )
