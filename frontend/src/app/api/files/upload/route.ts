import { NextRequest, NextResponse } from "next/server";
import { clearAuthCookies, setAuthCookies } from "@/lib/auth-cookies";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

async function refreshAccessToken(refreshToken: string) {
  const response = await fetch(`${BACKEND_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) return null;
  return (await response.json()) as { access_token: string; refresh_token?: string };
}

async function uploadToBackend(formData: FormData, accessToken: string) {
  return fetch(`${BACKEND_URL}/api/v1/files/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: formData,
  });
}

export async function POST(request: NextRequest) {
  try {
    let accessToken = request.cookies.get("access_token")?.value;
    const refreshToken = request.cookies.get("refresh_token")?.value;
    let refreshedTokens: { access_token: string; refresh_token?: string } | null = null;

    if (!accessToken) {
      if (!refreshToken) {
        return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
      }
      refreshedTokens = await refreshAccessToken(refreshToken);
      if (!refreshedTokens) {
        const response = NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
        clearAuthCookies(response);
        return response;
      }
      accessToken = refreshedTokens.access_token;
    }

    const formData = await request.formData();

    let response = await uploadToBackend(formData, accessToken);

    if (response.status === 401 && refreshToken) {
      refreshedTokens = await refreshAccessToken(refreshToken);
      if (refreshedTokens) {
        response = await uploadToBackend(formData, refreshedTokens.access_token);
      }
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Upload failed" }));
      const errorResponse = NextResponse.json(error, { status: response.status });
      if (response.status === 401) clearAuthCookies(errorResponse);
      return errorResponse;
    }

    const data = await response.json();
    const successResponse = NextResponse.json(data, { status: 201 });
    if (refreshedTokens) {
      setAuthCookies(successResponse, {
        accessToken: refreshedTokens.access_token,
        refreshToken: refreshedTokens.refresh_token,
      });
    }
    return successResponse;
  } catch (error) {
    console.error("Chat file upload proxy failed", error);
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
