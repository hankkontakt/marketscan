import type { Metadata } from "next";
import { DagligBriefingView } from "./DagligBriefingView";

export const metadata: Metadata = {
  title: "Daglig Briefing — MarketScan",
  description: "Dagens marknadsläge — toppbetyg, rörelser och insideraktivitet",
};

export default function DagligBriefingPage() {
  return <DagligBriefingView />;
}
