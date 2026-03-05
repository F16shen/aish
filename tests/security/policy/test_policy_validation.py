from __future__ import annotations

import logging
from pathlib import Path

from aish.security.security_config import load_security_policy


def test_invalid_risk_rule_is_logged_and_marked_invalid(tmp_path: Path, caplog) -> None:
    policy_path = tmp_path / "security_policy.yaml"
    policy_path.write_text(
        "global:\n"
        "  enable_sandbox: false\n"
        "rules:\n"
        "  - id: H-001\n"
        "    path: ['/etc/**']\n"
        "    risk: MIDUEM\n",
        encoding="utf-8",
    )

    caplog.set_level(logging.WARNING)
    policy = load_security_policy(config_path=policy_path)

    assert len(policy.validation_issues) == 1
    issue = policy.validation_issues[0]
    assert issue.rule_id == "H-001"
    assert issue.field == "risk"
    assert issue.value == "MIDUEM"
    assert len(policy.invalid_fallback_rules) == 1
    assert policy.invalid_fallback_rules[0].rule_id == "H-001"

    assert "invalid rule ignored" in caplog.text
    assert "rule_id=H-001" in caplog.text
