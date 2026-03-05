import pytest


@pytest.fixture(autouse=True)
def _isolate_xdg_config_home(tmp_path, monkeypatch: pytest.MonkeyPatch):
    # Ensure tests do not read/write real user config under ~/.config/aish
    # (which makes tests machine-dependent).
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))


@pytest.fixture
def anyio_backend() -> str:
    # 配置所有 @pytest.mark.anyio 测试使用 asyncio 后端
    return "asyncio"
