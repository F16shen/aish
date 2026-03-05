from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fnmatch import fnmatch
from pathlib import Path
from typing import List, Optional

from .sandbox_types import FsChange, SandboxResult

from ..i18n import t


class RiskLevel(str, Enum):
    """统一的三档风险等级。

    - LOW:   低风险，一般为只读操作或小范围写入，可直接执行；
    - MEDIUM:中风险，可能有较大影响，需要用户确认后执行；
    - HIGH:  高风险，例如触碰敏感路径或大规模破坏，默认阻断。
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class PolicyRule:
    """单条路径风险规则。

    对用户来说，规则只需要描述路径模式 + 风险等级 + （可选）说明。
    """

    pattern: str
    risk: RiskLevel
    description: Optional[str] = None

    operations: Optional[set[str]] = None
    exclude: Optional[list[str]] = None
    rule_id: Optional[str] = None
    name: Optional[str] = None
    reason: Optional[str] = None
    confirm_message: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass(frozen=True)
class PolicyValidationIssue:
    rule_id: str
    field: str
    value: str
    message: str


@dataclass(frozen=True)
class InvalidFallbackRule:
    pattern: str
    rule_id: str
    exclude: list[str] | None = None


@dataclass
class SecurityPolicy:
    """基于路径匹配的安全策略配置。"""

    # v2：单一开关
    enable_sandbox: bool
    rules: List[PolicyRule]

    default_risk_level: RiskLevel = RiskLevel.LOW
    audit_enabled: bool = False
    audit_log_path: Optional[str] = None
    validation_issues: list[PolicyValidationIssue] = field(default_factory=list)
    invalid_fallback_rules: list[InvalidFallbackRule] = field(default_factory=list)

    @staticmethod
    def default() -> "SecurityPolicy":
        return SecurityPolicy(enable_sandbox=False, rules=list(_DEFAULT_RULES))

    def match(self, path: str, operation: Optional[str]) -> Optional[PolicyRule]:
        """按顺序匹配 (path, operation)，返回第一条命中的规则。

        - operation 为 None 时，仅做路径匹配；
        - rule.operations 存在时需要包含该 operation 才算命中；
        - rule.exclude 存在时，命中 exclude 的路径将被排除。

        TODO: 支持 READ 等非写操作的可靠观测与匹配。
        """

        op = operation.upper() if operation else None

        for rule in self.rules:
            if not fnmatch(path, rule.pattern):
                continue

            if rule.exclude:
                if any(fnmatch(path, ex) for ex in rule.exclude):
                    continue

            if op is not None and rule.operations is not None:
                if op not in rule.operations:
                    continue

            return rule

        return None


_DEFAULT_RULES: List[PolicyRule] = [
    PolicyRule(
        pattern="/**/security_policy.yaml",
        risk=RiskLevel.HIGH,
        description="Security policy file is protected",
        operations={"WRITE", "DELETE"},
        rule_id="H-SEC-001",
        name="Protect security policy",
        reason="Security policy file should not be modified by AI commands",
        confirm_message="Security policy file is protected and cannot be modified by AI commands.",
        suggestion="Edit the security policy file manually if needed.",
    )
]


def load_policy(config_path: Optional[Path] = None) -> SecurityPolicy:
    """
    加载安全策略配置。
    """

    # 延迟导入，避免循环依赖（security_config 需要引用本模块的数据结构）
    from .security_config import load_security_policy

    return load_security_policy(config_path=config_path)


# ---------------------------------------------------------------------------
# AI 风险评估（迁移自 ai_risk_engine.py）
# ---------------------------------------------------------------------------


@dataclass
class AiRiskAssessment:
    """针对 AI 命令的风险评估结果。"""

    level: RiskLevel
    reasons: List[str]
    changes: List[FsChange]


class AiRiskEngine:
    """基于沙箱结果和 SecurityPolicy 计算风险等级。"""

    def __init__(self, policy: SecurityPolicy) -> None:
        self._policy = policy

    def _normalize_path(self, path: str) -> str:
        """将 FsChange.path 规范化为以 "/" 开头的逻辑路径。"""

        if not path:
            return "/"
        if path.startswith("/"):
            return path
        return "/" + path.lstrip("/")

    def assess(self, command: str, sandbox_result: SandboxResult) -> AiRiskAssessment:  # noqa: ARG002
        """根据沙箱执行结果和策略评估本次 AI 命令的风险等级。"""

        changes = sandbox_result.changes or []
        if not changes:
            return AiRiskAssessment(
                level=self._policy.default_risk_level,
                reasons=[t("security.ai_risk.no_fs_changes")],
                changes=[],
            )

        high_hits: list[tuple[FsChange, str]] = []
        medium_hits: list[tuple[FsChange, str]] = []
        low_hits: list[tuple[FsChange, str]] = []
        unmatched: list[FsChange] = []

        for ch in changes:
            logical_path = self._normalize_path(ch.path)

            op: str
            if ch.kind == "deleted":
                op = "DELETE"
            else:
                # created/modified 视为 WRITE
                op = "WRITE"

            rule = self._policy.match(logical_path, op)
            if rule is None:
                unmatched.append(ch)
                continue

            if rule.risk == RiskLevel.HIGH:
                high_hits.append((ch, logical_path))
            elif rule.risk == RiskLevel.MEDIUM:
                medium_hits.append((ch, logical_path))
            else:
                low_hits.append((ch, logical_path))

        if high_hits:
            level = RiskLevel.HIGH
        elif medium_hits:
            level = RiskLevel.MEDIUM
        elif low_hits:
            level = RiskLevel.LOW
        else:
            level = self._policy.default_risk_level

        reasons: List[str] = []
        if high_hits:
            reasons.append(
                t("security.ai_risk.high_hits", count=len(high_hits)),
            )
        if medium_hits:
            reasons.append(
                t("security.ai_risk.medium_hits", count=len(medium_hits)),
            )
        if not (high_hits or medium_hits):
            reasons.append(
                t("security.ai_risk.low_or_unmatched_hits", count=len(changes)),
            )

        preview_changes = (high_hits or medium_hits or low_hits)[:3]
        if preview_changes:
            preview_paths = ", ".join(p for _ch, p in preview_changes)
            reasons.append(t("security.ai_risk.preview_paths", paths=preview_paths))

        result = AiRiskAssessment(level=level, reasons=reasons, changes=changes)

        return result


__all__ = [
    "RiskLevel",
    "PolicyRule",
    "PolicyValidationIssue",
    "InvalidFallbackRule",
    "SecurityPolicy",
    "load_policy",
    "AiRiskAssessment",
    "AiRiskEngine",
]
