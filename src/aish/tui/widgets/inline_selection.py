"""Inline selection widget for TUI - displays options above status bar."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aish.tui.types import SelectionState


class InlineSelectionWidget:
    """Widget for inline selection UI above status bar.

    This widget renders a compact selection interface that appears
    above the status bar, using up/down arrows for navigation.
    """

    def __init__(self, max_visible: int = 5):
        """Initialize inline selection widget.

        Args:
            max_visible: Maximum number of options to display at once
        """
        self.max_visible = max_visible

    def render(self, state: SelectionState) -> list[str]:
        """Render selection state as list of lines.

        Args:
            state: Current selection state

        Returns:
            List of formatted strings, one per line
        """
        if not state.is_active or not state.options:
            return []

        lines = []

        # Add title if available
        if state.title:
            lines.append(f"[bold cyan]{state.title}[/bold cyan]")

        # Add prompt
        if state.prompt:
            lines.append(f"[dim]{state.prompt}[/dim]")

        # Get visible options
        visible_options = self._get_visible_options(state)

        for idx, option in enumerate(visible_options):
            value = option.get("value", "")
            label = option.get("label", value)

            # Get the actual index in the full options list
            actual_index = state.options.index(option)
            is_selected = actual_index == state.selected_index

            # Style based on selection state
            if is_selected:
                # Selected option - use reverse style for highlight
                lines.append(f"[reverse bold]● {label}[/reverse bold]")
            else:
                # Unselected option
                lines.append(f"[dim]○ {label}[/dim]")

        # Add hint
        hint = self._get_hint(state)
        if hint:
            lines.append(f"[gray]{hint}[/gray]")

        return lines

    def _get_visible_options(self, state: SelectionState) -> list[dict]:
        """Get visible options centered around current selection.

        Args:
            state: Current selection state

        Returns:
            List of option dictionaries that should be visible
        """
        options = state.options
        selected = state.selected_index

        if len(options) <= self.max_visible:
            return options

        # Calculate window around selected item
        half_window = self.max_visible // 2
        start_idx = max(0, selected - half_window)
        end_idx = min(len(options), start_idx + self.max_visible)

        # Adjust if we're near the end
        if end_idx - start_idx < self.max_visible:
            start_idx = max(0, end_idx - self.max_visible)

        return options[start_idx:end_idx]

    def _get_hint(self, state: SelectionState) -> str:
        """Get hint text for selection.

        Args:
            state: Current selection state

        Returns:
            Hint text string
        """
        parts = []

        # Navigation hints
        parts.append("↑↓: Navigate")

        # Confirm hint
        parts.append("Enter: Confirm")

        # Cancel hint
        if state.allow_cancel:
            parts.append("Esc: Cancel")

        # Custom input hint
        if state.allow_custom_input:
            parts.append("Tab: Custom input")

        return " | ".join(parts)

    def get_height(self, state: SelectionState) -> int:
        """Calculate the height needed for rendering.

        Args:
            state: Current selection state

        Returns:
            Number of lines needed for rendering
        """
        if not state.is_active or not state.options:
            return 0

        height = 0

        # Title
        if state.title:
            height += 1

        # Prompt
        if state.prompt:
            height += 1

        # Options (limited by max_visible)
        height += min(len(state.options), self.max_visible)

        # Hint
        height += 1

        # Spacing
        height += 1

        return height
