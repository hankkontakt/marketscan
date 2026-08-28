import type { Metadata } from "next";
import { KvalitetslistaView } from "./KvalitetslistaView";

export const metadata: Metadata = {
  title: "Kvalitetslista — MarketScan",
  description: "Evidensbaserad kvalitetsscreening av svenska småbolag",
};

export default function KvalitetslistaPage() {
  return <KvalitetslistaView />;
}