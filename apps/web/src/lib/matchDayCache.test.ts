import { describe, expect, it } from "vitest";

import { buildTodayRecommendApiContent } from "./matchDayCache";

describe("buildTodayRecommendApiContent", () => {
  it("prefixes label with stringified cache", () => {
    const cache = {
      date: "2026-05-19",
      fixed: [{ matchId: 1 }],
      dynamic: { byMatchId: {} },
      meta: { createdAt: "x", updatedAt: "x" }
    };

    const content = buildTodayRecommendApiContent(cache);
    expect(content.startsWith("今日推荐")).toBe(true);
    expect(content).toBe(`今日推荐${JSON.stringify(cache)}`);
    expect(JSON.parse(content.slice("今日推荐".length))).toEqual(cache);
  });
});
