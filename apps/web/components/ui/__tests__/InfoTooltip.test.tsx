import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { InfoTooltip } from "../InfoTooltip";

describe("InfoTooltip", () => {
  it("renders trigger button", () => {
    const { container } = render(<InfoTooltip text="test tooltip" />);
    const btn = container.querySelector("button");
    expect(btn).not.toBeNull();
  });

  it("renders with custom side", () => {
    const { container } = render(<InfoTooltip text="left tooltip" side="left" />);
    const btn = container.querySelector("button");
    expect(btn).not.toBeNull();
  });
});
