import type { Metadata } from "next";
import { ScreenerView } from "./ScreenerView";

export const metadata: Metadata = { title: "Screener" };

export default function ScreenerPage() {
  return <ScreenerView />;
}
