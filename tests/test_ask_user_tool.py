import json
import sys
from unittest.mock import AsyncMock, patch

import pytest

from aish.config import ConfigModel
from aish.context_manager import ContextManager
from aish.llm import LLMCallbackResult, LLMSession
from aish.skills import SkillManager
from aish.tools.ask_user import AskUserTool
from aish.tools.result import ToolResult


def test_ask_user_tool_selected(monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)

    def request_choice(data):
        assert data["prompt"] == "pick one"
        assert data["default"] == "a"
        return "b", "selected"

    tool = AskUserTool(request_choice=request_choice)
    result = tool(
        prompt="pick one",
        options=[
            {"value": "a", "label": "A"},
            {"value": "b", "label": "B"},
        ],
        default="a",
    )

    assert result.ok is True
    payload = json.loads(result.output)
    assert payload["value"] == "b"
    assert payload["label"] == "B"
    assert payload["status"] == "selected"


def test_ask_user_tool_cancelled_pauses(monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)

    def request_choice(_data):
        return None, "cancelled"

    tool = AskUserTool(request_choice=request_choice)
    result = tool(
        prompt="pick one",
        options=[
            {"value": "a", "label": "A"},
            {"value": "b", "label": "B"},
        ],
        default="a",
    )

    assert result.ok is False
    assert result.meta.get("kind") == "user_input_required"
    assert result.meta.get("reason") == "cancelled"
    assert "continue with default" in result.output


def test_ask_user_tool_unavailable_pauses():
    # Ensure deterministic "unavailable" across environments.
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False, raising=False)
    tool = AskUserTool(request_choice=lambda _data: ("a", "selected"))
    result = tool(
        prompt="pick one",
        options=[
            {"value": "a", "label": "A"},
            {"value": "b", "label": "B"},
        ],
        default="a",
    )
    assert result.ok is False
    assert result.meta.get("kind") == "user_input_required"
    assert result.meta.get("reason") == "unavailable"
    monkeypatch.undo()


def test_ask_user_tool_custom_input_allowed(monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)

    def request_choice(_data):
        return "mango", "selected"

    tool = AskUserTool(request_choice=request_choice)
    result = tool(
        prompt="pick one",
        options=[
            {"value": "a", "label": "A"},
            {"value": "b", "label": "B"},
        ],
        allow_custom_input=True,
    )

    assert result.ok is True
    payload = json.loads(result.output)
    assert payload["value"] == "mango"
    assert payload["status"] == "custom"


@pytest.mark.anyio
async def test_handle_tool_calls_ask_user_user_input_required_breaks(monkeypatch):
    config = ConfigModel(model="test-model", api_key="test-key")
    session = LLMSession(config=config, skill_manager=SkillManager())
    context_manager = ContextManager()

    tool_calls = [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "ask_user", "arguments": "{}"},
        },
        {
            "id": "call_2",
            "type": "function",
            "function": {"name": "bash_exec", "arguments": "{\"code\":\"echo hi\"}"},
        },
    ]

    async def fake_pre_execute_tool(tool_name, _tool_args):
        if tool_name == "ask_user":
            return (
                LLMCallbackResult.APPROVE,
                ToolResult(
                    ok=False,
                    output="paused",
                    meta={"kind": "user_input_required", "reason": "cancelled"},
                ),
            )
        raise AssertionError("should not execute tool calls after ask_user pause")

    with patch.object(session, "pre_execute_tool", new=AsyncMock(side_effect=fake_pre_execute_tool)):
        tool_call_cancelled, output, _messages = await session._handle_tool_calls(
            tool_calls=tool_calls,
            context_manager=context_manager,
            system_message=None,
            output="",
        )

    assert tool_call_cancelled is True
    assert output == "paused"
