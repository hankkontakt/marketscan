import type { Metadata } from "next";
import { TopplistorView } from "./TopplistorView";

export const metadata: Metadata = {
  title: "Topplistor — MarketScan",
  description: "MasterRank — den auktoritativa rankningen (kvalitet, värdering, analytiker, teknik, katalysator)",
};

export default function TopplistorPage() {
  return <TopplistorView />;
}
