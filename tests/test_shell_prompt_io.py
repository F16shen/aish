from __future__ import annotations

import time
from unittest.mock import patch

from aish.llm import LLMCallbackResult, LLMEvent, LLMEventType
from aish.shell_enhanced.shell_prompt_io import handle_ask_user_required


class _DummyShell:
    def __init__(self) -> None:
        self.current_live = None

    def _stop_animation(self) -> None:
        return

    def _finalize_content_preview(self) -> None:
        return

    def _compute_ask_user_max_visible(
        self,
        total_options: int,
        term_rows: int,
        allow_custom_input: bool,
        max_visible_cap: int = 12,
    ) -> int:
        _ = term_rows, allow_custom_input, max_visible_cap
        return max(1, min(total_options, 3))

    def _read_terminal_size(self) -> tuple[int, int]:
        return (24, 80)

    def _is_ui_resize_enabled(self) -> bool:
        return False


def test_handle_ask_user_required_sets_selected_value():
    shell = _DummyShell()
    event = LLMEvent(
        event_type=LLMEventType.ASK_USER_REQUIRED,
        data={
            "prompt": "Pick one",
            "options": [
                {"value": "opt1", "label": "Option 1"},
                {"value": "opt2", "label": "Option 2"},
            ],
            "default": "opt1",
            "allow_cancel": True,
            "allow_custom_input": True,
            "custom_prompt": "This is intentionally very long to avoid squeezing input space",
        },
        timestamp=time.time(),
    )

    class _DummyApp:
        def __init__(self, *args, **kwargs) -> None:
            class _Input:
                @staticmethod
                def flush() -> None:
                    return

                @staticmethod
                def flush_keys() -> None:
                    return

            self.input = _Input()

        def run(self, in_thread: bool = True) -> str:
            _ = in_thread
            return "opt2"

    with patch("prompt_toolkit.Application", _DummyApp):
        result = handle_ask_user_required(shell, event)

    assert result == LLMCallbackResult.CONTINUE
    assert event.data.get("selected_value") == "opt2"
