import type { Metadata } from "next";
import { PortfoljView } from "./PortfoljView";
import { DECISIONS_V3_ENABLED } from "@/lib/v3";
import { PortfoljViewV3 } from "./PortfoljViewV3";

export const metadata: Metadata = { title: "Min portfölj" };

export default function PortfoljPage() {
  // Real runtime gate: V3 renders only when NEXT_PUBLIC_DECISIONS_V3=true;
  // otherwise the V1 portfolio view stays untouched (dual-render behind flag).
  return DECISIONS_V3_ENABLED ? <PortfoljViewV3 /> : <PortfoljView />;
}