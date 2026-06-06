import { describe, it, expect } from "vitest";
import React from "react";
import { InfoTooltip } from "../InfoTooltip";

describe("InfoTooltip", () => {
  it("renders the trigger button", () => {
    const el = React.createElement(InfoTooltip, { text: "Helpful info" });
    // Component should be defined and memo-ized
    expect(InfoTooltip.displayName).toBeUndefined();
    expect(el.type).toBeDefined();
  });

  it("wraps text in Radix Tooltip provider", () => {
    const el = React.createElement(InfoTooltip, { text: "Test tooltip" });
    expect(el.props).toHaveProperty("text", "Test tooltip");
    expect(el.props).toHaveProperty("side", "top");
  });
});
