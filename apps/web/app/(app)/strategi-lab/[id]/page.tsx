import type { Metadata } from "next";
import { StrategyResultView } from "./StrategyResultView";

export const metadata: Metadata = { title: "Backtest-resultat" };

export default async function StrategyResultPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <StrategyResultView strategyId={id} />;
}
