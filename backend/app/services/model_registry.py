"""Provider-aware model registry for chat model configuration."""

from dataclasses import dataclass
from typing import Any

CHAT_PROVIDER_LABELS: dict[str, str] = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "gemini": "Gemini",
}

CHAT_PROVIDER_KEY_FIELDS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GOOGLE_API_KEY",
}

CHAT_PROVIDER_MODEL_FIELDS: dict[str, str] = {
    "anthropic": "CHAT_ANTHROPIC_MODELS",
    "openai": "CHAT_OPENAI_MODELS",
    "gemini": "CHAT_GEMINI_MODELS",
}


class ProviderConfigError(ValueError):
    """Raised when model provider configuration is invalid."""


@dataclass(frozen=True)
class ChatModelRef:
    provider: str
    model: str

    @property
    def id(self) -> str:
        return f"{self.provider}:{self.model}"


def normalize_provider(provider: str) -> str:
    normalized = (provider or "").strip().lower()
    if normalized == "google":
        return "gemini"
    return normalized


def _configured_chat_models(app_settings: Any, provider: str) -> list[str]:
    field_name = CHAT_PROVIDER_MODEL_FIELDS.get(provider)
    if not field_name:
        raise ProviderConfigError(f"Unsupported chat provider: {provider}")
    return list(getattr(app_settings, field_name, []) or [])


def enabled_chat_providers(app_settings: Any) -> list[str]:
    providers = [normalize_provider(p) for p in (app_settings.CHAT_ENABLED_PROVIDERS or [])]
    default_provider = normalize_provider(app_settings.CHAT_PROVIDER)
    if default_provider and default_provider not in providers:
        providers.insert(0, default_provider)
    invalid = sorted({p for p in providers if p not in CHAT_PROVIDER_MODEL_FIELDS})
    if invalid:
        raise ProviderConfigError(f"Unsupported chat provider(s): {', '.join(invalid)}")
    return list(dict.fromkeys(providers))


def default_chat_model_ref(app_settings: Any) -> ChatModelRef:
    provider = normalize_provider(app_settings.CHAT_PROVIDER)
    if provider not in CHAT_PROVIDER_MODEL_FIELDS:
        raise ProviderConfigError(f"Unsupported chat provider: {provider}")
    model = (getattr(app_settings, "CHAT_MODEL", "") or getattr(app_settings, "AI_MODEL", "")).strip()
    if not model:
        models = _configured_chat_models(app_settings, provider)
        if not models:
            raise ProviderConfigError(f"No chat models configured for provider: {provider}")
        model = models[0]
    return ChatModelRef(provider=provider, model=model)


def chat_model_options(app_settings: Any) -> list[dict[str, Any]]:
    default_ref = default_chat_model_ref(app_settings)
    options: list[dict[str, Any]] = []
    for provider in enabled_chat_providers(app_settings):
        for model in _configured_chat_models(app_settings, provider):
            ref = ChatModelRef(provider=provider, model=model)
            options.append(
                {
                    "id": ref.id,
                    "provider": provider,
                    "model": model,
                    "label": f"{CHAT_PROVIDER_LABELS[provider]}: {model}",
                    "enabled": True,
                    "default": ref == default_ref,
                }
            )
    if not any(option["id"] == default_ref.id for option in options):
        options.insert(
            0,
            {
                "id": default_ref.id,
                "provider": default_ref.provider,
                "model": default_ref.model,
                "label": f"{CHAT_PROVIDER_LABELS[default_ref.provider]}: {default_ref.model}",
                "enabled": True,
                "default": True,
            },
        )
    return options


def resolve_chat_model_ref(model_ref: str | None, app_settings: Any) -> ChatModelRef:
    if not model_ref:
        return default_chat_model_ref(app_settings)
    raw_ref = model_ref.strip()
    if ":" in raw_ref:
        provider, model = raw_ref.split(":", 1)
        resolved = ChatModelRef(provider=normalize_provider(provider), model=model)
    else:
        enabled_matches = [
            ChatModelRef(provider=provider, model=raw_ref)
            for provider in enabled_chat_providers(app_settings)
            if raw_ref in _configured_chat_models(app_settings, provider)
        ]
        resolved = enabled_matches[0] if enabled_matches else ChatModelRef(
            provider=normalize_provider(app_settings.CHAT_PROVIDER),
            model=raw_ref,
        )
    if resolved.provider not in CHAT_PROVIDER_MODEL_FIELDS:
        raise ProviderConfigError(f"Unsupported chat provider: {resolved.provider}")
    configured = _configured_chat_models(app_settings, resolved.provider)
    if configured and resolved.model not in configured:
        raise ProviderConfigError(
            f"Unsupported chat model for provider {resolved.provider}: {resolved.model}"
        )
    return resolved


def require_api_key(app_settings: Any, provider: str) -> str:
    field_name = CHAT_PROVIDER_KEY_FIELDS.get(provider)
    if not field_name:
        raise ProviderConfigError(f"Unsupported provider: {provider}")
    api_key = getattr(app_settings, field_name, "")
    if not api_key:
        raise ProviderConfigError(f"{field_name} is required for provider '{provider}'")
    return api_key


def build_chat_model(model_ref: str | None, app_settings: Any) -> Any:
    ref = resolve_chat_model_ref(model_ref, app_settings)
    api_key = require_api_key(app_settings, ref.provider)
    if ref.provider == "anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        return AnthropicModel(ref.model, provider=AnthropicProvider(api_key=api_key))
    if ref.provider == "openai":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        return OpenAIChatModel(ref.model, provider=OpenAIProvider(api_key=api_key))
    if ref.provider == "gemini":
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        return GoogleModel(ref.model, provider=GoogleProvider(api_key=api_key))
    raise ProviderConfigError(f"Unsupported chat provider: {ref.provider}")
