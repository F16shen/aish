from __future__ import annotations

from aish.config import ConfigModel
from aish.shell import AIShell
from aish.shell_enhanced.shell_types import InputIntent
from aish.skills import SkillManager


def make_shell() -> AIShell:
    skill_manager = SkillManager()
    skill_manager.load_all_skills()
    return AIShell(config=ConfigModel(model="test-model"), skill_manager=skill_manager)


def test_route_ai_prefix():
    shell = make_shell()
    route = shell._input_router.route("; explain ls")
    assert route.intent == InputIntent.AI


def test_route_help_command():
    shell = make_shell()
    route = shell._input_router.route("cd --help")
    assert route.intent == InputIntent.HELP
    assert route.help_command == "cd"


def test_route_operator_command():
    shell = make_shell()
    route = shell._input_router.route("cd /tmp && pwd")
    assert route.intent == InputIntent.OPERATOR_COMMAND


def test_route_special_command():
    shell = make_shell()
    route = shell._input_router.route("exit")
    assert route.intent == InputIntent.SPECIAL_COMMAND
    assert route.command_name == "exit"


def test_route_builtin_command():
    shell = make_shell()
    route = shell._input_router.route("history 5")
    assert route.intent == InputIntent.BUILTIN_COMMAND


def test_route_parse_error_falls_to_command_or_ai():
    shell = make_shell()
    route = shell._input_router.route('echo "unterminated')
    assert route.intent == InputIntent.COMMAND_OR_AI
    assert route.parse_error is True


def test_route_regular_command_or_ai_with_parts():
    shell = make_shell()
    route = shell._input_router.route("ls -la")
    assert route.intent == InputIntent.COMMAND_OR_AI
    assert route.parse_error is False
    assert route.cmd_parts[:1] == ["ls"]
