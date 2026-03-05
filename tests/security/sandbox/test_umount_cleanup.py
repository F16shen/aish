from __future__ import annotations

from pathlib import Path

from aish.security.sandbox import SandboxConfig, SandboxExecutor


class _FakeProc:
    def __init__(self, returncode: int, stderr: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr


def _make_executor() -> SandboxExecutor:
    return SandboxExecutor(SandboxConfig(repo_root=Path("/")))


def test_umount_busy_falls_back_to_lazy_and_succeeds(monkeypatch):
    executor = _make_executor()
    calls: list[list[str]] = []

    def fake_run_cmd(cmd, **kwargs):
        calls.append(list(cmd))
        if cmd[:2] == ["umount", "-l"]:
            return _FakeProc(0, "")
        return _FakeProc(1, "umount: target is busy.")

    monkeypatch.setattr("aish.security.sandbox.run_cmd", fake_run_cmd)

    executor._umount(Path("/tmp/aish-sandbox-x/merged/var"))

    assert len(calls) == 2
    assert calls[0][0] == "umount"
    assert calls[0][1] != "-l"
    assert calls[1][:2] == ["umount", "-l"]


def test_umount_busy_lazy_also_fails_prints_warning(monkeypatch, capsys):
    executor = _make_executor()

    def fake_run_cmd(cmd, **kwargs):
        if cmd[:2] == ["umount", "-l"]:
            return _FakeProc(1, "umount: lazy umount failed")
        return _FakeProc(1, "umount: target is busy.")

    monkeypatch.setattr("aish.security.sandbox.run_cmd", fake_run_cmd)

    target = Path("/tmp/aish-sandbox-x/merged/var")
    executor._umount(target)

    captured = capsys.readouterr()
    assert f"failed to umount {target}" in captured.err
