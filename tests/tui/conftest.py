"""TUI test fixtures."""

import pytest
from unittest.mock import Mock, patch

from aish.config import ConfigModel, TUISettings


@pytest.fixture
def tui_settings():
    """Create default TUI settings for testing."""
    return TUISettings(
        enabled=True,
        theme="dark",
        status_bar_height=1,
        notification_timeout=5.0,
        max_history_display=20,
        animation_fps=10,
        max_content_lines=100,
        show_time=True,
        show_cwd=True,
    )


@pytest.fixture
def tui_config(tui_settings):
    """Create a config model with TUI settings for testing."""
    return ConfigModel(
        model="test-model",
        tui=tui_settings,
    )


@pytest.fixture
def mock_shell(tui_config):
    """Create a mock shell instance for testing."""
    shell = Mock()
    shell.config = tui_config
    shell.logger = Mock()
    shell.history_manager = Mock()
    shell.env_manager = Mock()
    shell.env_manager.get_exported_vars.return_value = {}
    return shell


@pytest.fixture
def tui_app(tui_config, mock_shell):
    """Create a TUIApp instance for testing."""
    from aish.tui.app import TUIApp

    return TUIApp(tui_config, mock_shell)


@pytest.fixture
def mock_prompt_session():
    """Mock prompt_toolkit PromptSession for input testing."""
    with patch("aish.tui.widgets.input_bar.PromptSession") as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        yield mock_session
