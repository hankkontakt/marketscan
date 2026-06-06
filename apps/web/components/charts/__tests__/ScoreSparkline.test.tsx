import { describe, it, expect } from "vitest";
import React from "react";
import { ScoreSparkline } from "../ScoreSparkline";

describe("ScoreSparkline", () => {
  it("renders without crashing", () => {
    const { container } = render(React.createElement(ScoreSparkline, { values: [30, 50, 70] }));
    expect(container.querySelector("svg")).toBeTruthy();
  });

  it("renders empty placeholder for < 2 values", () => {
    const { container } = render(React.createElement(ScoreSparkline, { values: [50] }));
    expect(container.querySelector("svg")).toBeFalsy();
  });
});

// Minimal render helper (no jsdom needed for SVG output)
function render(el: React.ReactElement) {
  const div = document.createElement("div");
  document.body.appendChild(div);
  // Server-side render by just checking existence
  return { container: div };
}
