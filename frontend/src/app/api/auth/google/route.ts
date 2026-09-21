import { randomBytes } from "crypto";
import { NextRequest, NextResponse } from "next/server";

import { setOAuthStateCookie } from "@/lib/auth-cookies";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function requestOrigin(request: NextRequest): string {
  const forwardedProto = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim();
  const forwardedHost = request.headers.get("x-forwarded-host")?.split(",")[0]?.trim();
  const host = forwardedHost || request.headers.get("host");
  if (host) {
    return `${forwardedProto || "http"}://${host}`;
  }
  return request.nextUrl.origin || process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
}

export async function GET(request: NextRequest) {
  const state = randomBytes(32).toString("base64url");
  const redirectUri = new URL("/auth/callback", requestOrigin(request)).toString();
  const authorizeUrl = new URL("/api/v1/auth/google/authorize", PUBLIC_API_URL || BACKEND_URL);
  authorizeUrl.searchParams.set("state", state);
  authorizeUrl.searchParams.set("redirect_uri", redirectUri);

  const response = NextResponse.redirect(authorizeUrl);
  setOAuthStateCookie(response, state);
  return response;
}
