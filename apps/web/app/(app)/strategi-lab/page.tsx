import type { Metadata } from "next";
import { StrategiLabView } from "./StrategiLabView";

export const metadata: Metadata = { title: "Strategi Lab" };

export default function StrategiLabPage() {
  return <StrategiLabView />;
}
