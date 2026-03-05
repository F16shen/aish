from __future__ import annotations

from pathlib import Path
import io

from rich.console import Console

from aish.security.security_config import load_security_policy
from aish.security.security_manager import SimpleSecurityManager
from aish.security.security_policy import PolicyRule, RiskLevel, SecurityPolicy


def _quiet_console() -> Console:
    return Console(file=io.StringIO(), force_terminal=False, width=120)


def test_load_security_policy_ignores_sandbox_off_action_field(tmp_path: Path):
    policy_path = tmp_path / "security_policy.yaml"
    policy_path.write_text(
        "global:\n"
        "  enable_sandbox: false\n"
        "  sandbox_off_action: BLOCK\n"
        "rules: []\n",
        encoding="utf-8",
    )

    policy = load_security_policy(config_path=policy_path)
    assert policy.enable_sandbox is False
    assert not hasattr(policy, "sandbox_off_action")


def test_sandbox_fallback_high_blocks_ai_command_by_path_match_even_without_operation_check():
    policy = SecurityPolicy(
        enable_sandbox=False,
        rules=[
            PolicyRule(
                pattern="/etc/**",
                risk=RiskLevel.HIGH,
                operations={"DELETE"},
                rule_id="H-001",
            )
        ],
    )
    mgr = SimpleSecurityManager(
        policy=policy,
        console=_quiet_console(),
    )

    decision = mgr.decide("touch /etc/hosts", is_ai_command=True)
    assert decision.allow is False
    assert decision.require_confirmation is False
    assert decision.analysis.get("mode") == "command_fallback"


def test_sandbox_fallback_medium_requires_confirmation():
    policy = SecurityPolicy(
        enable_sandbox=False,
        rules=[
            PolicyRule(
                pattern="/home/**",
                risk=RiskLevel.MEDIUM,
                rule_id="M-001",
            )
        ],
    )
    mgr = SimpleSecurityManager(
        policy=policy,
        console=_quiet_console(),
    )

    decision = mgr.decide("rm -rf /home/lixin/a", is_ai_command=True)
    assert decision.allow is True
    assert decision.require_confirmation is True


def test_sandbox_fallback_no_path_allows_without_confirmation():
    policy = SecurityPolicy(
        enable_sandbox=False,
        rules=[],
    )
    mgr = SimpleSecurityManager(
        policy=policy,
        console=_quiet_console(),
    )

    decision = mgr.decide("echo hi", is_ai_command=True)
    assert decision.allow is True
    assert decision.require_confirmation is False


def test_non_ai_command_does_not_enter_command_fallback():
    policy = SecurityPolicy(
        enable_sandbox=False,
        rules=[
            PolicyRule(
                pattern="/etc/**",
                risk=RiskLevel.HIGH,
                rule_id="H-001",
            )
        ],
    )
    mgr = SimpleSecurityManager(
        policy=policy,
        console=_quiet_console(),
    )

    decision = mgr.decide("touch /etc/hosts", is_ai_command=False)
    assert decision.allow is True
    assert decision.require_confirmation is False
    assert decision.analysis.get("mode") == "sandbox"


def test_command_fallback_blacklist_mode_ls_with_system_path_is_low():
    policy = SecurityPolicy(
        enable_sandbox=False,
        rules=[
            PolicyRule(
                pattern="/etc/**",
                risk=RiskLevel.HIGH,
                rule_id="H-001",
            )
        ],
    )
    mgr = SimpleSecurityManager(policy=policy, console=_quiet_console())

    decision = mgr.decide("ls /etc", is_ai_command=True)

    assert decision.level == RiskLevel.LOW
    assert decision.allow is True
    assert decision.require_confirmation is False
    assert decision.analysis.get("matched_rules") == []


def test_command_fallback_blacklist_mode_rm_with_system_path_still_blocks():
    policy = SecurityPolicy(
        enable_sandbox=False,
        rules=[
            PolicyRule(
                pattern="/etc/**",
                risk=RiskLevel.HIGH,
                rule_id="H-001",
            )
        ],
    )
    mgr = SimpleSecurityManager(policy=policy, console=_quiet_console())

    decision = mgr.decide("rm -f /etc/passwd", is_ai_command=True)

    assert decision.level == RiskLevel.HIGH
    assert decision.allow is False
    assert decision.require_confirmation is False


def test_command_fallback_dd_raw_device_is_high_and_blocked():
    policy = SecurityPolicy(
        enable_sandbox=False,
        rules=[],
    )
    mgr = SimpleSecurityManager(policy=policy, console=_quiet_console())

    decision = mgr.decide("dd if=/dev/zero of=/dev/sda bs=1M", is_ai_command=True)

    assert decision.level == RiskLevel.HIGH
    assert decision.allow is False
    assert decision.require_confirmation is False
    reasons = decision.analysis.get("reasons") or []
    assert any("高危命令" in str(item) for item in reasons)


def test_fallback_invalid_rule_match_escalates_to_medium(tmp_path: Path):
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

    policy = load_security_policy(config_path=policy_path)
    mgr = SimpleSecurityManager(policy=policy, console=_quiet_console())

    decision = mgr.decide("rm -f /etc/passwd", is_ai_command=True)

    assert decision.level == RiskLevel.MEDIUM
    assert decision.allow is True
    assert decision.require_confirmation is True
    assert decision.analysis.get("matched_invalid_rule_ids") == ["H-001"]
    assert decision.analysis.get("matched_rules") == []
