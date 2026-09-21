import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

const originalBackendUrl = process.env.BACKEND_URL;
const originalPublicApiUrl = process.env.NEXT_PUBLIC_API_URL;
const originalSiteUrl = process.env.NEXT_PUBLIC_SITE_URL;

function redirectLocation(response: Response): URL {
  const location = response.headers.get("location");
  if (!location) throw new Error("Missing redirect location");
  return new URL(location);
}

describe("Google OAuth route", () => {
  afterEach(() => {
    process.env.BACKEND_URL = originalBackendUrl;
    process.env.NEXT_PUBLIC_API_URL = originalPublicApiUrl;
    process.env.NEXT_PUBLIC_SITE_URL = originalSiteUrl;
    vi.resetModules();
  });

  it("uses the localhost request origin for the Google callback", async () => {
    process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000";
    process.env.NEXT_PUBLIC_SITE_URL = "https://advancedanalytica.co.uk";

    const { GET } = await import("./route");
    const response = await GET(new NextRequest("http://localhost:3000/api/auth/google"));
    const location = redirectLocation(response);

    expect(location.origin).toBe("http://localhost:8000");
    expect(location.pathname).toBe("/api/v1/auth/google/authorize");
    expect(location.searchParams.get("redirect_uri")).toBe(
      "http://localhost:3000/auth/callback",
    );
    expect(location.searchParams.get("state")).toBeTruthy();
  });

  it("uses forwarded production headers for the Google callback", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.advancedanalytica.co.uk";
    process.env.NEXT_PUBLIC_SITE_URL = "https://advancedanalytica.co.uk";

    const { GET } = await import("./route");
    const response = await GET(
      new NextRequest("http://internal:3000/api/auth/google", {
        headers: {
          "x-forwarded-host": "advancedanalytica.co.uk",
          "x-forwarded-proto": "https",
        },
      }),
    );
    const location = redirectLocation(response);

    expect(location.searchParams.get("redirect_uri")).toBe(
      "https://advancedanalytica.co.uk/auth/callback",
    );
  });
});
