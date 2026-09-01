import type { Metadata } from "next";
import { ScreenerView } from "./ScreenerView";
import { DECISIONS_V3_ENABLED } from "@/lib/v3";
import { ScreenerViewV3 } from "@/components/screener-v3/ScreenerViewV3";

export const metadata: Metadata = { title: "Aktier" };

export default function ScreenerPage() {
  // Real runtime gate: V3 renders only when NEXT_PUBLIC_DECISIONS_V3=true;
  // otherwise the V1 screener stays untouched (dual-render behind flag,
  // plan section 8: "Wire Screener v3 through API_BASE; dual-render V1/V3").
  return DECISIONS_V3_ENABLED ? <ScreenerViewV3 /> : <ScreenerView />;
}