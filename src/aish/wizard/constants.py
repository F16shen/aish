"""Constants used by setup wizard."""

from __future__ import annotations

_PROVIDER_ENV_KEYS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "google": "GOOGLE_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "zai": "ZAI_API_KEY",
    "openrouter": "OPENAI_API_KEY",
}

_PROVIDER_LABELS: dict[str, str] = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "deepseek": "DeepSeek",
    "gemini": "Gemini",
    "google": "Google",
    "minimax": "MiniMax",
    "moonshot": "Moonshot AI",
    "zai": "Z.AI",
    "openrouter": "OpenRouter",
    "azure": "Azure",
}

_PROVIDER_BASES: dict[str, str] = {
    "openrouter": "https://openrouter.ai/api/v1",
}

_PROVIDER_ALIASES: dict[str, str] = {
    "open_router": "openrouter",
    "openrouter.ai": "openrouter",
}

_PROVIDER_PRIORITY: tuple[str, ...] = (
    "openrouter",
    "openai",
    "anthropic",
    "deepseek",
    "gemini",
    "google",
    "minimax",
    "moonshot",
    "zai",
    "azure",
    "bedrock",
)

_STATIC_FILTER_SKIP_PROVIDERS: set[str] = {
    "aiohttp_openai",
    "azure",
    "azure_ai",
    "azure_text",
    "custom",
    "custom_openai",
    "databricks",
    "litellm_proxy",
    "llamafile",
    "lm_studio",
    "ollama",
    "ollama_chat",
    "openai_like",
    "openrouter",
    "oobabooga",
    "predibase",
    "sagemaker",
    "sagemaker_chat",
    "snowflake",
    "vllm",
    "hosted_vllm",
    "xinference",
}
