import { NextRequest, NextResponse } from "next/server";

import {
  clearOAuthStateCookie,
  OAUTH_STATE_COOKIE,
  setAuthCookies,
} from "@/lib/auth-cookies";
import { backendFetch, BackendApiError } from "@/lib/server-api";

interface OAuthCallbackBody {
  code: string;
  state: string;
  redirect_uri?: string;
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as Partial<OAuthCallbackBody>;
    if (!body.code || !body.state) {
      return NextResponse.json({ detail: "Missing OAuth callback parameters" }, { status: 400 });
    }

    const expectedState = request.cookies.get(OAUTH_STATE_COOKIE)?.value;
    if (!expectedState || expectedState !== body.state) {
      return NextResponse.json({ detail: "Invalid OAuth state" }, { status: 400 });
    }

    const tokens = await backendFetch<{ access_token: string; refresh_token: string }>(
      "/api/v1/auth/google/callback",
      {
        method: "POST",
        body: JSON.stringify({
          code: body.code,
          state: body.state,
          redirect_uri: body.redirect_uri,
        }),
      },
    );

    const user = await backendFetch("/api/v1/auth/me", {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    });

    const response = NextResponse.json({
      user,
      access_token: tokens.access_token,
      message: "Sign-in successful",
    });

    setAuthCookies(response, {
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
    });
    clearOAuthStateCookie(response);
    return response;
  } catch (error) {
    if (error instanceof BackendApiError) {
      const detail = (error.data as { detail?: string })?.detail || "Sign-in failed";
      return NextResponse.json({ detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
