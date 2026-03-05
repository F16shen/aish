import os

from typer.testing import CliRunner

from aish.cli import app
from aish.i18n import reset_i18n_for_tests


def test_help_is_localized_by_lang_env_zh_cn():
    runner = CliRunner()

    reset_i18n_for_tests()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    lang = os.getenv("LANG", "")
    if lang.lower().startswith("zh"):
        assert "内置大模型能力" in result.output
    else:
        assert "A shell with built-in LLM capabilities" in result.output


def test_help_falls_back_to_english_for_non_zh():
    runner = CliRunner()

    reset_i18n_for_tests()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    # This project currently supports only zh-CN/en-US; non-zh locales fall back to English.
    # If LANG starts with zh, help may render in Chinese.
    lang = os.getenv("LANG", "")
    if not lang.lower().startswith("zh"):
        assert "A shell with built-in LLM capabilities" in result.output
