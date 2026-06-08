import type { Metadata } from "next";
import { SignalAnalyticsView } from "./SignalAnalyticsView";

export const metadata: Metadata = { title: "Signalanalys" };

export default function SignalAnalyticsPage() {
  return <SignalAnalyticsView />;
}
