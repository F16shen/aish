from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
import re
import shlex

from .security_policy import InvalidFallbackRule, PolicyRule, RiskLevel, SecurityPolicy


_INLINE_REDIRECT_RE = re.compile(r"^(?P<op>>>?|[12]>>?)(?P<target>/.+)$")
_BLACKLIST_COMMANDS = {
    "rm",
    "rmdir",
    "unlink",
    "shred",
    "mv",
    "cp",
    "touch",
    "tee",
    "chmod",
    "chown",
    "chgrp",
    "dd",
}
_DD_DANGEROUS_TARGET_RE = re.compile(r"^of=/dev/(?:sd[a-z]\d*|nvme\d+n\d+(?:p\d+)?|vd[a-z]\d*|xvd[a-z]\d*|mmcblk\d+(?:p\d+)?)$")


def _risk_rank(level: RiskLevel) -> int:
    if level == RiskLevel.HIGH:
        return 3
    if level == RiskLevel.MEDIUM:
        return 2
    return 1


def extract_explicit_paths(command: str) -> list[str]:
    """Extract explicit absolute paths from command text.

    Supported forms (MVP):
    - plain absolute paths: /etc/hosts
    - quoted absolute paths: "/home/user/a b" or '/tmp/a'
    - redirect targets after > and >>
    """

    candidates: list[str] = []
    seen: set[str] = set()

    try:
        tokens = shlex.split(command, posix=True)
    except Exception:
        tokens = command.split()

    redirect_ops = {">", ">>", "1>", "1>>", "2>", "2>>"}

    for index, token in enumerate(tokens):
        if token.startswith("/") and token not in seen:
            seen.add(token)
            candidates.append(token)

        if token in redirect_ops and index + 1 < len(tokens):
            target = tokens[index + 1]
            if target.startswith("/") and target not in seen:
                seen.add(target)
                candidates.append(target)
            continue

        inline = _INLINE_REDIRECT_RE.match(token)
        if inline:
            target = inline.group("target")
            if target.startswith("/") and target not in seen:
                seen.add(target)
                candidates.append(target)

    return candidates


@dataclass(frozen=True)
class FallbackRuleHit:
    path: str
    rule_id: str | None
    rule_name: str | None
    risk: RiskLevel
    reason: str | None


@dataclass(frozen=True)
class CommandFallbackResult:
    level: RiskLevel
    paths: list[str]
    hits: list[FallbackRuleHit]
    invalid_rule_ids: list[str]
    blacklist_triggered: bool
    dangerous_command_triggered: bool


def _base_command(tokens: list[str]) -> str:
    if not tokens:
        return ""

    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "sudo":
            index += 1
            while index < len(tokens) and tokens[index].startswith("-"):
                index += 1
            continue
        if "=" in token and not token.startswith("/") and token.find("=") > 0:
            index += 1
            continue
        return token

    return ""


def _is_blacklist_triggered(command: str, tokens: list[str]) -> bool:
    base_cmd = _base_command(tokens)
    if base_cmd in _BLACKLIST_COMMANDS:
        return True
    if base_cmd == "sed" and "-i" in tokens:
        return True
    if ">" in tokens or ">>" in tokens or "1>" in tokens or "1>>" in tokens or "2>" in tokens or "2>>" in tokens:
        return True
    for token in tokens:
        if _INLINE_REDIRECT_RE.match(token):
            return True
    return False


def _is_dangerous_command_triggered(tokens: list[str]) -> bool:
    base_cmd = _base_command(tokens)
    if base_cmd != "dd":
        return False

    for token in tokens:
        if _DD_DANGEROUS_TARGET_RE.match(token):
            return True
    return False


class CommandFallbackEvaluator:
    """Evaluate fallback risk from command text when sandbox is unavailable.

    This evaluator intentionally ignores operation type (WRITE/DELETE) and only
    uses explicit path matches from command text.
    """

    def __init__(self, policy: SecurityPolicy) -> None:
        self._policy = policy

    def _match_rules(self, path: str) -> list[PolicyRule]:
        matched: list[PolicyRule] = []

        for rule in self._policy.rules:
            if not fnmatch(path, rule.pattern):
                continue
            if rule.exclude and any(fnmatch(path, ex) for ex in rule.exclude):
                continue
            matched.append(rule)

        return matched

    def _match_invalid_rules(self, path: str) -> list[InvalidFallbackRule]:
        matched: list[InvalidFallbackRule] = []

        for rule in self._policy.invalid_fallback_rules:
            if not fnmatch(path, rule.pattern):
                continue
            if rule.exclude and any(fnmatch(path, ex) for ex in rule.exclude):
                continue
            matched.append(rule)

        return matched

    def assess(self, command: str) -> CommandFallbackResult:
        try:
            tokens = shlex.split(command, posix=True)
        except Exception:
            tokens = command.split()

        blacklist_triggered = _is_blacklist_triggered(command, tokens)
        dangerous_triggered = _is_dangerous_command_triggered(tokens)

        if dangerous_triggered:
            return CommandFallbackResult(
                level=RiskLevel.HIGH,
                paths=extract_explicit_paths(command),
                hits=[],
                invalid_rule_ids=[],
                blacklist_triggered=True,
                dangerous_command_triggered=True,
            )

        if not blacklist_triggered:
            return CommandFallbackResult(
                level=RiskLevel.LOW,
                paths=[],
                hits=[],
                invalid_rule_ids=[],
                blacklist_triggered=False,
                dangerous_command_triggered=False,
            )

        paths = extract_explicit_paths(command)
        if not paths:
            return CommandFallbackResult(
                level=RiskLevel.LOW,
                paths=[],
                hits=[],
                invalid_rule_ids=[],
                blacklist_triggered=True,
                dangerous_command_triggered=False,
            )

        hits: list[FallbackRuleHit] = []
        highest = RiskLevel.LOW
        invalid_rule_ids: set[str] = set()

        for path in paths:
            for rule in self._match_rules(path):
                hits.append(
                    FallbackRuleHit(
                        path=path,
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        risk=rule.risk,
                        reason=rule.reason,
                    )
                )
                if _risk_rank(rule.risk) > _risk_rank(highest):
                    highest = rule.risk

            for invalid in self._match_invalid_rules(path):
                invalid_rule_ids.add(invalid.rule_id)

        if invalid_rule_ids and _risk_rank(highest) < _risk_rank(RiskLevel.MEDIUM):
            highest = RiskLevel.MEDIUM

        if not hits:
            return CommandFallbackResult(
                level=highest,
                paths=paths,
                hits=[],
                invalid_rule_ids=sorted(invalid_rule_ids),
                blacklist_triggered=True,
                dangerous_command_triggered=False,
            )

        return CommandFallbackResult(
            level=highest,
            paths=paths,
            hits=hits,
            invalid_rule_ids=sorted(invalid_rule_ids),
            blacklist_triggered=True,
            dangerous_command_triggered=False,
        )


__all__ = [
    "FallbackRuleHit",
    "CommandFallbackResult",
    "CommandFallbackEvaluator",
    "extract_explicit_paths",
]
