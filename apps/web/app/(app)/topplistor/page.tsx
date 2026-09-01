import type { Metadata } from "next";
import { TopplistorView } from "./TopplistorView";
import { DECISIONS_V3_ENABLED } from "@/lib/v3";
import { TopplistorViewV3 } from "@/components/screener-v3/TopplistorViewV3";

export const metadata: Metadata = {
  title: "Topplistor — MarketScan",
  description: "MasterRank — den auktoritativa rankningen (kvalitet, värdering, analytiker, teknik, katalysator)",
};

export default function TopplistorPage() {
  return DECISIONS_V3_ENABLED ? <TopplistorViewV3 /> : <TopplistorView />;
}