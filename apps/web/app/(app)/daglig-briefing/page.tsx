import type { Metadata } from "next";
import { DagligBriefingView } from "./DagligBriefingView";
import { DagligBriefingViewV3 } from "./DagligBriefingViewV3";
import { DECISIONS_V3_ENABLED } from "@/lib/v3";

export const metadata: Metadata = {
  title: "Daglig Briefing — MarketScan",
  description: "Dagens marknadsläge — toppbetyg, rörelser och insideraktivitet",
};

export default function DagligBriefingPage() {
  // Real runtime gate: V3 renders only when NEXT_PUBLIC_DECISIONS_V3=true;
  // otherwise the V1 briefing stays untouched (dual-render behind flag).
  return DECISIONS_V3_ENABLED ? <DagligBriefingViewV3 /> : <DagligBriefingView />;
}
