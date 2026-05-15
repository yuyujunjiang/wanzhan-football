import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChatPage } from "./ChatPage";

vi.mock("../../lib/aiChatStream", () => ({
  streamAiChat: vi.fn(async ({ onChunk, onDone }) => {
    onChunk("流式");
    onChunk("回答");
    onDone();
  })
}));

describe("ChatPage", () => {
  it("shows prompt chips with 今日推荐 first", () => {
    render(<ChatPage />);

    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toHaveTextContent("今日推荐");
  });

  it("sends a prompt and appends streamed answer", async () => {
    const user = userEvent.setup();
    render(<ChatPage />);

    await user.click(screen.getByRole("button", { name: "今日推荐" }));

    expect(await screen.findByText("今日推荐")).toBeInTheDocument();
    expect(await screen.findByText("流式回答")).toBeInTheDocument();
  });

  it("does not send blank input", async () => {
    render(<ChatPage />);

    expect(screen.getByRole("button", { name: "发送" })).toBeDisabled();
  });
});
