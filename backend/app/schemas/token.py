"""Token schemas."""

from typing import Literal

from pydantic import EmailStr

from app.schemas.base import BaseSchema


class Token(BaseSchema):
    """OAuth2 token response with refresh token."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseSchema):
    """JWT token payload."""

    sub: str | None = None
    exp: int | None = None
    type: Literal["access", "refresh"] | None = None


class RefreshTokenRequest(BaseSchema):
    """Request body for token refresh."""

    refresh_token: str


class GoogleOAuthCallbackRequest(BaseSchema):
    """Authorization-code callback payload from the frontend OAuth handler."""

    code: str
    state: str | None = None
    redirect_uri: str | None = None


class SupabaseOtpRequest(BaseSchema):
    """Request an email OTP from Supabase Auth."""

    email: EmailStr


class SupabaseOtpVerifyRequest(BaseSchema):
    """Verify a Supabase email OTP and exchange it for a local session."""

    email: EmailStr
    token: str
