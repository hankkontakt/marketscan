import { describe, it, expect } from "vitest";
import { buildScanUrl } from "../api";

describe("buildScanUrl", () => {
  it("builds a query string from params", () => {
    const url = buildScanUrl({ score_min: 50, limit: 100 });
    expect(url).toContain("score_min=50");
    expect(url).toContain("limit=100");
  });

  it("skips undefined values", () => {
    const url = buildScanUrl({ score_min: undefined, limit: 50 });
    expect(url).not.toContain("score_min");
    expect(url).toContain("limit=50");
  });

  it("handles array params", () => {
    const url = buildScanUrl({ segments: ["large_cap", "mid_cap"] });
    expect(url).toContain("segments=large_cap");
    expect(url).toContain("segments=mid_cap");
  });
});
