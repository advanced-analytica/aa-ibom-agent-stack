"""Tests for the provider-aware agent models endpoint."""

import pytest

from app.core.config import settings


@pytest.mark.anyio
async def test_agent_models_endpoint_returns_provider_metadata(client, monkeypatch):
    monkeypatch.setattr(settings, "CHAT_PROVIDER", "openai")
    monkeypatch.setattr(settings, "CHAT_MODEL", "gpt-5.4-mini")
    monkeypatch.setattr(settings, "CHAT_ENABLED_PROVIDERS", ["openai", "gemini"])
    monkeypatch.setattr(settings, "CHAT_OPENAI_MODELS", ["gpt-5.4-mini"])
    monkeypatch.setattr(settings, "CHAT_GEMINI_MODELS", ["gemini-2.5-flash"])

    response = await client.get(f"{settings.API_V1_STR}/agent/models")

    assert response.status_code == 200
    data = response.json()
    assert data["default"] == "openai:gpt-5.4-mini"
    assert data["models"] == [
        {
            "id": "openai:gpt-5.4-mini",
            "provider": "openai",
            "model": "gpt-5.4-mini",
            "label": "OpenAI: gpt-5.4-mini",
            "enabled": True,
            "default": True,
        },
        {
            "id": "gemini:gemini-2.5-flash",
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "label": "Gemini: gemini-2.5-flash",
            "enabled": True,
            "default": False,
        },
    ]
