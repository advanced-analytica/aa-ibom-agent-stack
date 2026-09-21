# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
"""Tests for authentication routes."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

ServiceMock = AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_session_service, get_user_service
from app.core.config import settings
from app.core.exceptions import AlreadyExistsError, AuthenticationError
from app.main import app
from app.api.deps import get_redis
from app.api.deps import get_db_session


class MockUser:
    """Mock user for testing."""

    def __init__(
        self,
        id=None,
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        role="user",
    ):
        self.id = id or uuid4()
        self.email = email
        self.full_name = full_name
        self.is_active = is_active
        self.role = role
        self.hashed_password = "hashed"
        self.avatar_url = None
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)


@pytest.fixture
def mock_user() -> MockUser:
    """Create a mock user."""
    return MockUser()


@pytest.fixture
def mock_user_service(mock_user: MockUser) -> MagicMock:
    """Create a mock user service."""
    service = MagicMock()
    service.authenticate = ServiceMock(return_value=mock_user)
    service.register = ServiceMock(return_value=mock_user)
    service.get_by_id = ServiceMock(return_value=mock_user)
    service.get_by_email = ServiceMock(return_value=mock_user)
    service.authenticate_google = ServiceMock(return_value=mock_user)
    service.authenticate_supabase_otp = ServiceMock(return_value=mock_user)
    return service


@pytest.fixture
def mock_session_service() -> MagicMock:
    """Create a mock session service."""
    service = MagicMock()
    service.create_session = ServiceMock()
    return service


@pytest.fixture
async def client_with_mock_service(
    mock_user_service: MagicMock,
    mock_session_service: MagicMock,
    mock_redis: MagicMock,
    mock_db_session,
) -> AsyncClient:
    """Client with mocked user service."""
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_session_service] = lambda: mock_session_service
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db_session] = lambda: mock_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_login_success(client_with_mock_service: AsyncClient):
    """Test successful login."""
    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_invalid_credentials(
    client_with_mock_service: AsyncClient,
    mock_user_service: MagicMock,
):
    """Test login with invalid credentials."""
    mock_user_service.authenticate = ServiceMock(
        side_effect=AuthenticationError(message="Invalid credentials")
    )

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": "test@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_register_success(client_with_mock_service: AsyncClient):
    """Test successful registration."""
    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "new@example.com",
            "password": "password123",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"  # From mock


@pytest.mark.anyio
async def test_register_duplicate_email(
    client_with_mock_service: AsyncClient,
    mock_user_service: MagicMock,
):
    """Test registration with duplicate email."""
    mock_user_service.register = ServiceMock(
        side_effect=AlreadyExistsError(message="Email already registered")
    )

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "existing@example.com",
            "password": "password123",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_get_current_user(
    client_with_mock_service: AsyncClient,
    mock_user: MockUser,
    mock_user_service: MagicMock,
):
    """Test getting current user info."""
    # Override get_current_user to return mock user
    app.dependency_overrides[get_current_user] = lambda: mock_user

    response = await client_with_mock_service.get(
        f"{settings.API_V1_STR}/auth/me",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == mock_user.email


@pytest.mark.anyio
async def test_google_authorize_requires_config(
    client_with_mock_service: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """Google OAuth endpoints fail closed until client credentials are configured."""
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")

    response = await client_with_mock_service.get(
        f"{settings.API_V1_STR}/auth/google/authorize",
        params={"state": "state-with-enough-entropy"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Google sign-in is not configured"


@pytest.mark.anyio
async def test_google_callback_exchanges_code_and_creates_local_session(
    client_with_mock_service: AsyncClient,
    mock_user_service: MagicMock,
    mock_session_service: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    """The OAuth callback converts a verified Google identity into local tokens."""
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "google-client-id")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "google-client-secret")

    token_response = MagicMock()
    token_response.raise_for_status = MagicMock()
    token_response.json.return_value = {"access_token": "google-access-token"}

    userinfo_response = MagicMock()
    userinfo_response.raise_for_status = MagicMock()
    long_avatar_url = f"https://lh3.googleusercontent.com/a-/{'x' * 900}=s96-c"
    userinfo_response.json.return_value = {
        "sub": "google-sub-123",
        "email": "Test@Example.com",
        "email_verified": True,
        "name": "Test User",
        "picture": long_avatar_url,
    }

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return token_response

        async def get(self, *args, **kwargs):
            return userinfo_response

    monkeypatch.setattr("app.api.routes.v1.auth.httpx.AsyncClient", MockAsyncClient)

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/google/callback",
        json={"code": "auth-code", "state": "state-with-enough-entropy"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    mock_user_service.authenticate_google.assert_awaited_once_with(
        email="Test@Example.com",
        google_sub="google-sub-123",
        email_verified=True,
        full_name="Test User",
        avatar_url=long_avatar_url,
    )
    mock_session_service.create_session.assert_awaited_once()


@pytest.mark.anyio
async def test_supabase_otp_request_requires_config(
    client_with_mock_service: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """Supabase OTP fails closed until URL and anon key are configured."""
    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    monkeypatch.setattr(settings, "SUPABASE_ANON_KEY", "")

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/supabase-otp/request",
        json={"email": "test@example.com"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Supabase OTP sign-in is not configured"


@pytest.mark.anyio
async def test_supabase_otp_verify_exchanges_verified_user_for_local_session(
    client_with_mock_service: AsyncClient,
    mock_user_service: MagicMock,
    mock_session_service: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    """A verified Supabase OTP identity is exchanged for local app tokens."""
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_ANON_KEY", "anon-key")

    verify_response = MagicMock()
    verify_response.raise_for_status = MagicMock()
    verify_response.json.return_value = {
        "user": {
            "id": "supabase-user-123",
            "email": "Test@Example.com",
            "user_metadata": {"name": "Test User"},
        },
        "access_token": "supabase-access-token",
    }

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return verify_response

    monkeypatch.setattr("app.api.routes.v1.auth.httpx.AsyncClient", MockAsyncClient)

    response = await client_with_mock_service.post(
        f"{settings.API_V1_STR}/auth/supabase-otp/verify",
        json={"email": "test@example.com", "token": "123456"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    mock_user_service.authenticate_supabase_otp.assert_awaited_once_with(
        email="Test@Example.com",
        supabase_auth_user_id="supabase-user-123",
        full_name="Test User",
    )
    mock_session_service.create_session.assert_awaited_once()
