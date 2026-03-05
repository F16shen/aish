from __future__ import annotations

import json

from aish.security import sandbox_worker
from aish.security.sandbox import SandboxUnavailableError


class _FakeResult:
    def __init__(self):
        self.exit_code = 0
        self.stdout = "ok"
        self.stderr = ""
        self.changes = []


def test_worker_returns_bad_request_on_invalid_json(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin.read", lambda: "{bad json")

    exit_code = sandbox_worker.main()

    assert exit_code == 0
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["reason"] == "bad_request"


def test_worker_maps_sandbox_unavailable(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.stdin.read",
        lambda: json.dumps(
            {
                "command": "echo ok",
                "cwd": "/",
                "repo_root": "/",
                "sim_uid": None,
                "sim_gid": None,
                "timeout_s": 10,
            },
            ensure_ascii=False,
        ),
    )

    class _Exec:
        def __init__(self, cfg):
            pass

        def simulate(self, *args, **kwargs):
            raise SandboxUnavailableError("overlay_mount_failed", details="boom")

    monkeypatch.setattr("aish.security.sandbox_worker.SandboxExecutor", _Exec)

    exit_code = sandbox_worker.main()

    assert exit_code == 0
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["ok"] is False
    assert payload["reason"] == "overlay_mount_failed"


def test_worker_success_payload(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.stdin.read",
        lambda: json.dumps(
            {
                "command": "echo ok",
                "cwd": "/",
                "repo_root": "/",
                "sim_uid": None,
                "sim_gid": None,
                "timeout_s": 10,
            },
            ensure_ascii=False,
        ),
    )

    class _Exec:
        def __init__(self, cfg):
            pass

        def simulate(self, *args, **kwargs):
            return _FakeResult()

    monkeypatch.setattr("aish.security.sandbox_worker.SandboxExecutor", _Exec)

    exit_code = sandbox_worker.main()

    assert exit_code == 0
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["result"]["exit_code"] == 0
