from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import httpx

from ..config import get_default_aish_data_dir
from .interface import ProviderAuthConfig
from .oauth import OAuthProviderSpec, OAuthTokens, login_with_standard_device_code

GITHUB_COPILOT_PROVIDER = "github-copilot"
GITHUB_COPILOT_DEFAULT_MODEL = "gpt-4o"
GITHUB_COPILOT_CLIENT_ID = "Iv1.b507a08c87ecfe98"
GITHUB_COPILOT_SCOPE = "read:user"
GITHUB_COPILOT_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_COPILOT_DEVICE_CODE_URL = "https://github.com/login/device/code"
GITHUB_COPILOT_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_COPILOT_RUNTIME_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"
GITHUB_COPILOT_DEFAULT_BASE_URL = "https://api.individual.githubcopilot.com"
GITHUB_COPILOT_RUNTIME_TOKEN_LEEWAY_SECONDS = 300

GITHUB_COPILOT_OAUTH_PROVIDER = OAuthProviderSpec(
    provider_id=GITHUB_COPILOT_PROVIDER,
    display_name="GitHub Copilot",
    client_id=GITHUB_COPILOT_CLIENT_ID,
    scope=GITHUB_COPILOT_SCOPE,
    authorize_url=GITHUB_COPILOT_AUTHORIZE_URL,
    token_url=GITHUB_COPILOT_ACCESS_TOKEN_URL,
    device_authorization_url=GITHUB_COPILOT_DEVICE_CODE_URL,
)


class GitHubCopilotAuthError(RuntimeError):
    pass


@dataclass
class GitHubCopilotAuthState:
    auth_path: Path
    github_token: str
    token_type: str | None = None
    scope: str | None = None
    runtime_token: str | None = None
    runtime_token_expires_at: int | None = None
    runtime_api_base: str | None = None

    def has_valid_runtime_token(
        self, *, leeway_seconds: int = GITHUB_COPILOT_RUNTIME_TOKEN_LEEWAY_SECONDS
    ) -> bool:
        if not self.runtime_token or self.runtime_token_expires_at is None:
            return False
        return int(time.time() * 1000) < (
            self.runtime_token_expires_at - (leeway_seconds * 1000)
        )


def is_github_copilot_model(model: str | None) -> bool:
    return bool(
        model and model.strip().lower().startswith(f"{GITHUB_COPILOT_PROVIDER}/")
    )


def strip_github_copilot_prefix(model: str) -> str:
    if is_github_copilot_model(model):
        return model.split("/", 1)[1].strip()
    return model.strip()


def resolve_github_copilot_auth_path(
    explicit_path: str | os.PathLike[str] | None = None,
) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser()

    env_path = os.getenv("AISH_GITHUB_COPILOT_AUTH_PATH")
    if env_path:
        return Path(env_path).expanduser()

    return get_default_aish_data_dir() / "github-copilot-auth.json"


def load_github_copilot_auth(
    auth_path: str | os.PathLike[str] | None = None,
) -> GitHubCopilotAuthState:
    path = resolve_github_copilot_auth_path(auth_path)
    if not path.exists():
        raise GitHubCopilotAuthError(
            "GitHub Copilot auth not found. Run `aish models auth login --provider github-copilot` first."
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise GitHubCopilotAuthError(
            f"Failed to read GitHub Copilot auth file: {path}"
        ) from exc

    github_token = _coerce_str(payload.get("github_token"))
    if not github_token:
        raise GitHubCopilotAuthError(
            "GitHub Copilot auth is incomplete. Re-run `aish models auth login --provider github-copilot`."
        )

    runtime = payload.get("runtime")
    runtime_payload = runtime if isinstance(runtime, dict) else {}
    return GitHubCopilotAuthState(
        auth_path=path,
        github_token=github_token,
        token_type=_coerce_str(payload.get("token_type")) or None,
        scope=_coerce_str(payload.get("scope")) or None,
        runtime_token=_coerce_str(runtime_payload.get("token")) or None,
        runtime_token_expires_at=_coerce_int(runtime_payload.get("expires_at")),
        runtime_api_base=_coerce_str(runtime_payload.get("api_base")) or None,
    )


def persist_github_copilot_tokens(
    auth_path: str | os.PathLike[str],
    *,
    tokens: OAuthTokens,
) -> None:
    if not tokens.access_token:
        raise GitHubCopilotAuthError(
            "GitHub Copilot login succeeded, but GitHub did not return an access token."
        )

    _persist_github_copilot_auth(
        Path(auth_path),
        github_token=tokens.access_token,
        token_type=tokens.token_type,
        scope=tokens.scope,
    )


def login_github_copilot_with_device_code(
    *,
    auth_path: str | os.PathLike[str] | None = None,
    notify=None,
    **_ignored: Any,
) -> GitHubCopilotAuthState:
    return login_with_standard_device_code(
        provider=GITHUB_COPILOT_OAUTH_PROVIDER,
        auth_path=auth_path,
        resolve_auth_path=resolve_github_copilot_auth_path,
        load_auth_state=load_github_copilot_auth,
        persist_tokens=persist_github_copilot_tokens,
        notify=notify,
        error_factory=GitHubCopilotAuthError,
    )


def login_github_copilot_with_browser(
    *,
    auth_path: str | os.PathLike[str] | None = None,
    notify=None,
    **_ignored: Any,
) -> GitHubCopilotAuthState:
    if notify is not None:
        notify(
            "GitHub Copilot uses GitHub device-code login in aish; starting device-code flow."
        )
    return login_github_copilot_with_device_code(
        auth_path=auth_path,
        notify=notify,
    )


def derive_github_copilot_api_base_url_from_runtime_token(token: str) -> str | None:
    trimmed = token.strip()
    if not trimmed:
        return None

    match = trimmed.replace(";", "; ").split(";")
    for item in match:
        key, separator, value = item.strip().partition("=")
        if separator and key.lower() == "proxy-ep" and value.strip():
            host = value.strip().replace("https://", "").replace("http://", "")
            host = host.replace("proxy.", "api.", 1)
            return f"https://{host}"
    return None


async def resolve_github_copilot_runtime_auth(
    auth_state: GitHubCopilotAuthState,
    *,
    client: httpx.AsyncClient | None = None,
    force_refresh: bool = False,
) -> GitHubCopilotAuthState:
    if auth_state.has_valid_runtime_token() and not force_refresh:
        return auth_state

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)

    try:
        response = await client.get(
            GITHUB_COPILOT_RUNTIME_TOKEN_URL,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_state.github_token}",
            },
        )
    except Exception as exc:
        raise GitHubCopilotAuthError(
            f"GitHub Copilot runtime token exchange failed: {exc}"
        ) from exc
    finally:
        if owns_client:
            await client.aclose()

    if response.is_error:
        raise GitHubCopilotAuthError(
            f"GitHub Copilot runtime token exchange failed: {response.status_code} {_extract_http_error_message(response)}"
        )

    try:
        payload = response.json()
    except Exception as exc:
        raise GitHubCopilotAuthError(
            "GitHub Copilot runtime token exchange returned invalid JSON."
        ) from exc

    runtime_token = _coerce_str(payload.get("token"))
    expires_at = _normalize_timestamp_ms(payload.get("expires_at"))
    if not runtime_token or expires_at is None:
        raise GitHubCopilotAuthError(
            "GitHub Copilot runtime token exchange returned incomplete data."
        )

    runtime_api_base = (
        derive_github_copilot_api_base_url_from_runtime_token(runtime_token)
        or GITHUB_COPILOT_DEFAULT_BASE_URL
    )
    _persist_github_copilot_auth(
        auth_state.auth_path,
        github_token=auth_state.github_token,
        token_type=auth_state.token_type,
        scope=auth_state.scope,
        runtime_token=runtime_token,
        runtime_token_expires_at=expires_at,
        runtime_api_base=runtime_api_base,
    )
    return GitHubCopilotAuthState(
        auth_path=auth_state.auth_path,
        github_token=auth_state.github_token,
        token_type=auth_state.token_type,
        scope=auth_state.scope,
        runtime_token=runtime_token,
        runtime_token_expires_at=expires_at,
        runtime_api_base=runtime_api_base,
    )


def build_github_copilot_request(
    *,
    model: str,
    messages: list[dict[str, Any]],
    stream: bool,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str = "auto",
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "model": strip_github_copilot_prefix(model),
        "messages": messages,
        "stream": stream,
    }
    if tools:
        request["tools"] = tools
        request["tool_choice"] = tool_choice
    if temperature is not None:
        request["temperature"] = temperature
    if max_tokens is not None:
        request["max_tokens"] = max_tokens
    return request


async def create_github_copilot_chat_completion(
    *,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str = "auto",
    auth_path: str | os.PathLike[str] | None = None,
    timeout: float = 300.0,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    auth = load_github_copilot_auth(auth_path)
    request_body = build_github_copilot_request(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
        stream=False,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        auth = await resolve_github_copilot_runtime_auth(auth, client=client)

        for attempt in range(2):
            response = await client.post(
                f"{_resolve_github_copilot_base_url(auth.runtime_api_base)}/chat/completions",
                json=request_body,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {auth.runtime_token}",
                },
            )
            if response.status_code == httpx.codes.UNAUTHORIZED and attempt == 0:
                auth = await resolve_github_copilot_runtime_auth(
                    auth,
                    client=client,
                    force_refresh=True,
                )
                continue
            if response.is_error:
                raise GitHubCopilotAuthError(
                    f"GitHub Copilot request failed: {response.status_code} {_extract_http_error_message(response)}"
                )
            try:
                payload = response.json()
            except Exception as exc:
                raise GitHubCopilotAuthError(
                    "GitHub Copilot returned invalid JSON."
                ) from exc
            if not isinstance(payload, dict):
                raise GitHubCopilotAuthError(
                    "GitHub Copilot returned an unexpected response payload."
                )
            return payload

    raise GitHubCopilotAuthError(
        "GitHub Copilot request failed after runtime token refresh."
    )


def _persist_github_copilot_auth(
    path: Path,
    *,
    github_token: str,
    token_type: str | None = None,
    scope: str | None = None,
    runtime_token: str | None = None,
    runtime_token_expires_at: int | None = None,
    runtime_api_base: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "provider": GITHUB_COPILOT_PROVIDER,
        "github_token": github_token,
    }
    if token_type:
        payload["token_type"] = token_type
    if scope:
        payload["scope"] = scope
    if runtime_token and runtime_token_expires_at is not None:
        payload["runtime"] = {
            "token": runtime_token,
            "expires_at": runtime_token_expires_at,
            "api_base": runtime_api_base or GITHUB_COPILOT_DEFAULT_BASE_URL,
        }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _resolve_github_copilot_base_url(api_base: str | None) -> str:
    trimmed = (api_base or "").strip().rstrip("/")
    return trimmed or GITHUB_COPILOT_DEFAULT_BASE_URL


def _extract_http_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        return response.text.strip() or "unknown error"

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = _coerce_str(error.get("message"))
            if message:
                return message
        error_text = _coerce_str(error)
        if error_text:
            return error_text
        message = _coerce_str(payload.get("message"))
        if message:
            return message
    return response.text.strip() or "unknown error"


def _coerce_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _coerce_int(value: Any) -> Optional[int]:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _normalize_timestamp_ms(value: Any) -> int | None:
    parsed = _coerce_int(value)
    if parsed is None:
        return None
    return parsed if parsed > 10_000_000_000 else parsed * 1000


class GitHubCopilotProviderAdapter:
    provider_id = GITHUB_COPILOT_PROVIDER
    model_prefix = GITHUB_COPILOT_PROVIDER
    display_name = GITHUB_COPILOT_OAUTH_PROVIDER.display_name
    uses_litellm = False
    supports_streaming = False
    should_trim_messages = False
    auth_config = ProviderAuthConfig(
        auth_path_config_key="github_copilot_auth_path",
        default_model=GITHUB_COPILOT_DEFAULT_MODEL,
        load_auth_state=lambda auth_path: load_github_copilot_auth(auth_path),
        login_handlers={
            "browser": lambda **kwargs: login_github_copilot_with_browser(**kwargs),
            "device-code": lambda **kwargs: login_github_copilot_with_device_code(
                **kwargs
            ),
        },
    )

    def matches_model(self, model: str | None) -> bool:
        return is_github_copilot_model(model)

    async def create_completion(
        self,
        *,
        model: str,
        config,
        api_base: str | None,
        api_key: str | None,
        messages: list[dict[str, Any]],
        stream: bool,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
        fallback_completion=None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return await create_github_copilot_chat_completion(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            auth_path=getattr(config, self.auth_config.auth_path_config_key, None),
            timeout=float(kwargs.get("timeout", 300)),
            temperature=getattr(config, "temperature", None),
            max_tokens=getattr(config, "max_tokens", None),
        )

    async def validate_model_switch(self, *, model: str, config) -> str | None:
        try:
            load_github_copilot_auth(
                getattr(config, self.auth_config.auth_path_config_key, None)
            )
        except GitHubCopilotAuthError as exc:
            return str(exc)
        return None


GITHUB_COPILOT_PROVIDER_ADAPTER = GitHubCopilotProviderAdapter()