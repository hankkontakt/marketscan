import type { Metadata } from "next";
import { InsiderRadarView } from "./InsiderRadarView";

export const metadata: Metadata = {
  title: "Insider Radar — MarketScan",
  description: "Se vad bolagsledningar och styrelseledamöter köper och säljer",
};

export default function InsiderRadarPage() {
  return <InsiderRadarView />;
}
