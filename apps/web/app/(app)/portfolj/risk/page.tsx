import type { Metadata } from "next";
import { RiskView } from "./RiskView";

export const metadata: Metadata = { title: "Portföljrisk & Analys" };

export default function RiskPage() {
  return <RiskView />;
}
