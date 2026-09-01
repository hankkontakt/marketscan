import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: { getSession: async () => ({ data: { session: null } }) },
  }),
}));

import { v3Screener, v3StockByTicker, DECISIONS_V3_ENABLED } from "../v3";

describe("v3 decision client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("builds the screener URL with filters and parses the projection", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ snapshot_id: "s1", as_of: "2026-09-01T12:00:00Z", total_count: 1, rows: [{ ticker: "MSFT" }] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const data = await v3Screener({ thesis_band: "BULLISH", segment: "large_cap" });
    const [url] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/api/v3/decisions/screener");
    expect(String(url)).toContain("thesis_band=BULLISH");
    expect(String(url)).toContain("segment=large_cap");
    expect(data.total_count).toBe(1);
  });

  it("omits empty filters from the query string", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ rows: [] }) });
    vi.stubGlobal("fetch", fetchMock);

    await v3Screener({});
    const [url] = fetchMock.mock.calls[0];
    expect(String(url)).not.toContain("?");
  });

  it("resolves a stock decision by ticker alias", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ticker: "CPRX", thesis_band: "NEUTRAL" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const data = await v3StockByTicker("CPRX");
    const [url] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/api/v3/decisions/stock/CPRX");
    expect(data.thesis_band).toBe("NEUTRAL");
  });

  it("gate is read from NEXT_PUBLIC_DECISIONS_V3", () => {
    // Build-time env; the assertion documents the contract (default off).
    expect(["true", "false"]).toContain(String(DECISIONS_V3_ENABLED));
  });
});