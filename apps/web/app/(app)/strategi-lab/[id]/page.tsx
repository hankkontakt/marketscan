import type { Metadata } from "next";
import { StrategyResultView } from "./StrategyResultView";

export const metadata: Metadata = { title: "Backtest-resultat" };

export default function StrategyResultPage({ params }: { params: { id: string } }) {
  return <StrategyResultView strategyId={params.id} />;
}
