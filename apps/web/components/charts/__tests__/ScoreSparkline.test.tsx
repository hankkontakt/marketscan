import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ScoreSparkline } from "../ScoreSparkline";

describe("ScoreSparkline", () => {
  it("renders empty state for <2 values", () => {
    const { container } = render(<ScoreSparkline values={[]} />);
    expect(container.querySelector("svg")).toBeNull();
  });

  it("renders svg with 2+ values", () => {
    const { container } = render(<ScoreSparkline values={[50, 60, 70]} />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg?.getAttribute("width")).toBe("48");
  });
});
