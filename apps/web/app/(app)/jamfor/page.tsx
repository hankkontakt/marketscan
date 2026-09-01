import type { Metadata } from "next";
import { JamforView } from "./JamforView";
import { JamforViewV3 } from "./JamforViewV3";
import { DECISIONS_V3_ENABLED } from "@/lib/v3";

export const metadata: Metadata = { title: "Jämför aktier" };

export default function JamforPage() {
  // Real runtime gate: V3 renders only when NEXT_PUBLIC_DECISIONS_V3=true;
  // otherwise the V1 compare view stays untouched (dual-render behind flag).
  return DECISIONS_V3_ENABLED ? <JamforViewV3 /> : <JamforView />;
}
