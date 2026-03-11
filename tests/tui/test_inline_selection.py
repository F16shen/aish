"""Tests for InlineSelectionWidget."""

import pytest

from aish.tui.types import SelectionState
from aish.tui.widgets import InlineSelectionWidget


class TestInlineSelectionWidget:
    """Test inline selection widget."""

    @pytest.fixture
    def widget(self):
        """Create a widget for testing."""
        return InlineSelectionWidget(max_visible=5)

    @pytest.fixture
    def sample_state(self):
        """Create a sample selection state."""
        return SelectionState(
            is_active=True,
            prompt="Select an option",
            title="Test Selection",
            options=[
                {"value": "1", "label": "Option 1"},
                {"value": "2", "label": "Option 2"},
                {"value": "3", "label": "Option 3"},
            ],
            selected_index=0,
            allow_cancel=True,
            allow_custom_input=False,
        )

    def test_init(self, widget):
        """Test widget initialization."""
        assert widget.max_visible == 5

    def test_render_empty_state(self, widget):
        """Test rendering empty state."""
        state = SelectionState(is_active=False)
        lines = widget.render(state)
        assert lines == []

    def test_render_active_state(self, widget, sample_state):
        """Test rendering active selection state."""
        lines = widget.render(sample_state)

        # Should have title, prompt, 3 options, and hint
        assert len(lines) == 6

        # Check title
        assert "[bold cyan]" in lines[0]
        assert "Test Selection" in lines[0]

        # Check prompt
        assert "[dim]" in lines[1]
        assert "Select an option" in lines[1]

        # Check first option is selected
        assert "[reverse bold]" in lines[2]
        assert "● Option 1" in lines[2]

        # Check second option is not selected
        assert "[dim]" in lines[3]
        assert "○ Option 2" in lines[3]

        # Check third option is not selected
        assert "[dim]" in lines[4]
        assert "○ Option 3" in lines[4]

        # Check hint
        assert "[gray]" in lines[5]
        assert "↑↓: Navigate" in lines[5]

    def test_render_with_custom_input_allowed(self, widget):
        """Test rendering with custom input allowed."""
        state = SelectionState(
            is_active=True,
            prompt="Select",
            options=[{"value": "1", "label": "One"}],
            allow_custom_input=True,
        )
        lines = widget.render(state)

        # Hint should include Tab option
        hint_line = lines[-1]
        assert "Tab: Custom input" in hint_line

    def test_render_without_cancel(self, widget):
        """Test rendering without cancel option."""
        state = SelectionState(
            is_active=True,
            prompt="Select",
            options=[{"value": "1", "label": "One"}],
            allow_cancel=False,
        )
        lines = widget.render(state)

        # Hint should not include Esc
        hint_line = lines[-1]
        assert "Esc" not in hint_line

    def test_get_visible_options_all_visible(self, widget, sample_state):
        """Test getting visible options when all fit."""
        visible = widget._get_visible_options(sample_state)
        assert len(visible) == 3

    def test_get_visible_options_windowed(self, sample_state):
        """Test getting visible options with windowing."""
        widget = InlineSelectionWidget(max_visible=2)

        # Create state with more options than max_visible
        state = SelectionState(
            is_active=True,
            prompt="Select",
            options=[
                {"value": "1", "label": "Option 1"},
                {"value": "2", "label": "Option 2"},
                {"value": "3", "label": "Option 3"},
                {"value": "4", "label": "Option 4"},
            ],
            selected_index=1,  # Second option selected
        )

        visible = widget._get_visible_options(state)

        # Should show window around selected index
        assert len(visible) == 2
        # First visible should be Option 1 (index 0)
        assert visible[0]["value"] == "1"
        assert visible[1]["value"] == "2"

    def test_get_height(self, widget, sample_state):
        """Test calculating height."""
        height = widget.get_height(sample_state)

        # Title (1) + Prompt (1) + Options (3) + Hint (1) + Spacing (1)
        # Widget.get_height counts: title + prompt + min(options, max_visible) + hint + spacing
        # For 3 options with max_visible=5: 1 + 1 + 3 + 1 + 1 = 7
        # But the actual implementation returns: title? + prompt? + min(options, max_visible) + hint + 1 spacing
        assert height == 7

    def test_get_height_empty(self, widget):
        """Test calculating height for empty state."""
        state = SelectionState(is_active=False)
        height = widget.get_height(state)
        assert height == 0

    def test_render_with_no_title(self, widget):
        """Test rendering without title."""
        state = SelectionState(
            is_active=True,
            prompt="Select",
            options=[{"value": "1", "label": "One"}],
            title="",
        )
        lines = widget.render(state)

        # First line should be prompt, not title
        assert "Select" in lines[0]

    def test_render_with_no_prompt(self, widget):
        """Test rendering without prompt."""
        state = SelectionState(
            is_active=True,
            prompt="",
            options=[{"value": "1", "label": "One"}],
            title="Test",
        )
        lines = widget.render(state)

        # First line should be title
        assert "[bold cyan]" in lines[0]
        assert "Test" in lines[0]
