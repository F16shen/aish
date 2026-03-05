from __future__ import annotations

from aish.security.command_fallback import extract_explicit_paths


def test_extract_explicit_paths_plain_and_quoted_and_redirect() -> None:
    command = 'cp "/home/user/a b.txt" /tmp/out.txt && echo hi > /var/tmp/log.txt'
    paths = extract_explicit_paths(command)

    assert "/home/user/a b.txt" in paths
    assert "/tmp/out.txt" in paths
    assert "/var/tmp/log.txt" in paths


def test_extract_explicit_paths_ignores_relative_targets() -> None:
    command = "echo hi > out.txt && cat ./x"
    paths = extract_explicit_paths(command)

    assert paths == []
