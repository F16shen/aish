import json
from pathlib import Path

import httpx
import pytest

from aish.providers.github_copilot import (
    GITHUB_COPILOT_DEFAULT_BASE_URL,
    GitHubCopilotAuthState,
    GitHubCopilotAuthError,
    build_github_copilot_request,
    create_github_copilot_chat_completion,
    derive_github_copilot_api_base_url_from_runtime_token,
    load_github_copilot_auth,
    login_github_copilot_with_browser,
    persist_github_copilot_tokens,
    resolve_github_copilot_runtime_auth,
)
from aish.providers.oauth import OAuthTokens


def test_persist_and_load_github_copilot_auth(tmp_path):
    auth_path = tmp_path / "github-copilot-auth.json"

    persist_github_copilot_tokens(
        auth_path,
        tokens=OAuthTokens(
            access_token="ghu_test_123",
            token_type="bearer",
            scope="read:user",
        ),
    )

    auth = load_github_copilot_auth(auth_path)

    assert auth.auth_path == auth_path
    assert auth.github_token == "ghu_test_123"
    assert auth.token_type == "bearer"
    assert auth.scope == "read:user"


def test_derive_github_copilot_api_base_url_from_runtime_token_uses_proxy_endpoint():
    base_url = derive_github_copilot_api_base_url_from_runtime_token(
        "token;proxy-ep=https://proxy.copilot.example;"
    )

    assert base_url == "https://api.copilot.example"


@pytest.mark.anyio
async def test_resolve_github_copilot_runtime_auth_exchanges_and_persists_token(tmp_path):
    auth_path = tmp_path / "github-copilot-auth.json"
    auth_path.write_text(
        json.dumps({"provider": "github-copilot", "github_token": "ghu_test_123"}),
        encoding="utf-8",
    )
    auth = load_github_copilot_auth(auth_path)

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "token": "copilot-runtime;proxy-ep=https://proxy.copilot.example;",
                "expires_at": 2_000_000_000,
            },
        )
    )

    async with httpx.AsyncClient(transport=transport) as client:
        refreshed = await resolve_github_copilot_runtime_auth(auth, client=client)

    assert refreshed.runtime_token == "copilot-runtime;proxy-ep=https://proxy.copilot.example;"
    assert refreshed.runtime_api_base == "https://api.copilot.example"
    reloaded = load_github_copilot_auth(auth_path)
    assert reloaded.runtime_token == refreshed.runtime_token
    assert reloaded.runtime_api_base == refreshed.runtime_api_base


def test_build_github_copilot_request_strips_provider_prefix_and_passes_tools():
    request = build_github_copilot_request(
        model="github-copilot/gpt-4o",
        messages=[{"role": "user", "content": "hello"}],
        stream=False,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "bash_exec",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    )

    assert request["model"] == "gpt-4o"
    assert request["messages"][0]["content"] == "hello"
    assert request["tool_choice"] == "auto"


@pytest.mark.anyio
async def test_create_github_copilot_chat_completion_uses_runtime_token_and_chat_endpoint(
    tmp_path,
):
    auth_path = tmp_path / "github-copilot-auth.json"
    auth_path.write_text(
        json.dumps({"provider": "github-copilot", "github_token": "ghu_test_123"}),
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == httpx.URL("https://api.github.com/copilot_internal/v2/token"):
            assert request.headers["Authorization"] == "Bearer ghu_test_123"
            return httpx.Response(
                200,
                json={
                    "token": "copilot-runtime-token",
                    "expires_at": 2_000_000_000,
                },
            )

        assert request.url == httpx.URL(
            f"{GITHUB_COPILOT_DEFAULT_BASE_URL}/chat/completions"
        )
        assert request.headers["Authorization"] == "Bearer copilot-runtime-token"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "gpt-4o"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "hello from copilot"},
                        "finish_reason": "stop",
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            httpx,
            "AsyncClient",
            lambda *args, **kwargs: original_async_client(
                transport=transport,
                timeout=kwargs.get("timeout", 300.0),
            ),
        )
        result = await create_github_copilot_chat_completion(
            model="github-copilot/gpt-4o",
            messages=[{"role": "user", "content": "hello"}],
            auth_path=auth_path,
        )

    assert result["choices"][0]["message"]["content"] == "hello from copilot"


def test_github_copilot_browser_login_aliases_to_device_code(monkeypatch):
    expected = GitHubCopilotAuthState(auth_path=Path("/tmp/copilot-auth.json"), github_token="gh")
    calls: list[str] = []

    def fake_login(**kwargs):
        calls.append(kwargs["auth_path"])
        return expected

    monkeypatch.setattr(
        "aish.providers.github_copilot.login_github_copilot_with_device_code",
        fake_login,
    )

    result = login_github_copilot_with_browser(auth_path="/tmp/copilot-auth.json")

    assert result is expected
    assert calls == ["/tmp/copilot-auth.json"]


def test_load_github_copilot_auth_rejects_missing_token(tmp_path):
    auth_path = tmp_path / "github-copilot-auth.json"
    auth_path.write_text(json.dumps({"provider": "github-copilot"}), encoding="utf-8")

    with pytest.raises(GitHubCopilotAuthError):
        load_github_copilot_auth(auth_path)