import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import { ChatControls } from "./chat-controls";

describe("ChatControls", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          default: "anthropic:claude-sonnet-4-5",
          models: [
            {
              id: "anthropic:claude-sonnet-4-5",
              provider: "anthropic",
              model: "claude-sonnet-4-5",
              label: "Anthropic: claude-sonnet-4-5",
              enabled: true,
              default: true,
            },
            {
              id: "openai:gpt-5.4-mini",
              provider: "openai",
              model: "gpt-5.4-mini",
              label: "OpenAI: gpt-5.4-mini",
              enabled: true,
              default: false,
            },
          ],
        }),
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders backend-provided provider model options", async () => {
    const onModelChange = vi.fn();
    render(<ChatControls onModelChange={onModelChange} />);

    fireEvent.click(screen.getByRole("button", { name: /chat controls/i }));

    await waitFor(() => {
      expect(screen.getByText("Anthropic: claude-sonnet-4-5")).toBeInTheDocument();
      expect(screen.getByText("OpenAI: gpt-5.4-mini")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /openai: gpt-5.4-mini/i }));

    expect(onModelChange).toHaveBeenCalledWith("openai:gpt-5.4-mini");
  });
});
