import type { Metadata } from "next";
import { StockView } from "./StockView";

interface Props {
  params: Promise<{ ticker: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { ticker } = await params;
  return { title: ticker.toUpperCase() };
}

export default async function AktiePage({ params }: Props) {
  const { ticker } = await params;
  return <StockView ticker={ticker.toUpperCase()} />;
}
