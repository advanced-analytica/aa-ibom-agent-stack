import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { OAuthButtons } from "./oauth-buttons";

describe("OAuthButtons", () => {
  const originalProviders = process.env.NEXT_PUBLIC_OAUTH_PROVIDERS;

  afterEach(() => {
    process.env.NEXT_PUBLIC_OAUTH_PROVIDERS = originalProviders;
  });

  it("renders Google sign-in through the local auth route", () => {
    process.env.NEXT_PUBLIC_OAUTH_PROVIDERS = "google";

    render(<OAuthButtons />);

    const link = screen.getByRole("link", { name: /continue with google/i });
    expect(link).toHaveAttribute("href", "/api/auth/google");
  });

  it("preserves the next route when supplied", () => {
    process.env.NEXT_PUBLIC_OAUTH_PROVIDERS = "google";

    render(<OAuthButtons next="/chat" />);

    expect(screen.getByRole("link", { name: /continue with google/i })).toHaveAttribute(
      "href",
      "/api/auth/google?next=%2Fchat",
    );
  });
});
