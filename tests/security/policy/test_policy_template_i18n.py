from aish.i18n import reset_i18n_for_tests
from aish.security import security_config


def test_policy_template_is_zh_when_lang_is_zh(monkeypatch):
    monkeypatch.setenv("LANG", "zh_CN.UTF-8")
    reset_i18n_for_tests()
    tpl = security_config._get_empty_policy_template()
    assert "全局默认行为配置" in tpl


def test_policy_template_is_en_when_lang_is_en(monkeypatch):
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    reset_i18n_for_tests()
    tpl = security_config._get_empty_policy_template()
    assert "global default behavior" in tpl
