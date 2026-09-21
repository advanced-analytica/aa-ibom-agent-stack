"""Authentication routes."""

import logging
from typing import Annotated, Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, SessionSvc, UserSvc
from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
)
from app.schemas.token import (
    GoogleOAuthCallbackRequest,
    RefreshTokenRequest,
    SupabaseOtpRequest,
    SupabaseOtpVerifyRequest,
    Token,
)
from app.schemas.user import UserCreate, UserRead

logger = logging.getLogger(__name__)

router = APIRouter()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def _require_google_oauth_config() -> None:
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured",
        )


def _oauth_redirect_uri(redirect_uri: str | None = None) -> str:
    return redirect_uri or settings.GOOGLE_OAUTH_REDIRECT_URI


def _require_supabase_auth_config() -> None:
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase OTP sign-in is not configured",
        )


def _supabase_auth_url(path: str) -> str:
    return f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/{path.lstrip('/')}"


def _supabase_headers() -> dict[str, str]:
    return {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


@router.post(
    "/login",
    response_model=Token,
)
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserSvc,
    session_service: SessionSvc,
) -> Any:
    """OAuth2 password login, returns access and refresh tokens."""
    user = await user_service.authenticate(form_data.username, form_data.password)
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    # Track this login as a server-side session (enables remote logout).
    await session_service.create_session(
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/google/authorize")
async def google_authorize(
    state: Annotated[str, Query(min_length=16)],
    redirect_uri: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    """Redirect the browser to Google's OAuth 2.0 authorization endpoint."""
    _require_google_oauth_config()
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": _oauth_redirect_uri(redirect_uri),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.post("/google/callback", response_model=Token)
async def google_callback(
    request: Request,
    body: GoogleOAuthCallbackRequest,
    user_service: UserSvc,
    session_service: SessionSvc,
) -> Token:
    """Exchange a Google authorization code for local auth tokens."""
    _require_google_oauth_config()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": body.code,
                    "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                    "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                    "redirect_uri": _oauth_redirect_uri(body.redirect_uri),
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
            token_response.raise_for_status()
            google_tokens = token_response.json()

            access_token = google_tokens.get("access_token")
            if not access_token:
                raise AuthenticationError(message="Google token response missing access token")

            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_response.raise_for_status()
            profile = userinfo_response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("Google OAuth request failed: %s", exc.response.status_code)
        raise AuthenticationError(message="Google sign-in failed") from exc
    except httpx.HTTPError as exc:
        logger.warning("Google OAuth network error: %s", exc)
        raise AuthenticationError(message="Google sign-in failed") from exc

    google_sub = profile.get("sub")
    email = profile.get("email")
    if not google_sub or not email:
        raise AuthenticationError(message="Google profile did not include a user identity")

    email_verified = profile.get("email_verified")
    if isinstance(email_verified, str):
        email_verified = email_verified.lower() == "true"

    user = await user_service.authenticate_google(
        email=email,
        google_sub=google_sub,
        email_verified=bool(email_verified),
        full_name=profile.get("name"),
        avatar_url=profile.get("picture"),
    )
    local_access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    await session_service.create_session(
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    return Token(access_token=local_access_token, refresh_token=refresh_token)


@router.post("/supabase-otp/request")
async def supabase_otp_request(body: SupabaseOtpRequest) -> dict[str, bool | str]:
    """Send an email OTP through Supabase Auth."""
    _require_supabase_auth_config()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                _supabase_auth_url("otp"),
                headers=_supabase_headers(),
                json={
                    "email": body.email,
                    "create_user": True,
                    "data": {},
                },
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning("Supabase OTP request failed: %s", exc.response.status_code)
        raise AuthenticationError(message="Could not send sign-in code") from exc
    except httpx.HTTPError as exc:
        logger.warning("Supabase OTP network error: %s", exc)
        raise AuthenticationError(message="Could not send sign-in code") from exc
    return {"sent": True, "message": "If email sign-in is enabled, a code has been sent."}


@router.post("/supabase-otp/verify", response_model=Token)
async def supabase_otp_verify(
    request: Request,
    body: SupabaseOtpVerifyRequest,
    user_service: UserSvc,
    session_service: SessionSvc,
) -> Token:
    """Verify a Supabase email OTP and issue local app tokens."""
    _require_supabase_auth_config()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                _supabase_auth_url("verify"),
                headers=_supabase_headers(),
                json={"email": body.email, "token": body.token, "type": "email"},
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("Supabase OTP verify failed: %s", exc.response.status_code)
        raise AuthenticationError(message="Invalid or expired sign-in code") from exc
    except httpx.HTTPError as exc:
        logger.warning("Supabase OTP network error: %s", exc)
        raise AuthenticationError(message="Invalid or expired sign-in code") from exc

    supabase_user = payload.get("user") or {}
    supabase_user_id = supabase_user.get("id")
    email = supabase_user.get("email") or body.email
    if not supabase_user_id or not email:
        raise AuthenticationError(message="Supabase profile did not include a user identity")

    metadata = supabase_user.get("user_metadata") or {}
    user = await user_service.authenticate_supabase_otp(
        email=email,
        supabase_auth_user_id=supabase_user_id,
        full_name=metadata.get("full_name") or metadata.get("name"),
    )
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    await session_service.create_session(
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_in: UserCreate,
    user_service: UserSvc,
) -> Any:
    """Register a new user."""
    user = await user_service.register(user_in)
    return user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    body: RefreshTokenRequest,
    user_service: UserSvc,
    session_service: SessionSvc,
) -> Any:
    """Exchange a refresh token for a new access token."""

    session = await session_service.validate_refresh_token(body.refresh_token)
    if not session:
        raise AuthenticationError(message="Invalid or expired refresh token")

    user = await user_service.get_by_id(session.user_id)
    if not user.is_active:
        raise AuthenticationError(message="User account is disabled")

    access_token = create_access_token(subject=str(user.id))
    new_refresh_token = create_refresh_token(subject=str(user.id))

    await session_service.logout_by_refresh_token(body.refresh_token)
    await session_service.create_session(
        user_id=user.id,
        refresh_token=new_refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    return Token(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout(
    body: RefreshTokenRequest,
    session_service: SessionSvc,
) -> None:
    """Logout and invalidate the current session.

    Invalidates the refresh token, preventing further token refresh.
    """
    await session_service.logout_by_refresh_token(body.refresh_token)


@router.get("/me", response_model=UserRead)
async def get_current_user_info(current_user: CurrentUser) -> Any:
    """Get current authenticated user information."""
    return current_user
