import type { Metadata } from "next";
import { RadarView } from "./RadarView";

export const metadata: Metadata = {
  title: "Kandidatradar — MarketScan",
  description: "Bolag med sammanvägda signaler — kvalitet, momentum, insiders, blankning och nyheter",
};

export default function RadarPage() {
  return <RadarView />;
}