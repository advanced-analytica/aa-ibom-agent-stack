"""Tests for provider-aware model configuration."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.model_registry import (
    ProviderConfigError,
    build_chat_model,
    chat_model_options,
    resolve_chat_model_ref,
)
from app.services.rag.config import EmbeddingsConfig, RAGSettings
from app.services.rag.embeddings import EmbeddingService


def _settings(**overrides):
    defaults = {
        "CHAT_PROVIDER": "anthropic",
        "CHAT_MODEL": "claude-sonnet-4-5",
        "AI_MODEL": "gemini-2.5-flash",
        "CHAT_ENABLED_PROVIDERS": ["anthropic", "openai", "gemini"],
        "CHAT_ANTHROPIC_MODELS": ["claude-sonnet-4-5"],
        "CHAT_OPENAI_MODELS": ["gpt-5.4-mini"],
        "CHAT_GEMINI_MODELS": ["gemini-2.5-flash"],
        "ANTHROPIC_API_KEY": "anthropic-key",
        "OPENAI_API_KEY": "openai-key",
        "GOOGLE_API_KEY": "google-key",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_chat_model_options_include_enabled_providers_and_default():
    options = chat_model_options(_settings())

    assert [option["id"] for option in options] == [
        "anthropic:claude-sonnet-4-5",
        "openai:gpt-5.4-mini",
        "gemini:gemini-2.5-flash",
    ]
    assert options[0]["default"] is True
    assert {option["provider"] for option in options} == {"anthropic", "openai", "gemini"}


def test_chat_model_options_exclude_disabled_providers():
    options = chat_model_options(
        _settings(
            CHAT_PROVIDER="openai",
            CHAT_MODEL="gpt-5.4-mini",
            CHAT_ENABLED_PROVIDERS=["openai"],
        )
    )

    assert [option["provider"] for option in options] == ["openai"]


def test_resolve_bare_model_uses_enabled_provider_list():
    ref = resolve_chat_model_ref("gpt-5.4-mini", _settings())

    assert ref.provider == "openai"
    assert ref.model == "gpt-5.4-mini"
    assert ref.id == "openai:gpt-5.4-mini"


def test_unknown_chat_provider_fails_clearly():
    with pytest.raises(ProviderConfigError, match="Unsupported chat provider"):
        chat_model_options(_settings(CHAT_PROVIDER="llama", CHAT_ENABLED_PROVIDERS=["llama"]))


def test_missing_chat_provider_key_fails_clearly():
    with pytest.raises(ProviderConfigError, match="ANTHROPIC_API_KEY"):
        build_chat_model(None, _settings(ANTHROPIC_API_KEY=""))


@patch("pydantic_ai.models.anthropic.AnthropicModel")
@patch("pydantic_ai.providers.anthropic.AnthropicProvider")
def test_build_chat_model_uses_anthropic_adapter(mock_provider, mock_model):
    mock_provider.return_value = MagicMock()
    mock_model.return_value = MagicMock()

    build_chat_model("anthropic:claude-sonnet-4-5", _settings())

    mock_provider.assert_called_once_with(api_key="anthropic-key")
    mock_model.assert_called_once_with("claude-sonnet-4-5", provider=mock_provider.return_value)


@patch("pydantic_ai.models.openai.OpenAIChatModel")
@patch("pydantic_ai.providers.openai.OpenAIProvider")
def test_build_chat_model_uses_openai_adapter(mock_provider, mock_model):
    mock_provider.return_value = MagicMock()
    mock_model.return_value = MagicMock()

    build_chat_model("openai:gpt-5.4-mini", _settings())

    mock_provider.assert_called_once_with(api_key="openai-key")
    mock_model.assert_called_once_with("gpt-5.4-mini", provider=mock_provider.return_value)


@patch("pydantic_ai.models.google.GoogleModel")
@patch("pydantic_ai.providers.google.GoogleProvider")
def test_build_chat_model_uses_gemini_adapter(mock_provider, mock_model):
    mock_provider.return_value = MagicMock()
    mock_model.return_value = MagicMock()

    build_chat_model("gemini:gemini-2.5-flash", _settings())

    mock_provider.assert_called_once_with(api_key="google-key")
    mock_model.assert_called_once_with("gemini-2.5-flash", provider=mock_provider.return_value)


def test_embedding_config_derives_openai_dimension():
    config = EmbeddingsConfig(provider="openai", model="text-embedding-3-small")

    assert config.provider == "openai"
    assert config.dim == 1536


def test_embedding_config_rejects_mismatched_provider_model():
    with pytest.raises(ValueError, match="Unsupported embedding model"):
        EmbeddingsConfig(provider="gemini", model="text-embedding-3-small")


@patch("app.services.rag.embeddings.OpenAIEmbeddingProvider")
def test_embedding_service_uses_openai_provider(mock_provider, monkeypatch):
    monkeypatch.setattr("app.services.rag.embeddings.app_settings.OPENAI_API_KEY", "openai-key")
    rag_settings = RAGSettings(
        embeddings_config=EmbeddingsConfig(provider="openai", model="text-embedding-3-small")
    )

    service = EmbeddingService(rag_settings)

    assert service.provider is mock_provider.return_value
    mock_provider.assert_called_once_with(
        model="text-embedding-3-small",
        api_key="openai-key",
    )


@patch("app.services.rag.embeddings.GeminiEmbeddingProvider")
def test_embedding_service_uses_gemini_provider(mock_provider, monkeypatch):
    monkeypatch.setattr("app.services.rag.embeddings.app_settings.GOOGLE_API_KEY", "google-key")
    rag_settings = RAGSettings(
        embeddings_config=EmbeddingsConfig(provider="gemini", model="gemini-embedding-exp-03-07")
    )

    service = EmbeddingService(rag_settings)

    assert service.provider is mock_provider.return_value
    mock_provider.assert_called_once_with(
        model="gemini-embedding-exp-03-07",
        api_key="google-key",
    )
