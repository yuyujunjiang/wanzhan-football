import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChatMarkdown } from "./ChatMarkdown";

describe("ChatMarkdown", () => {
  it("renders headings and lists", () => {
    render(<ChatMarkdown content={"## 推荐\n\n- 第一场\n- **第二场**"} />);

    expect(screen.getByRole("heading", { level: 2, name: "推荐" })).toBeInTheDocument();
    expect(screen.getByText("第一场")).toBeInTheDocument();
    expect(screen.getByText("第二场").tagName).toBe("STRONG");
  });
});
