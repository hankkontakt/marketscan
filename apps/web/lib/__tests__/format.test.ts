import { describe, it, expect } from "vitest";
import { formatPrice, formatPctChange, signalLabel, scoreColorClass, segmentLabel } from "../format";

describe("formatPrice", () => {
  it("formats a number as SEK currency", () => {
    expect(formatPrice(123.45)).toMatch(/123,45/);
  });

  it("formats GBp as pence with p suffix", () => {
    expect(formatPrice(2864, "GBp")).toMatch(/2\s?864p/);
  });

  it("falls back gracefully on invalid currency code without throwing", () => {
    expect(formatPrice(10, "INVALID_CURRENCY")).toContain("INVALID_CURRENCY");
  });

  it("formats AUD currency", () => {
    expect(formatPrice(50.25, "AUD")).toMatch(/50,25/);
  });

  it("returns em dash for null", () => {
    expect(formatPrice(null)).toBe("—");
  });

  it("returns em dash for undefined", () => {
    expect(formatPrice(undefined)).toBe("—");
  });
});

describe("formatPctChange", () => {
  it("formats positive change with plus sign", () => {
    expect(formatPctChange(0.05)).toContain("+");
    expect(formatPctChange(0.05)).toContain("5");
  });

  it("formats negative change with minus sign", () => {
    expect(formatPctChange(-0.1)).toContain("-");
    expect(formatPctChange(-0.1)).toContain("10");
  });

  it("returns em dash for null", () => {
    expect(formatPctChange(null)).toBe("—");
  });
});

describe("signalLabel", () => {
  it('returns "Starkt köpläge" for STARK', () => {
    expect(signalLabel("STARK")).toBe("Starkt köpläge");
  });

  it('returns "Bra läge" for OK', () => {
    expect(signalLabel("OK")).toBe("Bra läge");
  });

  it("returns em dash for null", () => {
    expect(signalLabel(null)).toBe("—");
  });
});

describe("scoreColorClass", () => {
  it("returns high variant for score >= 70", () => {
    expect(scoreColorClass(85)).toBe("text-[var(--color-score-high)]");
  });

  it("returns mid variant for score between 50 and 69", () => {
    expect(scoreColorClass(60)).toBe("text-[var(--color-score-mid)]");
  });

  it("returns low variant for score < 50", () => {
    expect(scoreColorClass(30)).toBe("text-[var(--color-score-low)]");
  });

  it("returns muted for null", () => {
    expect(scoreColorClass(null)).toBe("text-[var(--color-text-muted)]");
  });
});

describe("segmentLabel", () => {
  it("translates segments to Swedish labels", () => {
    expect(segmentLabel("large_cap")).toBe("Stora bolag");
    expect(segmentLabel("mid_cap")).toBe("Medelstora");
    expect(segmentLabel("small_cap")).toBe("Småbolag");
    expect(segmentLabel("micro_cap")).toBe("Mikrobolag");
    expect(segmentLabel("unknown")).toBe("Okänd");
  });

  it("handles null gracefully", () => {
    expect(segmentLabel(null)).toBe("—");
  });
});
